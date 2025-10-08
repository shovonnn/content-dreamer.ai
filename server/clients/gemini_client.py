from dataclasses import dataclass
from typing import Optional
import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from config import logger


@dataclass
class VideoResult:
    # path to a generated mp4 file
    file_path: str
    model: str


class GeminiClient:
    """Thin wrapper for Gemini Veo 3 video generation.

    NOTE: This is a stub. Replace with actual Gemini SDK calls when available.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

    def generate_video(self, prompt: str, duration_seconds: int = 8, aspect_ratio: str = "9:16") -> VideoResult:
        """Generate a short video using Gemini Veo 3 and save to disk.

        Note:
            - Veo 3 currently produces ~8s clips; `duration_seconds` is accepted
              for API parity but not forwarded if unsupported by the model.
            - Supported aspect ratios per docs: "16:9" (720p/1080p) and "9:16" (720p).
        """
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set.")

        # Normalize aspect ratio input
        ar = aspect_ratio.strip()
        if ar not in ("16:9", "9:16"):
            raise ValueError(f"Unsupported aspect_ratio '{aspect_ratio}'. Use '16:9' or '9:16'.")

        # Choose resolution: 1080p only supported for 16:9, else fallback to 720p.
        # (If Google later enables 1080p for 9:16, this can be relaxed.)
        resolution = "1080p" if ar == "16:9" else "720p"

        # Initialize client with API key
        client = genai.Client(api_key=self.api_key)

        # Prepare output directory and filename
        out_dir = Path("generated_videos")
        out_dir.mkdir(parents=True, exist_ok=True)
        # Safe filename stub
        ts = int(time.time())
        fname = out_dir / f"veo3_{ts}.mp4"

        try:
            # Build config. Do NOT pass duration; the model fixes clip length (~8s).
            config = types.GenerateVideosConfig(aspect_ratio=ar, resolution=resolution)

            # Start long-running generation operation
            operation = client.models.generate_videos(
                model="veo-3.0-generate-001",
                prompt=prompt,
                config=config,
            )

            # Poll until done
            while not operation.done:
                time.sleep(10)  # per docs: poll every ~10s
                operation = client.operations.get(operation)

            if operation.error:
                raise RuntimeError(f"Veo 3 generation error: {operation.error.message}")

            logger.info(f"Veo 3 generation succeeded: {operation.response}")

            # Retrieve first generated video
            generated_video = operation.response.generated_videos[0]

            # Download and save
            client.files.download(file=generated_video.video)
            generated_video.video.save(str(fname))

            return VideoResult(file_path=str(fname), model="veo-3.0-generate-001")

        except Exception as e:
            # Re-wrap to make caller logs clearer while preserving original cause
            raise RuntimeError(f"Veo 3 video generation failed: {e}") from e
