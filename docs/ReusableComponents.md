# Reusable Components

Component Object catalog for this application, building on the generic 14
already in `framework/components/` (Milestone 3). Nothing here replaces
those — this maps *this app's* screens onto them and names the handful that
are genuinely new.

## Already covered by the existing generic component set

| Observed UI element | Existing component |
|---|---|
| Header bar (avatar, bell, doc, help, hamburger) | `HeaderComponent` |
| Tab bar (Steering overview / Steering insights) | `TopNavigationComponent` |
| Breadcrumb title (`Module \| Sub-page`) | `BreadcrumbComponent` (2-level case) |
| Quick-filter list + detail filter form | `SidebarComponent` (list) + a form composed of native inputs/`DropdownComponent` |
| Zone/results table | `TableComponent` — **already optimized** for bulk extraction (see the N+1 perf fix in the enterprise-readiness refactor); this app's tables are exactly the shape that fix targets |
| Tenant card grid | `GridComponent` |
| Network/tenant selector dropdown | `DropdownComponent` (non-native variant) |

## New components this app's screens justify

These don't exist yet in `framework/components/` and aren't reducible to the
existing 14 without losing meaning:

### `AppliedFiltersBarComponent`
The chip row under the header (`Home network + A01_Network_N1 (101-01) [x]`,
`Clear all`). Distinct from a generic "tag list" because chips can be
**compound** (one chip = multiple filter dimensions joined with `+`) and the
bar has both a per-chip remove and a global clear.

*Interface (documentation only — no implementation yet):*
- `chips() -> list[str]`
- `remove_chip(label: str) -> None`
- `clear_all() -> None`

### `QuickFilterListComponent`
A single-select list of icon+label presets where exactly one is active
(filled/dark background), functionally different from a checkbox list or a
`SidebarComponent`'s multi-item navigation (which doesn't track a single
"selected" state the way this does).

*Interface:*
- `select(label: str) -> None`
- `active_filter() -> str`
- `available_filters() -> list[str]`

### `TileLauncherComponent` / `PortalTileComponent`
The module-launcher grid on the portal. A `PortalTileComponent` is a single
tile (icon + label, click = navigate); `TileLauncherComponent` groups them
by section header (`Roaming products`, `SDS platform modules`,
`Security products`).

*Interface:*
- `TileLauncherComponent.tiles_in_section(section: str) -> list[str]`
- `TileLauncherComponent.open_module(name: str) -> None`

### `StatusCardComponent` (used by `CardGridComponent`)
A card with an icon-driven health state (green check / red triangle) plus a
label — the Tenants grid's building block. Kept distinct from
`PortalTileComponent` because its click semantics differ (select/switch
context vs. navigate to a module) even though the visual shape is similar.

*Interface:*
- `status() -> Literal["healthy", "needs_attention"]`
- `label() -> str`
- `select() -> None`

### `AccordionComponent` / `AccordionSectionComponent`
The portal's right-hand panel (Recent activity / Application logs / Failed
login attempts), each independently expandable.

*Interface:*
- `AccordionComponent.expand(section: str) -> None`
- `AccordionComponent.is_expanded(section: str) -> bool`
- `AccordionSectionComponent.content_table() -> TableComponent`

### `AlertIconComponent` / `StatusBadgeComponent`
Two small, high-reuse primitives: an icon-only status flag (the table's
"Needs attention" triangle — no visible text, must be asserted via
accessible name) and a coloured region/status tag (`EMEA`, `EU`). Worth
naming explicitly because "assert on an icon with no text" and "assert on a
coloured pill" are different enough problems that a generic `UIAssert.visible`
call would hide the actual intent of the check.

## Phase 5 — Enterprise DataTable framework

The existing `TableComponent` already covers headers/rows/cell/find/sort/
row-action extraction via one bulk `evaluate()` call (see the
enterprise-readiness refactor). What this app's Steering overview table adds
that isn't in `TableComponent` yet:

| Capability | Present today? | What's needed |
|---|---|---|
| Search | No | A `SearchBoxComponent` wired to the table's own search input, not assumed to be a separate global search |
| Sorting | Yes (`sort_by_column`) | Already covers click-to-sort; add a `sorted_by() -> str \| None` reader if the app exposes a sort-indicator icon, once seen |
| Pagination | Via `PaginationComponent`, not table-integrated | Compose `TableComponent` + `PaginationComponent` at the Page Object level rather than merging them — keeps each component single-purpose |
| Filters | No (filtering is external, via `FilterPanelComponent`) | Correct as designed — this app's filters live in the sidebar, not the table header, so they should stay a separate component the Page Object coordinates, not part of `TableComponent` itself |
| Export | No | `TableExportComponent.export() -> Path`, likely wrapping `BasePage.download_file()` (already exists) |
| Column selection | Not observed | Defer — no evidence this table supports hide/show columns |
| Checkbox / bulk selection | Not observed | Defer — no checkboxes visible in the captured table |
| Row actions | Yes (`click_row_action`) | Already covers a text-labelled action (`edit`/`delete`-style); this app's "Needs attention" icon isn't a row action, it's a status read — don't conflate them |
| Inline editing | Not observed | Defer |
| Context menu | Not observed | Defer |
| Reusable validation | Partial | `UIAssert.table_data()` already exists; add table-specific helpers only once a second table's shape is observed and the abstraction is confirmed, not before |

**Recommendation**: extend `TableComponent` incrementally (search, export)
rather than building a second "enterprise" table component — one table
abstraction, growing by evidence, is exactly the DRY principle the
enterprise-readiness refactor pass already enforced elsewhere in this
codebase. Do not add column-selection/checkbox/inline-edit/context-menu
support speculatively; there is zero screenshot evidence for any of them in
this app, and Milestone 3's own retrospective (skeleton modules with
invented UI) is the cautionary example for why that goes wrong.
