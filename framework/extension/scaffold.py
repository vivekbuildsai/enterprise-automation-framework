"""Framework-native scaffold generation — the one part of this milestone
that writes anything at all, and only ever into a controlled,
project-root-safe output directory (see `framework.extension.paths`),
only for subjects the deterministic extension analysis already classified
`CREATE_NEW`/`EXTEND_EXISTING`, and only in the customer's own detected
automation ecosystem (see `framework.extension.target`).

This is explicitly a SCAFFOLD, not a finished implementation: every
generated file carries `_SCAFFOLD_NOTICE`, every locator/assertion that
wasn't itself confirmed evidence carries a `TODO`, and nothing here is
ever labeled "production ready". Existing, already-reusable capabilities
(an API client, a DB repository, an auth mechanism, `DataComparator`, ...)
are referenced in comments — by name and source file — never duplicated
as a second implementation (see the "BAD: generate another ApiClient"
rule this module exists to honor).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from framework.discovery.models import DiscoveredPage, DiscoveryReport
from framework.exceptions import ConfigurationError
from framework.extension.models import (
    ExtensionClassification,
    ExtensionItem,
    ExtensionReport,
    ExtensionSubjectType,
    ScaffoldFile,
    ScaffoldFileKind,
    ScaffoldManifest,
    ScaffoldTarget,
    TestOpportunity,
)
from framework.extension.paths import resolve_scaffold_output_dir, safe_scaffold_target
from framework.extension.target import detect_scaffold_target
from framework.sync.models import RepositoryAnalysis

_SCAFFOLD_NOTICE = (
    "GENERATED SCAFFOLD — REVIEW REQUIRED. Every locator/mapping below came "
    "from real discovery/correlation evidence, but nothing here has been "
    "executed or validated. Not production ready until a human confirms it."
)

_SCAFFOLDABLE_CLASSIFICATIONS = (
    ExtensionClassification.CREATE_NEW,
    ExtensionClassification.EXTEND_EXISTING,
)


@dataclass(frozen=True, slots=True)
class _ElementPlan:
    """One discovered element, reduced to what every per-language template
    needs — computed once, rendered N ways.
    """

    slug: str
    label: str
    is_input: bool
    locator_strategy: str
    locator_value: str
    needs_locator_review: bool


def _words(text: str) -> list[str]:
    # Splits camelCase/PascalCase boundaries too (e.g. "EmployeeDetails" ->
    # ["Employee", "Details"]) — needed because `_slugify` is sometimes
    # called on an already-`_pascal_case`d string (see `_page_feature_name`),
    # and without this a name like "EmployeeDetails" would slugify to the
    # single unreadable word "employeedetails" instead of "employee_details".
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.findall(r"[A-Za-z0-9]+", spaced)


def _slugify(text: str, *, fallback: str = "element") -> str:
    words = _words(text)
    return "_".join(w.lower() for w in words)[:40] or fallback


def _pascal_case(text: str, *, fallback: str = "New") -> str:
    words = [w.capitalize() for w in _words(text)] or [fallback]
    return "".join(words)


def _page_seed(page: DiscoveredPage) -> str:
    if page.title.strip():
        return page.title.strip()
    last_segment = Path(urlparse(page.url).path.rstrip("/")).name
    return last_segment or "New Page"


def _page_class_name(page: DiscoveredPage) -> str:
    name = _pascal_case(_page_seed(page), fallback="New")
    return name if name.endswith("Page") else f"{name}Page"


def _page_feature_name(page: DiscoveredPage) -> str:
    """Same seed as `_page_class_name`, without the `Page` suffix — used
    for test class/file names (`EmployeeDetailsTest`, not
    `EmployeeDetailsPageTest`).
    """
    return _pascal_case(_page_seed(page), fallback="New")


def _plan_elements(page: DiscoveredPage) -> list[_ElementPlan]:
    plans: list[_ElementPlan] = []
    seen_slugs: set[str] = set()
    for index, element in enumerate(page.elements):
        base = element.locator.accessible_name or element.text or element.element_type
        slug = _slugify(base or "element")
        if slug in seen_slugs:
            slug = f"{slug}_{index}"
        seen_slugs.add(slug)
        plans.append(
            _ElementPlan(
                slug=slug,
                label=base or element.tag,
                is_input=element.element_type in ("input", "textbox") or element.tag == "input",
                locator_strategy=element.locator.strategy,
                locator_value=element.locator.value,
                needs_locator_review=element.locator.strategy not in ("test_id", "role", "label"),
            )
        )
    return plans


def _find_discovered_page(
    item: ExtensionItem, discovery_report: DiscoveryReport
) -> DiscoveredPage | None:
    """A `UI_PAGE` `ExtensionItem.subject` is always `page.title or
    page.url` (see `framework.extension.gap_analysis._page_extension_item`)
    — matched back to the real `DiscoveredPage` by trying both, since the
    manifest only ever kept the resolved string, not which field it came
    from.
    """
    for page in discovery_report.pages:
        if item.subject in (page.title, page.url):
            return page
    return None


def _related_reuse_lines(page: DiscoveredPage, extension_items: list[ExtensionItem]) -> list[str]:
    """Comments pointing at existing capabilities this page's own
    discovered network calls already correlate to — the mechanism that
    keeps generated tests referencing the customer's real API/DB layer
    instead of re-describing it.
    """
    page_paths = {call.path for call in page.network_calls}
    if not page_paths:
        return []
    lines: list[str] = []
    for item in extension_items:
        if item.subject_type not in (
            ExtensionSubjectType.API_ENDPOINT,
            ExtensionSubjectType.DATABASE,
        ):
            continue
        if item.classification not in (
            ExtensionClassification.REUSE_EXISTING,
            ExtensionClassification.EXTEND_EXISTING,
        ):
            continue
        if not any(path in item.subject for path in page_paths):
            continue
        if item.matched_capability is not None:
            lines.append(
                f"Reuses: {item.matched_capability.name} ({item.matched_capability.source_file})"
            )
    return lines


def _opportunity_for_page(
    page: DiscoveredPage, test_opportunities: list[TestOpportunity]
) -> TestOpportunity | None:
    for opportunity in test_opportunities:
        if opportunity.page_url == page.url:
            return opportunity
    return None


# --- Java (Selenium) -------------------------------------------------------


def _java_page_object(class_name: str, elements: list[_ElementPlan]) -> str:
    lines = [
        "package pages;",
        "",
        "import org.openqa.selenium.By;",
        "import org.openqa.selenium.WebDriver;",
        "",
        f"// {_SCAFFOLD_NOTICE}",
        f"public class {class_name} {{",
        "    private final WebDriver driver;",
        "",
    ]
    for element in elements:
        comment = "TODO: verify locator" if element.needs_locator_review else "confirmed locator"
        lines.append(f"    // {comment} ({element.locator_strategy})")
        lines.append(f"    private final By {element.slug} = {_java_by(element)};")
        lines.append("")
    lines.append(f"    public {class_name}(WebDriver driver) {{")
    lines.append("        this.driver = driver;")
    lines.append("    }")
    lines.append("")
    for element in elements:
        method = _pascal_case(element.slug)
        if element.is_input:
            lines.append(f"    public void fill{method}(String value) {{")
            lines.append("        // TODO: confirm test data")
            lines.append(f"        driver.findElement({element.slug}).sendKeys(value);")
        else:
            lines.append(f"    public void click{method}() {{")
            lines.append(f"        driver.findElement({element.slug}).click();")
        lines.append("    }")
        lines.append("")
    lines.append("}")
    return "\n".join(lines)


def _java_by(element: _ElementPlan) -> str:
    if element.locator_strategy == "test_id":
        return f"By.cssSelector(\"[data-testid='{element.locator_value}']\")"
    if element.locator_strategy == "css" and element.locator_value.startswith("#"):
        return f'By.id("{element.locator_value[1:]}")'
    return f'By.cssSelector("{element.locator_value}")'


def _java_testng_test(
    class_name: str, feature_name: str, reuse_lines: list[str], opportunity: TestOpportunity | None
) -> str:
    scenarios = (opportunity.suggested_scenario_types if opportunity else None) or ["happy_path"]
    lines = [
        "package tests;",
        "",
        "import org.testng.annotations.Test;",
        f"import pages.{class_name};",
        "// TODO: import the existing WebDriver/session setup this framework's other tests use",
        "// TODO: import the existing API client / DB validation utilities referenced below",
        "",
        f"// {_SCAFFOLD_NOTICE}",
    ]
    for line in reuse_lines:
        lines.append(f"// {line}")
    lines.append(f"public class {feature_name}Test {{")
    lines.append("")
    for scenario in scenarios:
        method = _pascal_case(scenario.replace("_", " "), fallback="Scenario")
        lines.append('    @Test(groups = {"scaffold"})')
        lines.append(
            f"    public void {feature_name.lower() if feature_name else 'page'}{method}() {{"
        )
        lines.append("        // TODO: verify expected API mapping")
        lines.append("        // TODO: verify DB assertion")
        lines.append("        // TODO: confirm authentication state")
        lines.append("    }")
        lines.append("")
    lines.append("}")
    return "\n".join(lines)


def _java_junit_test(
    class_name: str, feature_name: str, reuse_lines: list[str], opportunity: TestOpportunity | None
) -> str:
    scenarios = (opportunity.suggested_scenario_types if opportunity else None) or ["happy_path"]
    lines = [
        "package tests;",
        "",
        "import org.junit.jupiter.api.Test;",
        f"import pages.{class_name};",
        "// TODO: import the existing WebDriver/session setup this framework's other tests use",
        "// TODO: import the existing API client / DB validation utilities referenced below",
        "",
        f"// {_SCAFFOLD_NOTICE}",
    ]
    for line in reuse_lines:
        lines.append(f"// {line}")
    lines.append(f"public class {feature_name}Test {{")
    lines.append("")
    for scenario in scenarios:
        method = _pascal_case(scenario.replace("_", " "), fallback="Scenario")
        lines.append("    @Test")
        lines.append(f"    void {feature_name.lower() if feature_name else 'page'}{method}() {{")
        lines.append("        // TODO: verify expected API mapping")
        lines.append("        // TODO: verify DB assertion")
        lines.append("        // TODO: confirm authentication state")
        lines.append("    }")
        lines.append("")
    lines.append("}")
    return "\n".join(lines)


# --- Python (pytest + Playwright) ------------------------------------------


def _python_page_object(class_name: str, elements: list[_ElementPlan]) -> str:
    lines = [
        f'"""{_SCAFFOLD_NOTICE}"""',
        "",
        "from __future__ import annotations",
        "",
        "from framework.pages.base_page import BasePage",
        "",
        "",
        f"class {class_name}(BasePage):",
        "",
    ]
    for element in elements:
        comment = "TODO: verify locator" if element.needs_locator_review else "confirmed locator"
        constant = f"{element.slug.upper()} = {element.locator_value!r}"
        lines.append(f"    {constant}  # {comment} ({element.locator_strategy})")
    if elements:
        lines.append("")
    for element in elements:
        if element.is_input:
            lines.append(f"    def fill_{element.slug}(self, value: str) -> None:")
            lines.append("        # TODO: confirm test data")
            lines.append(
                f"        self.fill_locator(self.locator(self.{element.slug.upper()}), value)"
            )
        else:
            lines.append(f"    def click_{element.slug}(self) -> None:")
            lines.append(
                f"        self.click_locator(self.locator(self.{element.slug.upper()}), "
                f"description={('click_' + element.slug)!r})"
            )
        lines.append("")
    return "\n".join(lines)


def _python_pytest_test(
    module_name: str,
    class_name: str,
    page_slug: str,
    reuse_lines: list[str],
    opportunity: TestOpportunity | None,
) -> str:
    scenarios = (opportunity.suggested_scenario_types if opportunity else None) or ["happy_path"]
    lines = [
        f'"""{_SCAFFOLD_NOTICE}',
    ]
    for line in reuse_lines:
        lines.append(line)
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append(f"from pages.{module_name} import {class_name}")
    lines.append(
        "# TODO: import the existing API client / DB validation utilities referenced above"
    )
    lines.append("")
    lines.append("")
    for scenario in scenarios:
        test_name = f"test_{page_slug}_{scenario}"
        lines.append(f"def {test_name}(page) -> None:")
        lines.append(f"    scaffold = {class_name}(page)")
        lines.append("    # TODO: verify expected API mapping")
        lines.append("    # TODO: verify DB assertion")
        lines.append("    # TODO: confirm authentication state")
        lines.append("    del scaffold  # placeholder until the scenario above is implemented")
        lines.append("")
    return "\n".join(lines)


# --- TypeScript (Playwright) -------------------------------------------------


def _typescript_page_object(class_name: str, elements: list[_ElementPlan]) -> str:
    lines = [
        f"// {_SCAFFOLD_NOTICE}",
        "import { Page, Locator } from '@playwright/test';",
        "",
        f"export class {class_name} {{",
        "  readonly page: Page;",
    ]
    for element in elements:
        comment = "TODO: verify locator" if element.needs_locator_review else "confirmed locator"
        lines.append(
            f"  readonly {element.slug}: Locator; // {comment} ({element.locator_strategy})"
        )
    lines.append("")
    lines.append("  constructor(page: Page) {")
    lines.append("    this.page = page;")
    for element in elements:
        lines.append(f"    this.{element.slug} = {_ts_locator(element)};")
    lines.append("  }")
    lines.append("")
    for element in elements:
        if element.is_input:
            lines.append(
                f"  async fill{_pascal_case(element.slug)}(value: string): Promise<void> {{"
            )
            lines.append("    // TODO: confirm test data")
            lines.append(f"    await this.{element.slug}.fill(value);")
        else:
            lines.append(f"  async click{_pascal_case(element.slug)}(): Promise<void> {{")
            lines.append(f"    await this.{element.slug}.click();")
        lines.append("  }")
        lines.append("")
    lines.append("}")
    return "\n".join(lines)


def _ts_locator(element: _ElementPlan) -> str:
    if element.locator_strategy == "test_id":
        return f"page.getByTestId('{element.locator_value}')"
    if element.locator_strategy == "role":
        return f"page.getByRole('{element.locator_value}')"
    if element.locator_strategy == "label":
        return f"page.getByLabel('{element.locator_value}')"
    return f"page.locator('{element.locator_value}')"


def _typescript_test(
    module_name: str,
    class_name: str,
    feature_name: str,
    reuse_lines: list[str],
    opportunity: TestOpportunity | None,
) -> str:
    scenarios = (opportunity.suggested_scenario_types if opportunity else None) or ["happy_path"]
    lines = [
        f"// {_SCAFFOLD_NOTICE}",
        "import { test, expect } from '@playwright/test';",
        f"import {{ {class_name} }} from '../pages/{module_name}';",
        "// TODO: import the existing API client / DB validation utilities referenced below",
        "",
    ]
    for line in reuse_lines:
        lines.append(f"// {line}")
    lines.append(f"test.describe('{feature_name} (scaffold — review required)', () => {{")
    for scenario in scenarios:
        lines.append(f"  test('{scenario.replace('_', ' ')}', async ({{ page }}) => {{")
        lines.append(f"    const scaffold = new {class_name}(page);")
        lines.append("    // TODO: verify expected API mapping")
        lines.append("    // TODO: verify DB assertion")
        lines.append("    // TODO: confirm authentication state")
        lines.append("    void scaffold; // placeholder until the scenario above is implemented")
        lines.append("  });")
        lines.append("")
    lines.append("});")
    return "\n".join(lines)


# --- Robot Framework ---------------------------------------------------------


def _robot_resource(feature_name: str, elements: list[_ElementPlan]) -> str:
    lines = [
        "*** Settings ***",
        f"Documentation    {_SCAFFOLD_NOTICE}",
        "",
        "*** Keywords ***",
    ]
    for element in elements:
        keyword_name = element.label.replace("_", " ").title() or "Element"
        comment = "TODO: verify locator" if element.needs_locator_review else "confirmed locator"
        if element.is_input:
            lines.append(f"Fill {keyword_name}")
            lines.append(f"    [Documentation]    {comment} ({element.locator_strategy})")
            lines.append("    [Arguments]    ${value}")
            lines.append("    # TODO: confirm test data")
            lines.append(f"    Input Text    {_robot_locator(element)}    ${{value}}")
        else:
            lines.append(f"Click {keyword_name}")
            lines.append(f"    [Documentation]    {comment} ({element.locator_strategy})")
            lines.append(f"    Click Element    {_robot_locator(element)}")
        lines.append("")
    return "\n".join(lines)


def _robot_locator(element: _ElementPlan) -> str:
    if element.locator_strategy == "test_id":
        return f'css:[data-testid="{element.locator_value}"]'
    if element.locator_strategy == "css" and element.locator_value.startswith("#"):
        return f"id:{element.locator_value[1:]}"
    return f"css:{element.locator_value}"


def _robot_test(
    resource_name: str,
    feature_name: str,
    reuse_lines: list[str],
    opportunity: TestOpportunity | None,
) -> str:
    scenarios = (opportunity.suggested_scenario_types if opportunity else None) or ["happy_path"]
    lines = [
        "*** Settings ***",
        f"Documentation    {_SCAFFOLD_NOTICE}",
        f"Resource         ../resources/{resource_name}.resource",
        "# TODO: import the existing RequestsLibrary session / DB keywords referenced below",
        "",
    ]
    for line in reuse_lines:
        lines.append(f"# {line}")
    lines.append("")
    lines.append("*** Test Cases ***")
    for scenario in scenarios:
        title = f"{feature_name} {scenario.replace('_', ' ').title()}"
        lines.append(title)
        lines.append("    [Tags]    scaffold")
        lines.append("    # TODO: verify expected API mapping")
        lines.append("    # TODO: verify DB assertion")
        lines.append("    # TODO: confirm authentication state")
        lines.append("")
    return "\n".join(lines)


def _readme(target: ScaffoldTarget, manifest_filename: str) -> str:
    return (
        f"# Generated extension scaffold — {target.value}\n\n"
        f"{_SCAFFOLD_NOTICE}\n\n"
        "This directory was produced by `python -m framework extension scaffold`. "
        "Nothing here has been executed. Review every `TODO`, run the customer's normal "
        "test command against it, and only then treat it as real automation.\n\n"
        f"See `{manifest_filename}` for what was reused vs. newly generated, and which "
        "items still need manual review.\n"
    )


def build_scaffold_plan(
    analysis: RepositoryAnalysis,
    discovery_report: DiscoveryReport,
    extension_report: ExtensionReport,
    *,
    target: ScaffoldTarget | None = None,
) -> tuple[list[ScaffoldFile], ScaffoldManifest]:
    """Computes the full scaffold plan without touching disk — safe to call
    for a dry run. Only `UI_PAGE` items classified `CREATE_NEW`/
    `EXTEND_EXISTING` are scaffolded; everything else (REUSE_EXISTING,
    MANUAL_REVIEW, UNKNOWN, and every non-UI_PAGE subject) is recorded in
    the manifest only — this module never generates a second API client,
    DB layer, or auth mechanism (see the module docstring).
    """
    resolved_target = target or detect_scaffold_target(analysis)

    files: list[ScaffoldFile] = []
    reused: set[str] = set()
    generated: list[str] = []
    manual_review: list[str] = []

    for item in extension_report.extension_items:
        if (
            item.classification
            in (
                ExtensionClassification.REUSE_EXISTING,
                ExtensionClassification.EXTEND_EXISTING,
            )
            and item.matched_capability is not None
        ):
            reused.add(item.matched_capability.name)
        if item.classification in (
            ExtensionClassification.MANUAL_REVIEW,
            ExtensionClassification.UNKNOWN,
        ):
            manual_review.append(item.subject)

    scaffoldable_pages = [
        item
        for item in extension_report.extension_items
        if item.subject_type == ExtensionSubjectType.UI_PAGE
        and item.classification in _SCAFFOLDABLE_CLASSIFICATIONS
    ]

    for item in scaffoldable_pages:
        page = _find_discovered_page(item, discovery_report)
        if page is None:
            manual_review.append(f"{item.subject} (no matching discovery data — skipped)")
            continue

        elements = _plan_elements(page)
        class_name = _page_class_name(page)
        feature_name = _page_feature_name(page)
        page_slug = _slugify(_page_seed(page), fallback="new_page")
        reuse_lines = _related_reuse_lines(page, extension_report.extension_items)
        opportunity = _opportunity_for_page(page, extension_report.test_opportunities)

        page_file, test_file = _render_target_files(
            resolved_target, class_name, feature_name, page_slug, elements, reuse_lines, opportunity
        )
        if page_file is None and test_file is None:
            # No template for this target (e.g. UNKNOWN) — nothing was
            # actually generated, so this must not be claimed as such.
            manual_review.append(
                f"{item.subject} (no scaffold template for target {resolved_target.value})"
            )
            continue
        if page_file is not None:
            files.append(page_file)
        if test_file is not None:
            files.append(test_file)
        generated.append(item.subject)

    if resolved_target != ScaffoldTarget.UNKNOWN:
        files.append(
            ScaffoldFile(
                relative_path="README.md",
                kind=ScaffoldFileKind.README,
                content=_readme(resolved_target, "extension-manifest.json"),
            )
        )
    else:
        files.append(
            ScaffoldFile(
                relative_path="README.md",
                kind=ScaffoldFileKind.README,
                content=(
                    "# Generated extension scaffold — target undetected\n\n"
                    f"{_SCAFFOLD_NOTICE}\n\n"
                    "No supported language/framework/test-runner combination was confidently "
                    "detected in the existing repository, so no code was scaffolded. See "
                    "extension-manifest.json for the full reuse/extension analysis — build the "
                    "new UI's automation by hand, following the existing repository's own "
                    "conventions.\n"
                ),
            )
        )

    manifest = ScaffoldManifest(
        existing_framework_source=analysis.source,
        new_ui_source=discovery_report.source,
        target=resolved_target,
        files=[f.relative_path for f in files],
        reused_capabilities=sorted(reused),
        newly_generated_capabilities=generated,
        manual_review_items=manual_review,
    )
    return files, manifest


def _render_target_files(
    target: ScaffoldTarget,
    class_name: str,
    feature_name: str,
    page_slug: str,
    elements: list[_ElementPlan],
    reuse_lines: list[str],
    opportunity: TestOpportunity | None,
) -> tuple[ScaffoldFile | None, ScaffoldFile | None]:
    if target == ScaffoldTarget.JAVA_SELENIUM_TESTNG:
        page = ScaffoldFile(
            relative_path=f"pages/{class_name}.java",
            kind=ScaffoldFileKind.PAGE_OBJECT,
            content=_java_page_object(class_name, elements),
        )
        test = ScaffoldFile(
            relative_path=f"tests/{feature_name}Test.java",
            kind=ScaffoldFileKind.TEST,
            content=_java_testng_test(class_name, feature_name, reuse_lines, opportunity),
        )
        return page, test

    if target == ScaffoldTarget.JAVA_SELENIUM_JUNIT:
        page = ScaffoldFile(
            relative_path=f"pages/{class_name}.java",
            kind=ScaffoldFileKind.PAGE_OBJECT,
            content=_java_page_object(class_name, elements),
        )
        test = ScaffoldFile(
            relative_path=f"tests/{feature_name}Test.java",
            kind=ScaffoldFileKind.TEST,
            content=_java_junit_test(class_name, feature_name, reuse_lines, opportunity),
        )
        return page, test

    if target == ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT:
        module_name = f"{page_slug}_page"
        page = ScaffoldFile(
            relative_path=f"pages/{module_name}.py",
            kind=ScaffoldFileKind.PAGE_OBJECT,
            content=_python_page_object(class_name, elements),
        )
        test = ScaffoldFile(
            relative_path=f"tests/test_{page_slug}.py",
            kind=ScaffoldFileKind.TEST,
            content=_python_pytest_test(
                module_name, class_name, page_slug, reuse_lines, opportunity
            ),
        )
        return page, test

    if target == ScaffoldTarget.TYPESCRIPT_PLAYWRIGHT:
        module_name = f"{page_slug}_page"
        page = ScaffoldFile(
            relative_path=f"pages/{module_name}.ts",
            kind=ScaffoldFileKind.PAGE_OBJECT,
            content=_typescript_page_object(class_name, elements),
        )
        test = ScaffoldFile(
            relative_path=f"tests/{page_slug}.spec.ts",
            kind=ScaffoldFileKind.TEST,
            content=_typescript_test(
                module_name, class_name, feature_name, reuse_lines, opportunity
            ),
        )
        return page, test

    if target == ScaffoldTarget.ROBOT_FRAMEWORK:
        resource_name = page_slug
        resource = ScaffoldFile(
            relative_path=f"resources/{resource_name}.resource",
            kind=ScaffoldFileKind.RESOURCE,
            content=_robot_resource(feature_name, elements),
        )
        test = ScaffoldFile(
            relative_path=f"tests/{resource_name}.robot",
            kind=ScaffoldFileKind.TEST,
            content=_robot_test(resource_name, feature_name, reuse_lines, opportunity),
        )
        return resource, test

    return None, None


def write_scaffold_plan(
    files: list[ScaffoldFile],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> list[Path]:
    """Resolves every planned file's real path (project-root-contained,
    traversal-checked) and, unless `dry_run`, writes it. Overwrite
    protection is checked for *every* file before *any* file is written —
    a partial write that silently clobbers some but not all existing
    customer files would be worse than failing outright.
    """
    output_root = resolve_scaffold_output_dir(output_dir)
    targets = [safe_scaffold_target(output_root, f.relative_path) for f in files]

    if not overwrite:
        existing = [t for t in targets if t.exists()]
        if existing:
            joined = ", ".join(str(t) for t in existing)
            raise ConfigurationError(
                f"Refusing to overwrite existing file(s) without --overwrite: {joined}"
            )

    if dry_run:
        return targets

    for file, target_path in zip(files, targets, strict=True):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(file.content, encoding="utf-8")
    return targets
