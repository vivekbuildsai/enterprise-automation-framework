from __future__ import annotations

from playwright.sync_api import Locator, Page

from framework.components.base_component import BaseComponent


class TreeViewComponent(BaseComponent):
    """Expandable hierarchical tree (e.g. an org chart, a network topology
    browser). Nodes are addressed by their visible label via the
    `treeitem` ARIA role, so the component works with any tree that follows
    the standard accessibility pattern rather than one specific tree
    library's DOM shape.
    """

    def __init__(self, page: Page, root_selector: str = "[role='tree']") -> None:
        super().__init__(page, root_selector)

    def _node(self, label: str) -> Locator:
        return self.root.get_by_role("treeitem", name=label)

    def select_node(self, label: str) -> None:
        self._node(label).click()

    def expand_node(self, label: str) -> None:
        node = self._node(label)
        if node.get_attribute("aria-expanded") == "false":
            node.click()

    def collapse_node(self, label: str) -> None:
        node = self._node(label)
        if node.get_attribute("aria-expanded") == "true":
            node.click()

    def is_node_expanded(self, label: str) -> bool:
        return self._node(label).get_attribute("aria-expanded") == "true"

    def visible_nodes(self) -> list[str]:
        return self.root.get_by_role("treeitem").all_inner_texts()
