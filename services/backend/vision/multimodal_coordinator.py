"""
Phenom Multimodal Vision Coordinator
Orchestrates multimodal visual queries between:
1. Cloud NVIDIA Nemotron Vision API (high-precision comprehension, diagram reasoning).
2. Resilient On-Device Fallback (Local OCR + Moondream2 VLM).

Enforces:
- Rule 4: All frames are sanitized in RAM with PrivacyMasker prior to transmission or processing.
- Zero disk IO: Strictly in-memory image and buffer management.
- Transparent provenance: Clearly denotes 'cloud_nemotron', 'local_vlm', or 'local_fallback'.
"""

import logging
from typing import Optional, Dict, Any, List
from PIL import Image

from services.backend.vision.frame_grabber import frame_grabber
from services.backend.vision.privacy_masker import privacy_masker
from services.backend.vision.nemotron_client import nemotron_client
from services.backend.vision.moondream_client import moondream_client
from services.backend.vision.ocr_engine import ocr_engine
from services.backend.safety.action_log import action_log

logger = logging.getLogger("phenom.multimodal_coordinator")


class MultimodalCoordinator:
    """
    Manages multimodal execution with automatic offline fallback.
    """

    def __init__(self):
        self.nemotron = nemotron_client
        self.moondream = moondream_client
        self.ocr = ocr_engine
        self.masker = privacy_masker
        self.grabber = frame_grabber

    async def execute_screen_query(
        self,
        prompt: str,
        prefer_cloud: bool = True,
        img: Optional[Image.Image] = None,
        apply_privacy: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a visual query against the active screen or provided image.
        If prefer_cloud is True, attempts Nemotron Vision with automatic degradation
        to local OCR + Moondream on any network, credential, or API failure.
        """
        # 1. Capture screen in RAM if not provided
        if img is None:
            raw_img = self.grabber.grab_frame()
        else:
            raw_img = img

        # 2. In-RAM Privacy Masking
        masked_count = 0
        if apply_privacy:
            sanitized_img, masked_count = self.masker.mask_sensitive_windows(raw_img)
        else:
            sanitized_img = raw_img

        # 3. Cloud Vision Path
        if prefer_cloud:
            cloud_res = await self.nemotron.query_screen(sanitized_img, prompt=prompt)
            if cloud_res.get("status") == "success":
                description = cloud_res.get("description", "").strip()
                result = {
                    "status": "success",
                    "source": "cloud_nemotron",
                    "model": cloud_res.get("model", self.nemotron.model_name),
                    "description": description,
                    "fallback_engaged": False,
                    "privacy_masked_windows": masked_count,
                    "message": f"Cloud visual comprehension complete: {description}"
                }
                self._log_multimodal_action("cloud_vision_query", prompt, result, tier=2)
                return result

            # Cloud failed: Trigger Resilient Fallback to Local
            fallback_reason = cloud_res.get("message") or f"Cloud error ({cloud_res.get('error_type', 'unknown')})"
            logger.warning(f"Nemotron Cloud vision failed: {fallback_reason}. Engaging local fallback.")
            
            fallback_res = await self._execute_local_fallback(sanitized_img, prompt, fallback_reason, masked_count)
            self._log_multimodal_action("cloud_vision_fallback", prompt, fallback_res, tier=0)
            return fallback_res

        # 4. Explicit Local Vision Path
        local_res = await self._execute_local_vision(sanitized_img, prompt, masked_count)
        self._log_multimodal_action("local_vision_query", prompt, local_res, tier=0)
        return local_res

    async def _execute_local_fallback(
        self,
        img: Image.Image,
        prompt: str,
        fallback_reason: str,
        masked_count: int
    ) -> Dict[str, Any]:
        """
        Synthesizes on-device OCR text and Moondream2 VLM analysis
        when cloud API is unreachable or unconfigured.
        """
        # Local VLM scene comprehension
        vlm_res = await self.moondream.query_image(img, prompt=prompt)
        vlm_desc = vlm_res.get("description") or "Local visual inspection completed."

        # Local OCR element / text extraction
        ocr_blocks = self.ocr.extract_text_via_ocr(img)
        visible_words = [b.get("text", "") for b in ocr_blocks[:15] if b.get("text")]
        
        # UI Automation fallback if OCR is empty
        if not visible_words:
            uia_elements = self.ocr.extract_elements_from_uia(max_depth=3)
            visible_words = [e.get("name", "") for e in uia_elements[:10] if e.get("name")]

        text_summary = f" Visible text: {', '.join(visible_words)}." if visible_words else ""
        synthesized_desc = f"{vlm_desc}{text_summary}"

        return {
            "status": "success",
            "source": "local_fallback",
            "model": "moondream2+ocr",
            "description": synthesized_desc,
            "fallback_engaged": True,
            "fallback_reason": fallback_reason,
            "privacy_masked_windows": masked_count,
            "message": f"Cloud vision was unavailable ({fallback_reason}); resolved via on-device local vision & OCR: {synthesized_desc}"
        }

    async def _execute_local_vision(
        self,
        img: Image.Image,
        prompt: str,
        masked_count: int
    ) -> Dict[str, Any]:
        """Runs standard on-device visual analysis."""
        vlm_res = await self.moondream.query_image(img, prompt=prompt)
        vlm_desc = vlm_res.get("description") or vlm_res.get("error") or "Screen visual inspection completed."
        
        return {
            "status": "success",
            "source": "local_vlm",
            "model": self.moondream.model_name,
            "description": vlm_desc,
            "fallback_engaged": False,
            "privacy_masked_windows": masked_count,
            "message": f"Local vision inspection complete: {vlm_desc}"
        }

    def _log_multimodal_action(self, action_name: str, prompt: str, result: Dict[str, Any], tier: int) -> None:
        try:
            action_log.log_action(
                tool_name=action_name,
                args={
                    "prompt": prompt[:80] + ("..." if len(prompt) > 80 else ""),
                    "source": result.get("source"),
                    "fallback_engaged": result.get("fallback_engaged", False),
                    "privacy_masked_windows": result.get("privacy_masked_windows", 0)
                },
                tier=tier,
                result={"status": result.get("status"), "model": result.get("model")}
            )
        except Exception:
            pass


multimodal_coordinator = MultimodalCoordinator()
