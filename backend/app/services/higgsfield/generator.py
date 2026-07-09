from dataclasses import dataclass
from typing import Any

from higgsfield_client import AsyncClient

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class HiggsfieldGenerationResult:
    request_id: str
    result_url: str
    raw_result: dict[str, Any]


class HiggsfieldGenerator:
    def __init__(
        self,
        client: AsyncClient | None = None,
        application: str = settings.higgsfield_application,
    ) -> None:
        self.client = client or AsyncClient()
        self.application = application

    async def generate(
        self,
        prompt: str,
        reference_image_url: str,
        aspect_ratio: str,
    ) -> HiggsfieldGenerationResult:
        controller = await self.client.submit(
            application=self.application,
            arguments={
                "prompt": prompt,
                "reference_image_url": reference_image_url,
                "aspect_ratio": aspect_ratio,
            },
        )
        result = await controller.get()
        result_url = self._extract_result_url(result)

        return HiggsfieldGenerationResult(
            request_id=controller.request_id,
            result_url=result_url,
            raw_result=result,
        )

    def _extract_result_url(self, result: dict[str, Any]) -> str:
        for key in (
            "result_url",
            "asset_url",
            "video_url",
            "image_url",
            "output_url",
            "url",
        ):
            value = result.get(key)
            if isinstance(value, str) and value:
                return value

        for key in ("result", "output", "data"):
            nested = result.get(key)
            if isinstance(nested, dict):
                try:
                    return self._extract_result_url(nested)
                except ValueError:
                    continue
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        try:
                            return self._extract_result_url(item)
                        except ValueError:
                            continue
                    if isinstance(item, str) and item.startswith(("http://", "https://")):
                        return item

        raise ValueError("Higgsfield response did not include a generated asset URL.")

