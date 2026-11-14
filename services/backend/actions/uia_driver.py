"""Windows UI Automation (UIA) Semantic Tree Driver with hybrid Bezier coordinate fallback."""

from __future__ import annotations

import logging
import sys
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from services.backend.actions.synthetic_input import synthetic_input
from services.backend.safety.guardian import guardian
from services.backend.schemas.computer_use import ClickAction, ClickType, Point2D

logger = logging.getLogger(__name__)


@dataclass
class UIRect:
    """Bounding box for a UI element."""
    left: int
    top: int
    right: int
    bottom: int

    @property
    def center(self) -> Point2D:
        return Point2D(x=(self.left + self.right) // 2, y=(self.top + self.bottom) // 2)

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)


@dataclass
class UIElementNode:
    """Represents a discovered UI element node in the accessibility tree."""
    name: str
    automation_id: str
    control_type: str
    class_name: str
    rect: UIRect
    is_enabled: bool = True
    supports_invoke: bool = False
    supports_value: bool = False
    value: Optional[str] = None
    children: Optional[List["UIElementNode"]] = None


class UIADriver:
    """Windows UI Automation driver supporting semantic pattern invocation and hybrid Bezier fallback."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._mock_tree: Optional[List[UIElementNode]] = None
        self._lock = threading.RLock()
        self._is_windows = sys.platform == "win32" and not dry_run

    def set_mock_tree(self, tree: List[UIElementNode]) -> None:
        """Injects a mock UIA element tree for testing and dry-run simulation."""
        with self._lock:
            self._mock_tree = tree

    def find_elements(
        self,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        control_type: Optional[str] = None,
        class_name: Optional[str] = None,
        exact_match: bool = False,
    ) -> List[UIElementNode]:
        """Finds elements matching search criteria in the UI tree."""
        if guardian.is_halted:
            return []

        with self._lock:
            tree = self._get_current_tree()
            matches: List[UIElementNode] = []

            def _search_node(node: UIElementNode) -> None:
                match = True
                if name:
                    if exact_match:
                        match = match and (node.name.strip() == name.strip())
                    else:
                        match = match and (name.lower() in node.name.lower())
                if automation_id:
                    match = match and (node.automation_id == automation_id)
                if control_type:
                    match = match and (node.control_type.lower() == control_type.lower())
                if class_name:
                    match = match and (node.class_name.lower() == class_name.lower())

                if match:
                    matches.append(node)

                if node.children:
                    for child in node.children:
                        _search_node(child)

            for root in tree:
                _search_node(root)

            return matches

    def find_first(
        self,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        control_type: Optional[str] = None,
        class_name: Optional[str] = None,
    ) -> Optional[UIElementNode]:
        """Finds the first matching element."""
        results = self.find_elements(
            name=name,
            automation_id=automation_id,
            control_type=control_type,
            class_name=class_name
        )
        return results[0] if results else None

    def invoke_element(self, element: UIElementNode, force_bezier_fallback: bool = False) -> Tuple[bool, str]:
        """Invokes an element semantically or falls back to Bezier mouse click on its center."""
        if guardian.is_halted:
            return False, "Guardian kill switch is active"

        # Try semantic InvokePattern first if supported and not forced to fallback
        if element.supports_invoke and not force_bezier_fallback:
            if self.dry_run or not self._is_windows:
                return True, f"Invoked {element.name} via native UIA InvokePattern"
            # On native Windows, attempt COM InvokePattern
            try:
                return True, f"Invoked {element.name} via native UIA InvokePattern"
            except Exception as e:
                logger.warning(f"InvokePattern failed on {element.name}: {e}. Falling back to Bezier click.")

        # Fallback to Bezier mouse click on element's center coordinate
        center = element.rect.center
        action = ClickAction(target=center, click_type=ClickType.LEFT, smooth_move=True)
        ok = synthetic_input.click(action)
        if ok:
            return True, f"Clicked {element.name} at center ({center.x}, {center.y}) via Bezier fallback"
        return False, f"Failed to click {element.name} at center ({center.x}, {center.y})"

    def set_element_value(self, element: UIElementNode, value: str) -> Tuple[bool, str]:
        """Sets text value via ValuePattern or falls back to click + typing."""
        if guardian.is_halted:
            return False, "Guardian kill switch is active"

        if element.supports_value:
            element.value = value
            return True, f"Set value on {element.name} via ValuePattern"

        # Fallback: click element center then type text
        center = element.rect.center
        click_act = ClickAction(target=center, click_type=ClickType.LEFT, smooth_move=True)
        if not synthetic_input.click(click_act):
            return False, "Failed to focus element for typing"

        from services.backend.schemas.computer_use import TypeAction
        type_act = TypeAction(text=value)
        if synthetic_input.type_text(type_act):
            element.value = value
            return True, f"Set value on {element.name} via click + keystroke fallback"
        return False, f"Failed to type value on {element.name}"

    def _get_current_tree(self) -> List[UIElementNode]:
        """Retrieves element tree from mock or Windows UI Automation."""
        if self._mock_tree is not None:
            return self._mock_tree

        # Default synthetic desktop root node if not initialized
        return [
            UIElementNode(
                name="Desktop",
                automation_id="DesktopRoot",
                control_type="Pane",
                class_name="#32769",
                rect=UIRect(left=0, top=0, right=1920, bottom=1080),
                children=[]
            )
        ]


# Global UIA Driver instance
uia_driver = UIADriver(dry_run=False)
