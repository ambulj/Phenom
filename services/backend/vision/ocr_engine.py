"""
Phenom Screen OCR & Coordinate Extraction Engine
Provides rapid coordinate localization for UI elements (buttons, inputs, labels)
using in-memory screen analysis and Windows UI Automation.
"""

from typing import List, Dict, Any, Optional
from PIL import Image
import numpy as np

try:
    import uiautomation as auto
except ImportError:
    auto = None

try:
    import easyocr
except ImportError:
    easyocr = None


class ScreenOCREngine:
    def __init__(self):
        self._reader = None

    def _get_reader(self):
        if self._reader is None and easyocr:
            try:
                self._reader = easyocr.Reader(["en"], gpu=False)
            except Exception:
                self._reader = None
        return self._reader

    def extract_elements_from_uia(self, max_depth: int = 4) -> List[Dict[str, Any]]:
        """
        Scans top-level active Windows controls using Windows UI Automation.
        Returns a list of interactive elements with names, control types, and bounding rectangles.
        """
        elements: List[Dict[str, Any]] = []
        if not auto:
            return elements

        try:
            root = auto.GetRootControl()
            focused = auto.GetFocusedControl()
            target_root = focused.GetTopLevelControl() if focused else root

            def walk(control, depth=0):
                if depth > max_depth:
                    return
                try:
                    name = control.Name.strip() if control.Name else ""
                    rect = control.BoundingRectangle
                    if name and rect and (rect.right - rect.left > 0) and (rect.bottom - rect.top > 0):
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        cx = rect.left + (w // 2)
                        cy = rect.top + (h // 2)
                        elements.append({
                            "name": name,
                            "control_type": control.ControlTypeName,
                            "x": cx,
                            "y": cy,
                            "bbox": [rect.left, rect.top, w, h],
                            "method": "ui_automation"
                        })
                    for child in control.GetChildren():
                        walk(child, depth + 1)
                except Exception:
                    pass

            walk(target_root, 0)
        except Exception:
            pass

        return elements

    def extract_text_via_ocr(self, img: Image.Image) -> List[Dict[str, Any]]:
        """
        Extracts words and bounding boxes from an in-memory PIL image using easyocr.
        """
        results: List[Dict[str, Any]] = []
        reader = self._get_reader()
        if not reader:
            return results

        try:
            arr = np.array(img)
            ocr_res = reader.readtext(arr)
            for item in ocr_res:
                bbox, text, conf = item
                text_clean = str(text).strip()
                if text_clean and conf > 0.3:
                    x1 = int(bbox[0][0])
                    y1 = int(bbox[0][1])
                    x2 = int(bbox[2][0])
                    y2 = int(bbox[2][1])
                    w = x2 - x1
                    h = y2 - y1
                    results.append({
                        "name": text_clean,
                        "text": text_clean,
                        "x": x1 + (w // 2),
                        "y": y1 + (h // 2),
                        "bbox": [x1, y1, w, h],
                        "confidence": float(conf),
                        "method": "ocr"
                    })
        except Exception:
            pass

        return results

    def find_element_coordinates(self, target: str, img: Optional[Image.Image] = None) -> Optional[Dict[str, Any]]:
        """
        Locates an element by name or substring.
        Prioritizes UI Automation for pixel-exact OS controls, then falls back to OCR.
        """
        clean_target = target.strip().lower()

        # 1. Try Windows UI Automation
        uia_elements = self.extract_elements_from_uia()
        for elem in uia_elements:
            if clean_target == elem["name"].lower():
                return elem
        for elem in uia_elements:
            if clean_target in elem["name"].lower():
                return elem

        # 2. Try OCR if image provided
        if img:
            ocr_elements = self.extract_text_via_ocr(img)
            for elem in ocr_elements:
                if clean_target == elem["text"].lower():
                    return elem
            for elem in ocr_elements:
                if clean_target in elem["text"].lower():
                    return elem

        return None


ocr_engine = ScreenOCREngine()
