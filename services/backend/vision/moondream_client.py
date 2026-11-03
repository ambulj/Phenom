"""
Phenom Moondream2 Local VLM Client
Connects to Ollama for lightweight (~1.8B parameters, ~1.5 GB VRAM) in-memory visual comprehension.
Never writes screen captures to disk.
"""

import io
import base64
import time
from typing import Optional, Dict, Any, List
from PIL import Image
import httpx

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
DEFAULT_VISION_MODEL = "moondream"
AMBIENT_COPILOT_PROMPT = (
    "Analyze the active screen state. Identify the open application, active workflow, "
    "and highlight any visible compiler errors, exceptions, stack traces, warning dialogs, or blocker popups."
)


class MoondreamVisionClient:
    def __init__(self, model_name: str = DEFAULT_VISION_MODEL, endpoint_url: str = OLLAMA_GENERATE_URL):
        self.model_name = model_name
        self.endpoint_url = endpoint_url

    def encode_image_base64(self, img: Image.Image, max_dim: int = 1280, quality: int = 80) -> str:
        """
        Encodes a PIL Image to base64 JPEG in memory.
        Downscales proportionally if image exceeds max_dim to conserve VRAM and inference time.
        Strictly zero disk writes.
        """
        # Convert RGBA / BGRX to RGB
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Downscale if needed
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    async def query_image(
        self,
        img: Image.Image,
        prompt: str = "Describe what is on screen and highlight any errors, popups, or active buttons.",
        timeout: float = 25.0,
    ) -> Dict[str, Any]:
        """
        Sends an in-memory image to Moondream2 on Ollama.
        Returns a dict with description, model used, and status.
        """
        b64_image = self.encode_image_base64(img)
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": [b64_image],
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(self.endpoint_url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "").strip()
                    return {
                        "status": "success",
                        "model": self.model_name,
                        "description": response_text
                    }
                else:
                    return {
                        "status": "error",
                        "model": self.model_name,
                        "error": f"Ollama returned status {resp.status_code}: {resp.text}"
                    }
        except Exception as e:
            return {
                "status": "unavailable",
                "model": self.model_name,
                "error": str(e),
                "hint": f"Ensure Ollama is running and model '{self.model_name}' is installed (ollama pull {self.model_name})."
            }

    async def query_ambient_screen(
        self,
        img: Image.Image,
        prompt: Optional[str] = None,
        timeout: float = 15.0,
    ) -> Dict[str, Any]:
        """
        Specialized ambient co-pilot inference focusing on active workflow, error popups,
        and compiler messages with a strict 15.0s timeout and in-memory downscaling.
        """
        query_prompt = prompt or AMBIENT_COPILOT_PROMPT
        start_t = time.perf_counter()
        result = await self.query_image(img, prompt=query_prompt, timeout=timeout)
        latency_ms = (time.perf_counter() - start_t) * 1000.0

        description = result.get("description", "")
        detected_errors: List[str] = []
        if description:
            # Simple keyword extraction for error popups / warnings
            lines = [l.strip() for l in description.split("\n") if l.strip()]
            for line in lines:
                low = line.lower()
                if any(k in low for k in ["error", "exception", "failed", "traceback", "warning", "fatal", "syntaxerror"]):
                    detected_errors.append(line)

        return {
            "status": result.get("status", "error"),
            "model": self.model_name,
            "description": description,
            "detected_errors": detected_errors,
            "latency_ms": latency_ms,
            "error": result.get("error")
        }


moondream_client = MoondreamVisionClient()
