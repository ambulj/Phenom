"""
Phenom NVIDIA Nemotron Vision API Client
Targeting NVIDIA Multimodal API (build.nvidia.com / integrate.api.nvidia.com).
Enforces:
1. Zero disk IO: frames are serialized to JPEG base64 strictly in-memory.
2. Secure credential storage: reads API key from Windows Credential Manager ('Phenom/nemotron-api-key')
   with fallback to NVIDIA_API_KEY / NEMOTRON_API_KEY environment variables.
3. OpenAI-compatible multimodal chat completions payload structure.
4. Comprehensive exception and timeout handling for offline/network-loss scenarios.
"""

import os
import io
import base64
import logging
from typing import Optional, Dict, Any
from PIL import Image
import httpx

from services.backend.remote.credentials import get_credential, set_credential

logger = logging.getLogger("phenom.nemotron")

NVIDIA_DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_NEMOTRON_MODEL = "nvidia/neva-22b"
CREDENTIAL_TARGET = "nemotron-api-key"


class NemotronVisionClient:
    """
    Cloud multimodal client for NVIDIA Nemotron / NeVA vision models.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.endpoint_url = endpoint_url or os.environ.get("NEMOTRON_ENDPOINT_URL", NVIDIA_DEFAULT_BASE_URL)
        self.model_name = model_name or os.environ.get("NVIDIA_VISION_MODEL", DEFAULT_NEMOTRON_MODEL)

    def get_api_key(self) -> Optional[str]:
        """
        Retrieves the NVIDIA API key from:
        1. Windows Credential Manager target 'Phenom/nemotron-api-key' (or SQLCipher DB fallback).
        2. Environment variable 'NVIDIA_API_KEY'.
        3. Environment variable 'NEMOTRON_API_KEY'.
        """
        cred_key = get_credential(CREDENTIAL_TARGET)
        if cred_key and cred_key.strip():
            return cred_key.strip()

        env_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NEMOTRON_API_KEY")
        if env_key and env_key.strip():
            return env_key.strip()

        return None

    def set_api_key(self, api_key: str) -> None:
        """Stores the NVIDIA API key in Windows Credential Manager."""
        set_credential(CREDENTIAL_TARGET, api_key.strip())

    def encode_image_base64(self, img: Image.Image, max_dim: int = 1280, quality: int = 80) -> str:
        """
        Encodes a PIL Image to base64 JPEG in RAM.
        Proportionally scales down image if dimensions exceed max_dim.
        Zero disk IO.
        """
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def build_payload(self, b64_image: str, prompt: str) -> Dict[str, Any]:
        """Constructs OpenAI-compatible multimodal payload."""
        return {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.2
        }

    async def query_screen(
        self,
        img: Image.Image,
        prompt: str = "Analyze this screen and describe key visual elements, dialogs, diagrams, or errors.",
        timeout_seconds: float = 25.0
    ) -> Dict[str, Any]:
        """
        Sends an in-RAM screen image to NVIDIA Nemotron Vision API.
        Returns structured dict with response text or typed error info.
        """
        api_key = self.get_api_key()
        if not api_key:
            return {
                "status": "error",
                "error_type": "no_api_key",
                "message": "NVIDIA API key not configured in Windows Credential Manager or environment."
            }

        b64_image = self.encode_image_base64(img)
        payload = self.build_payload(b64_image, prompt)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(self.endpoint_url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content", "").strip()
                        return {
                            "status": "success",
                            "model": self.model_name,
                            "description": content,
                            "usage": data.get("usage", {})
                        }
                    return {
                        "status": "error",
                        "error_type": "empty_response",
                        "message": "API returned 200 but choices array was empty."
                    }
                else:
                    return {
                        "status": "error",
                        "error_type": "http_error",
                        "status_code": resp.status_code,
                        "message": f"NVIDIA API responded with status {resp.status_code}: {resp.text[:200]}"
                    }
        except httpx.TimeoutException:
            return {
                "status": "error",
                "error_type": "timeout",
                "message": f"NVIDIA API request timed out after {timeout_seconds}s."
            }
        except httpx.RequestError as e:
            return {
                "status": "error",
                "error_type": "network_error",
                "message": f"Network error connecting to NVIDIA API: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": "unhandled_exception",
                "message": f"Unexpected error during Nemotron query: {str(e)}"
            }


nemotron_client = NemotronVisionClient()
