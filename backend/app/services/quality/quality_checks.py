import re
from datetime import timedelta
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.schemas import (
    QualityCheckItemRead,
    QualityCheckRequest,
    QualityCheckResultRead,
    QualityStatus,
)

ASPECT_RATIO_TOLERANCE = 0.03
DISCOUNT_PATTERN = re.compile(
    r"(\bdiscount\b|\bsale\b|\boffer\b|\bpromo\b|\bdeal\b|\b\d{1,2}%\s*off\b)",
    re.IGNORECASE,
)


class QualityCheckService:
    def evaluate(self, payload: QualityCheckRequest) -> QualityCheckResultRead:
        checks = [
            self._check_file_exists(payload),
            self._check_file_opens(payload),
            self._check_aspect_ratio(payload),
            self._check_minimum_resolution(payload),
            self._check_caption_not_empty(payload),
            self._check_product_url(payload),
            self._check_duplicate_caption(payload),
            self._check_discount_claim(payload),
        ]
        score = max(0, min(100, 100 + sum(check.score_delta for check in checks)))

        return QualityCheckResultRead(
            score=score,
            status=self._status(score),
            manual_approval_required=True,
            checks=checks,
        )

    def _check_file_exists(self, payload: QualityCheckRequest) -> QualityCheckItemRead:
        if payload.asset_file_path and Path(payload.asset_file_path).is_file():
            return self._pass("file_exists", "Asset file exists.")

        if payload.asset_url:
            return self._warning(
                "file_exists",
                "Remote asset URL provided; storage existence must be verified by fetch.",
                -5,
            )

        return self._fail("file_exists", "Asset file does not exist.", -20)

    def _check_file_opens(self, payload: QualityCheckRequest) -> QualityCheckItemRead:
        if not payload.asset_file_path:
            return self._warning(
                "file_opens",
                "No local file path provided for open validation.",
                -5,
            )

        path = Path(payload.asset_file_path)
        if not path.is_file():
            return self._fail("file_opens", "Asset file cannot be opened.", -20)

        if payload.asset_type == "video":
            if path.stat().st_size > 0:
                return self._pass("file_opens", "Video file exists and is non-empty.")
            return self._fail("file_opens", "Video file is empty.", -20)

        try:
            with Image.open(path) as image:
                image.verify()
        except (OSError, UnidentifiedImageError):
            return self._fail("file_opens", "Image file could not be opened.", -20)

        return self._pass("file_opens", "Image file opens successfully.")

    def _check_aspect_ratio(self, payload: QualityCheckRequest) -> QualityCheckItemRead:
        dimensions = self._dimensions(payload)
        if dimensions is None:
            return self._fail(
                "correct_aspect_ratio",
                "Cannot verify aspect ratio without dimensions.",
                -15,
            )

        width, height = dimensions
        try:
            expected_width, expected_height = self._parse_aspect_ratio(
                payload.expected_aspect_ratio,
            )
        except ValueError as exc:
            return self._fail(
                "correct_aspect_ratio",
                str(exc),
                -15,
            )
        actual_ratio = width / height
        expected_ratio = expected_width / expected_height
        delta = abs(actual_ratio - expected_ratio) / expected_ratio

        if delta <= ASPECT_RATIO_TOLERANCE:
            return self._pass(
                "correct_aspect_ratio",
                f"Aspect ratio matches {payload.expected_aspect_ratio}.",
            )

        return self._fail(
            "correct_aspect_ratio",
            f"Expected {payload.expected_aspect_ratio}, got {width}:{height}.",
            -15,
        )

    def _check_minimum_resolution(self, payload: QualityCheckRequest) -> QualityCheckItemRead:
        dimensions = self._dimensions(payload)
        if dimensions is None:
            return self._fail(
                "correct_minimum_resolution",
                "Cannot verify resolution without dimensions.",
                -15,
            )

        width, height = dimensions
        if width >= payload.minimum_width and height >= payload.minimum_height:
            return self._pass(
                "correct_minimum_resolution",
                f"Resolution {width}x{height} meets minimum.",
            )

        return self._fail(
            "correct_minimum_resolution",
            (
                f"Resolution {width}x{height} is below "
                f"{payload.minimum_width}x{payload.minimum_height}."
            ),
            -15,
        )

    @staticmethod
    def _check_caption_not_empty(
        payload: QualityCheckRequest,
    ) -> QualityCheckItemRead:
        if payload.caption.strip():
            return QualityCheckService._pass("no_empty_caption", "Caption is not empty.")

        return QualityCheckService._fail(
            "no_empty_caption",
            "Caption is empty.",
            -15,
        )

    @staticmethod
    def _check_product_url(payload: QualityCheckRequest) -> QualityCheckItemRead:
        if payload.product_url and payload.product_url.startswith(("http://", "https://")):
            return QualityCheckService._pass("product_url_exists", "Product URL exists.")

        return QualityCheckService._fail(
            "product_url_exists",
            "Product URL is missing or invalid.",
            -10,
        )

    @staticmethod
    def _check_duplicate_caption(
        payload: QualityCheckRequest,
    ) -> QualityCheckItemRead:
        caption = QualityCheckService._normalize_caption(payload.caption)
        cutoff = payload.check_date - timedelta(days=7)

        for recent_caption in payload.recent_captions:
            if recent_caption.posted_date < cutoff:
                continue
            if QualityCheckService._normalize_caption(recent_caption.caption) == caption:
                return QualityCheckService._fail(
                    "no_duplicate_caption_last_7_days",
                    "Caption duplicates a post from the last 7 days.",
                    -15,
                )

        return QualityCheckService._pass(
            "no_duplicate_caption_last_7_days",
            "Caption is not duplicated in the last 7 days.",
        )

    @staticmethod
    def _check_discount_claim(payload: QualityCheckRequest) -> QualityCheckItemRead:
        has_discount_claim = bool(DISCOUNT_PATTERN.search(payload.caption))
        if has_discount_claim and not payload.discount_active:
            return QualityCheckService._fail(
                "no_fake_discount_unless_active",
                "Caption includes a discount or offer, but no active discount is set.",
                -25,
            )

        return QualityCheckService._pass(
            "no_fake_discount_unless_active",
            "No unsupported discount claim found.",
        )

    def _dimensions(self, payload: QualityCheckRequest) -> tuple[int, int] | None:
        if payload.width and payload.height:
            return payload.width, payload.height

        if not payload.asset_file_path or payload.asset_type != "image":
            return None

        path = Path(payload.asset_file_path)
        if not path.is_file():
            return None

        try:
            with Image.open(path) as image:
                return image.size
        except (OSError, UnidentifiedImageError):
            return None

    @staticmethod
    def _parse_aspect_ratio(value: str) -> tuple[int, int]:
        parts = value.split(":", maxsplit=1)
        if len(parts) != 2:
            raise ValueError("Aspect ratio must be formatted like '9:16'.")

        width, height = int(parts[0]), int(parts[1])
        if width <= 0 or height <= 0:
            raise ValueError("Aspect ratio values must be positive.")

        return width, height

    @staticmethod
    def _normalize_caption(value: str) -> str:
        return " ".join(value.lower().split())

    @staticmethod
    def _status(score: int) -> QualityStatus:
        if score < 60:
            return "rejected"
        if score < 80:
            return "needs_review"
        return "approved_candidate"

    @staticmethod
    def _pass(name: str, message: str) -> QualityCheckItemRead:
        return QualityCheckItemRead(
            name=name,
            status="pass",
            message=message,
            score_delta=0,
        )

    @staticmethod
    def _warning(name: str, message: str, score_delta: int) -> QualityCheckItemRead:
        return QualityCheckItemRead(
            name=name,
            status="warning",
            message=message,
            score_delta=score_delta,
        )

    @staticmethod
    def _fail(name: str, message: str, score_delta: int) -> QualityCheckItemRead:
        return QualityCheckItemRead(
            name=name,
            status="fail",
            message=message,
            score_delta=score_delta,
        )
