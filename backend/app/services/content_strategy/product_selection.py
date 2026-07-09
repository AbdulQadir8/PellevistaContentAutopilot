from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Product, ProductImage
from app.schemas import ContentIdeaRead, ProductRead
from app.services.fake_catalog import fake_catalog_store


@dataclass(frozen=True, slots=True)
class SelectionCandidate:
    product_title: str
    tags: list[str]
    inventory_quantity: int
    has_usable_image: bool
    available_for_sale: bool
    last_posted_date: date | None
    score: int = 0


class ProductSelectionService:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def select_for_daily_content(
        self,
        plan_date: date,
        number_of_ideas: int,
    ) -> list[ContentIdeaRead]:
        candidates = await self._load_candidates()
        scored_candidates = [
            self._score_candidate(candidate, plan_date)
            for candidate in candidates
        ]
        selected = sorted(
            scored_candidates,
            key=lambda candidate: (-candidate.score, candidate.product_title),
        )[:number_of_ideas]

        return [
            ContentIdeaRead(
                product_title=candidate.product_title,
                pillar=self._pillar(candidate),
                angle=self._angle(candidate),
            )
            for candidate in selected
        ]

    async def _load_candidates(self) -> list[SelectionCandidate]:
        if self.session is not None:
            try:
                db_candidates = await self._load_db_candidates()
            except Exception:
                db_candidates = []

            if db_candidates:
                return db_candidates

        return [
            self._candidate_from_product_read(product)
            for product in fake_catalog_store.list_products()
        ]

    async def _load_db_candidates(self) -> list[SelectionCandidate]:
        if self.session is None:
            return []

        result = await self.session.exec(select(Product))
        products = result.all()
        candidates: list[SelectionCandidate] = []

        for product in products:
            image_result = await self.session.exec(
                select(ProductImage)
                .where(ProductImage.product_id == product.id)
                .limit(1),
            )
            image = image_result.one_or_none()
            candidates.append(
                SelectionCandidate(
                    product_title=product.title,
                    tags=self._parse_tags(product.tags),
                    inventory_quantity=product.total_inventory or 0,
                    has_usable_image=bool(image and image.url),
                    available_for_sale=product.available_for_sale,
                    last_posted_date=self._date(product.last_posted_at),
                ),
            )

        return candidates

    def _score_candidate(
        self,
        candidate: SelectionCandidate,
        plan_date: date,
    ) -> SelectionCandidate:
        score = 0
        tag_text = " ".join(candidate.tags).lower().replace("-", " ")

        if "red sole" in tag_text:
            score += 30

        if candidate.inventory_quantity > 5:
            score += 20

        if candidate.has_usable_image:
            score += 10

        if self._was_posted_in_last_7_days(candidate.last_posted_date, plan_date):
            score -= 40

        if not candidate.available_for_sale or candidate.inventory_quantity <= 0:
            score -= 100

        return SelectionCandidate(
            product_title=candidate.product_title,
            tags=candidate.tags,
            inventory_quantity=candidate.inventory_quantity,
            has_usable_image=candidate.has_usable_image,
            available_for_sale=candidate.available_for_sale,
            last_posted_date=candidate.last_posted_date,
            score=score,
        )

    @staticmethod
    def _candidate_from_product_read(product: ProductRead) -> SelectionCandidate:
        return SelectionCandidate(
            product_title=product.title,
            tags=product.tags,
            inventory_quantity=product.total_inventory or 0,
            has_usable_image=bool(product.image_url),
            available_for_sale=product.available_for_sale,
            last_posted_date=ProductSelectionService._parse_date(
                product.last_posted_date,
            ),
        )

    @staticmethod
    def _parse_tags(tags: str | None) -> list[str]:
        if not tags:
            return []

        return [tag.strip() for tag in tags.split(",") if tag.strip()]

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if value is None:
            return None

        return date.fromisoformat(value)

    @staticmethod
    def _date(value: datetime | None) -> date | None:
        if value is None:
            return None

        return value.date()

    @staticmethod
    def _was_posted_in_last_7_days(
        last_posted_date: date | None,
        plan_date: date,
    ) -> bool:
        if last_posted_date is None:
            return False

        return plan_date - timedelta(days=7) <= last_posted_date <= plan_date

    @staticmethod
    def _pillar(candidate: SelectionCandidate) -> str:
        tag_text = " ".join(candidate.tags).lower().replace("-", " ")
        if "red sole" in tag_text:
            return "Pain-point hook"

        if candidate.inventory_quantity > 5:
            return "Style education"

        return "Product beauty"

    @staticmethod
    def _angle(candidate: SelectionCandidate) -> str:
        tag_text = " ".join(candidate.tags).lower().replace("-", " ")
        if "red sole" in tag_text:
            return (
                "Most men spend hundreds on a suit, then ruin the look with cheap "
                "shoes."
            )

        if "monk" in tag_text:
            return "The dress shoe that makes smart outfits feel less predictable."

        if "oxford" in tag_text:
            return "One clean Oxford can make a basic outfit look intentionally styled."

        return "Turn this product into the easiest upgrade in the customer wardrobe."
