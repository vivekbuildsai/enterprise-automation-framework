"""Execution-model detection — captures how a customer's *existing*
suite is run (command, runner, parallelism, retries, environments,
browser, reporting, test selection) purely by reading known build/CI/
runner config files. Never executes anything: a real customer suite may
need credentials, infrastructure, licenses, or production-like systems
this analyzer has no business touching (see docs/FrameworkSync.md,
"Test execution preservation"). Every field stays `None`/empty unless
backed by a real file — nothing here is guessed from file-type
convention alone (e.g. "a `.csproj` exists, so the command is probably
`dotnet test`" is convention, not evidence, and is deliberately not
reported).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from framework.sync.models import ExecutionModel

_CI_COMMAND_PATTERN = re.compile(
    r"\b(mvn\s+test[^\n&|;]*|gradle\s+test[^\n&|;]*|pytest[^\n&|;]*"
    r"|npx\s+playwright\s+test[^\n&|;]*|npm\s+test[^\n&|;]*|npm\s+run\s+test[^\n&|;]*"
    r"|robot\s+[^\n&|;]*|dotnet\s+test[^\n&|;]*)"
)
_ALLURE_TOKEN = re.compile(r"allure", re.IGNORECASE)
_REPORTING_TOKENS = {
    re.compile(r"allure", re.IGNORECASE): "Allure",
    re.compile(r"extentreports", re.IGNORECASE): "ExtentReports",
    re.compile(r"mochawesome", re.IGNORECASE): "Mochawesome",
    re.compile(r"junit-xml|junitxml", re.IGNORECASE): "JUnit XML",
    re.compile(r"\['html'\]|reporter:\s*\[?\s*['\"]html['\"]"): "HTML reporter",
}
_BROWSER_TOKENS = ("chromium", "chrome", "firefox", "webkit", "edge", "safari")

# A real customer `testng.xml` is untrusted XML — deliberately never fed
# to a general-purpose XML parser (even the stdlib's `ElementTree`, which
# bandit correctly flags as XXE/entity-expansion-prone: internal entity
# expansion — the classic "billion laughs" DoS — is NOT blocked by
# ElementTree's defaults, confirmed by direct testing, only external
# SYSTEM entity resolution is). Only the two attributes actually needed
# are pulled directly off the `<suite ...>` opening tag via regex — the
# same lightweight-scanning approach the rest of `framework.sync` already
# uses, and it structurally cannot expand an entity because no entity
# processing ever happens.
_TESTNG_SUITE_TAG_PATTERN = re.compile(r"<suite\b[^>]*>", re.IGNORECASE)
_TESTNG_THREAD_COUNT_PATTERN = re.compile(r'thread-count\s*=\s*"(\d+)"', re.IGNORECASE)


def _testng_suite_parallelism(file_contents: dict[Path, str]) -> tuple[int | None, str | None]:
    for path, text in file_contents.items():
        if path.name != "testng.xml":
            continue
        suite_tag_match = _TESTNG_SUITE_TAG_PATTERN.search(text)
        if not suite_tag_match:
            continue
        thread_count_match = _TESTNG_THREAD_COUNT_PATTERN.search(suite_tag_match.group(0))
        parallelism = int(thread_count_match.group(1)) if thread_count_match else None
        return parallelism, "TestNG (via Maven Surefire)"
    return None, None


def _ci_command(file_contents: dict[Path, str]) -> str | None:
    """Scans GitHub Actions workflow YAML `run:` steps (parsed via
    PyYAML — already a framework dependency, safe/reliable for
    structured YAML) and, as a fallback, plain-text CI/build files
    (Jenkinsfile, README, Makefile) for a recognizable test-run command.
    """
    for path, text in file_contents.items():
        if ".github/workflows" in str(path).replace("\\", "/") and path.suffix in (".yml", ".yaml"):
            try:
                workflow = yaml.safe_load(text)
            except yaml.YAMLError:
                continue
            command = _find_run_command_in_workflow(workflow)
            if command:
                return command
    for path, text in file_contents.items():
        if path.name in ("Jenkinsfile", "README.md", "Makefile") and (
            match := _CI_COMMAND_PATTERN.search(text)
        ):
            return match.group(1).strip()
    return None


def _find_run_command_in_workflow(workflow: object) -> str | None:
    if not isinstance(workflow, dict):
        return None
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return None
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []):
            if not isinstance(step, dict):
                continue
            run = step.get("run")
            if isinstance(run, str) and (match := _CI_COMMAND_PATTERN.search(run)):
                return match.group(1).strip()
    return None


def _package_json_test_script(file_contents: dict[Path, str]) -> str | None:
    for path, text in file_contents.items():
        if path.name != "package.json":
            continue
        if match := re.search(r'"test"\s*:\s*"([^"]+)"', text):
            return match.group(1)
    return None


def _pytest_addopts(file_contents: dict[Path, str]) -> tuple[int | None, int | None, list[str]]:
    """`(parallelism, retries, reporting)` from `pytest.ini`/`pyproject.toml`
    `addopts`. `-n auto` (pytest-xdist) has no fixed number, so
    parallelism stays `None` for it rather than reporting a fabricated
    count — only `-n <digits>` yields a real parallelism value.
    """
    for path, text in file_contents.items():
        if path.name not in ("pytest.ini", "pyproject.toml", "setup.cfg"):
            continue
        parallelism = None
        if match := re.search(r"-n\s*(\d+)\b", text):
            parallelism = int(match.group(1))
        retries = None
        if match := re.search(r"--reruns[= ]\s*(\d+)", text):
            retries = int(match.group(1))
        reporting = ["Allure"] if _ALLURE_TOKEN.search(text) else []
        if parallelism is not None or retries is not None or reporting:
            return parallelism, retries, reporting
    return None, None, []


def _pytest_config_implied_command(file_contents: dict[Path, str]) -> str | None:
    """A `pytest.ini`/a `[tool.pytest.ini_options]` section existing at
    all is, by itself, real evidence the command is `pytest` — the same
    "config file presence is evidence" precedent `PytestAdapter` already
    uses for framework detection, applied here only as a fallback when no
    more specific invocation (a CI step, a package script) was found.
    """
    for path, text in file_contents.items():
        if path.name == "pytest.ini":
            return "pytest"
        if path.name == "pyproject.toml" and "[tool.pytest.ini_options]" in text:
            return "pytest"
    return None


def _playwright_config(file_contents: dict[Path, str]) -> tuple[int | None, int | None, str | None]:
    """`(retries, workers, browser)` from `playwright.config.ts`."""
    for path, text in file_contents.items():
        if path.name != "playwright.config.ts":
            continue
        retries = int(m.group(1)) if (m := re.search(r"retries:\s*(\d+)", text)) else None
        workers = int(m.group(1)) if (m := re.search(r"workers:\s*(\d+)", text)) else None
        browser = m.group(1) if (m := re.search(r"browserName:\s*['\"](\w+)['\"]", text)) else None
        return retries, workers, browser
    return None, None, None


def detect_reporting_tools(file_contents: dict[Path, str]) -> list[str]:
    found: list[str] = []
    for pattern, label in _REPORTING_TOKENS.items():
        if label in found:
            continue
        if any(pattern.search(text) for text in file_contents.values()):
            found.append(label)
    return found


def _browser(file_contents: dict[Path, str]) -> str | None:
    for text in file_contents.values():
        lowered = text.lower()
        for token in _BROWSER_TOKENS:
            if token in lowered:
                return token
    return None


def _environments(file_contents: dict[Path, str]) -> list[str]:
    """Environment names visible via `.env.<name>` files or
    `config/environments/<name>.yaml` — never guessed beyond what's
    literally present as a file.
    """
    found: set[str] = set()
    for path in file_contents:
        if path.name.startswith(".env.") and path.name.count(".") >= 2:
            found.add(path.name.split(".", 2)[2].split(".")[0])
        parts = path.parts
        if "environments" in parts and path.suffix in (".yaml", ".yml"):
            found.add(path.stem)
    return sorted(found)


def detect_execution_model(file_contents: dict[Path, str]) -> ExecutionModel | None:
    """Returns `None` (not an empty `ExecutionModel`) when zero evidence
    of any kind was found — an undetected execution model is not "no
    parallelism, no retries," it's simply unknown.
    """
    command = (
        _ci_command(file_contents)
        or _package_json_test_script(file_contents)
        or _pytest_config_implied_command(file_contents)
    )
    runner: str | None = None
    parallelism, testng_runner = _testng_suite_parallelism(file_contents)
    if testng_runner:
        runner = testng_runner

    pytest_parallelism, pytest_retries, pytest_reporting = _pytest_addopts(file_contents)
    playwright_retries, playwright_workers, playwright_browser = _playwright_config(file_contents)

    if parallelism is None:
        parallelism = pytest_parallelism if pytest_parallelism is not None else playwright_workers
    retries = pytest_retries if pytest_retries is not None else playwright_retries

    reporting = detect_reporting_tools(file_contents) or pytest_reporting
    browser = playwright_browser or _browser(file_contents)
    environments = _environments(file_contents)
    test_selection = None
    if match := re.search(r"-m\s+['\"]?(\w[\w\s]*)['\"]?", command or ""):
        test_selection = match.group(1).strip()

    if not any(
        (command, runner, parallelism, retries, environments, browser, reporting, test_selection)
    ):
        return None

    return ExecutionModel(
        command=command,
        runner=runner,
        parallelism=parallelism,
        retries=retries,
        environments=environments,
        browser=browser,
        reporting=reporting,
        test_selection=test_selection,
    )
