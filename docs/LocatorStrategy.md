# Locator Strategy

## Priority order (unchanged from Milestone 3's `framework/locators/Locators`)

1. `data-testid` / `get_by_test_id()`
2. `get_by_role()`
3. `get_by_label()`
4. `get_by_placeholder()`
5. `get_by_text()`
6. CSS
7. XPath — last resort, logged as a warning when used

This document doesn't change that priority. What it adds is *why it matters
more than usual for this specific app*, and the one hard blocker screenshots
alone can't resolve.

## The blocker: these are photographs, not DOM exports

Every screenshot is a photo of a physical monitor — there is no HTML,
no devtools inspection, no accessible-name data available from them. That
means **zero real selectors can be written from this material**. Every
locator example anywhere in this documentation set is illustrative
(`[data-testid='...']`-shaped placeholders), not observed fact — same
caveat Milestone 3 already applies to its 6 skeleton modules, now correctly
extended to this real app too. Actual locator work cannot start until one of:

- Real environment access (browser devtools against the live app), or
- An HTML/DOM export from someone with access, or
- A recorded Playwright trace/HAR from a manual session

is available. This is the top item in [RiskAnalysis.md](RiskAnalysis.md).

## Why role/label-first still wins here specifically

- **Icon-only header controls** (bell, document, help `?`, hamburger) have
  no visible text — `get_by_role("button", name=...)` only works if the app
  sets a real `aria-label`; if it doesn't, this becomes a CSS/`title`-attribute
  fallback in practice, which is worth flagging to the dev team as an
  accessibility gap *before* it becomes an automation blocker (this is
  exactly the kind of finding `AccessibilityChecker` — already built in
  Milestone 3 — exists to surface).
- **Table cells are hyperlink-styled text** (zone names, CoS names) —
  `get_by_role("link", name=...)` or `get_by_text()` scoped to a row is far
  more resilient than a CSS nth-child chain, especially given rows re-sort
  and re-filter constantly (see Workflow 1 in
  [BusinessFlow.md](BusinessFlow.md)).
- **Chips need scoped, not global, text matching** — the applied-filters bar
  can hold multiple chips; `get_by_text("Clear all")` is safe (one instance),
  but a chip's `[x]` remove control must be scoped to its parent chip
  (`chip_locator.get_by_role("button")`) or a filter test risks removing the
  wrong chip when more than one is present.
- **Quick-filter "active" state is a class/style toggle, not a form control**
  — there's no checkbox/radio to hook into; locating by `get_by_text(label)`
  to click, and reading active state via `get_attribute("class")` or
  `aria-selected` (whichever the real DOM uses), is the only viable approach
  — confirmed pattern already used in `SidebarComponent.is_item_active()`
  from Milestone 3.
- **Portal tiles' only identifying feature is their label text** — the icons
  are purely decorative/non-unique (several share similar shapes), so
  `get_by_role("link", name="Reports")`-style, not `nth-child` position in
  the grid, must be the locator — tile order looks configurable/personalizable
  (a launcher grid usually is), so position-based locators would be
  actively dangerous here, not just less ideal.

## data-testid: recommend, but can't confirm yet

Nothing in the photographs proves or disproves whether the real app ships
`data-testid` attributes. Recommend the QA/dev teams confirm this in the
first real access session — if present, it should be priority 1 as already
documented; if absent, `get_by_role`/`get_by_text` carry more of the load
than usual, and a `data-testid` adoption ask to the dev team becomes a
legitimate, evidence-backed recommendation (see
[RiskAnalysis.md](RiskAnalysis.md) and
[FutureAutomationRoadmap.md](FutureAutomationRoadmap.md)).
