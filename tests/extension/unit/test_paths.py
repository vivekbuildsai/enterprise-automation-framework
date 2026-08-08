"""Path-containment guarantees for scaffold output — generated customer
automation must always land inside the customer's own project, never in
this package's own installed location, and never escape via traversal.
`PROJECT_ROOT` is patched directly on `framework.extension.paths` (the
name as bound into that module's own namespace via `from ... import`,
same pattern `tests/config/unit/test_project_root.py` uses for other
`PROJECT_ROOT`-dependent modules).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.exceptions import ConfigurationError
from framework.extension import paths as paths_module
from framework.extension.paths import resolve_scaffold_output_dir, safe_scaffold_target

pytestmark = pytest.mark.extension


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "customer-project"
    root.mkdir()
    monkeypatch.setattr(paths_module, "PROJECT_ROOT", root)
    return root


def test_relative_output_dir_resolves_under_project_root(project_root: Path) -> None:
    resolved = resolve_scaffold_output_dir("generated/extension")
    assert resolved == project_root / "generated" / "extension"


def test_absolute_output_dir_inside_project_root_is_accepted(project_root: Path) -> None:
    target = project_root / "artifacts" / "extension"
    resolved = resolve_scaffold_output_dir(target)
    assert resolved == target


def test_relative_output_dir_escaping_via_dotdot_is_refused(project_root: Path) -> None:
    with pytest.raises(ConfigurationError, match="outside the project root"):
        resolve_scaffold_output_dir("../outside")


def test_absolute_output_dir_outside_project_root_is_refused(
    project_root: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "somewhere-else"
    outside.mkdir()
    with pytest.raises(ConfigurationError, match="outside the project root"):
        resolve_scaffold_output_dir(outside)


def test_output_dir_equal_to_project_root_itself_is_accepted(project_root: Path) -> None:
    resolved = resolve_scaffold_output_dir(project_root)
    assert resolved == project_root


def test_safe_scaffold_target_accepts_a_normal_relative_path(tmp_path: Path) -> None:
    target = safe_scaffold_target(tmp_path, "pages/EmployeePage.java")
    assert target == (tmp_path / "pages" / "EmployeePage.java").resolve()


def test_safe_scaffold_target_refuses_dotdot_traversal(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="path traversal"):
        safe_scaffold_target(tmp_path, "../../etc/passwd")


def test_safe_scaffold_target_refuses_an_absolute_path_escaping_root(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="path traversal"):
        safe_scaffold_target(tmp_path, "/etc/passwd")


def test_safe_scaffold_target_refuses_a_page_title_derived_traversal_attempt(
    tmp_path: Path,
) -> None:
    """A malicious/unusual discovered page title (`"../../../etc/passwd"`)
    must never be able to escape the output root just because it ended up
    embedded in a generated relative path.
    """
    with pytest.raises(ConfigurationError, match="path traversal"):
        safe_scaffold_target(tmp_path, "pages/../../../../etc/passwd")
