from app.schemas import CaptionGeneratorInput, CaptionGeneratorOutput, CaptionPlatform

BRAND_NAME = "PelleVista"
BRAND_DESCRIPTOR = "handcrafted leather shoes"
DEFAULT_HASHTAGS = ["#MensStyle", "#LeatherShoes", "#DressShoes"]

PAIN_POINT_HOOKS = [
    "Most men spend hundreds on a suit, then ruin the look with cheap shoes.",
    "A formal outfit is not complete until the shoes look intentional.",
    "Cheap shoes make expensive clothes look average.",
]

STRICT_BRAND_RULES = [
    "Never invent discounts, sale claims, or scarcity.",
    "Never claim medical, comfort, or performance benefits that are not provided.",
    "Keep the product category as men's handcrafted leather dress shoes.",
    "Use PelleVista spelling exactly.",
]


class CaptionGeneratorService:
    def generate(self, payload: CaptionGeneratorInput) -> CaptionGeneratorOutput:
        if payload.platform == "x":
            return self._x_caption(payload)
        if payload.platform == "facebook":
            return self._facebook_caption(payload)
        if payload.platform == "instagram":
            return self._instagram_caption(payload)
        if payload.platform == "pinterest":
            return self._pinterest_caption(payload)

        raise ValueError(f"Unsupported platform: {payload.platform}")

    def generate_for_platform(
        self,
        product_title: str,
        pillar: str,
        angle: str,
        platform: CaptionPlatform,
        product_type: str | None = None,
        tags: list[str] | None = None,
    ) -> CaptionGeneratorOutput:
        return self.generate(
            CaptionGeneratorInput(
                product_title=product_title,
                product_type=product_type,
                tags=tags or [],
                pillar=pillar,
                angle=angle,
                platform=platform,
            ),
        )

    def _x_caption(self, payload: CaptionGeneratorInput) -> CaptionGeneratorOutput:
        hook = self._hook(payload)
        caption = (
            f"{hook}\n\n"
            f"{BRAND_NAME} {BRAND_DESCRIPTOR} are made to finish the outfit properly."
        )
        return CaptionGeneratorOutput(platform="x", caption=self._clean(caption))

    def _facebook_caption(
        self,
        payload: CaptionGeneratorInput,
    ) -> CaptionGeneratorOutput:
        caption = (
            f"{self._hook(payload)}\n\n"
            f"{payload.product_title} is built to bring polish, structure, and presence to "
            "formal outfits without changing the man wearing them.\n\n"
            f"Explore {BRAND_NAME} handcrafted leather shoes."
        )
        return CaptionGeneratorOutput(platform="facebook", caption=self._clean(caption))

    def _instagram_caption(
        self,
        payload: CaptionGeneratorInput,
    ) -> CaptionGeneratorOutput:
        hashtags = self._hashtags(payload)
        caption = (
            "A sharp suit deserves shoes that match the effort.\n\n"
            f"Handcrafted {BRAND_NAME} leather shoes bring polish, structure, and "
            "presence to formal outfits.\n\n"
            f"{' '.join(hashtags)}"
        )
        return CaptionGeneratorOutput(
            platform="instagram",
            caption=self._clean(caption),
            hashtags=hashtags,
        )

    def _pinterest_caption(
        self,
        payload: CaptionGeneratorInput,
    ) -> CaptionGeneratorOutput:
        title = self._pinterest_title(payload)
        description = (
            f"Premium handcrafted men's leather {self._product_keyword(payload)} "
            "shoes for formal outfits, weddings, office wear, and luxury style."
        )
        caption = f"Title: {title}\n\nDescription:\n{description}"
        return CaptionGeneratorOutput(
            platform="pinterest",
            caption=self._clean(caption),
            title=title,
            description=description,
        )

    @staticmethod
    def _hook(payload: CaptionGeneratorInput) -> str:
        if payload.pillar == "Pain-point hook":
            if payload.angle:
                return payload.angle
            return PAIN_POINT_HOOKS[0]

        if payload.pillar == "Style education":
            return "A formal outfit is not complete until the shoes look intentional."

        if payload.pillar == "Red-sole positioning":
            return "The red sole is the detail that makes the outfit feel intentional."

        return payload.angle

    def _pinterest_title(self, payload: CaptionGeneratorInput) -> str:
        color = self._first_matching_descriptor(
            payload=payload,
            options=["black", "brown", "oxblood"],
        )
        keyword = self._product_keyword(payload)
        color_part = f" {color.title()}" if color else ""
        return f"Handcrafted Men's{color_part} {keyword.title()} Shoes"

    @staticmethod
    def _product_keyword(payload: CaptionGeneratorInput) -> str:
        tag_text = " ".join(payload.tags).lower().replace("-", " ")
        title = payload.product_title.lower()
        combined = f"{tag_text} {title}"

        if "wholecut" in combined:
            return "wholecut oxford"
        if "oxford" in combined:
            return "oxford"
        if "monk" in combined:
            return "monk strap"
        if "loafer" in combined:
            return "loafer"

        if payload.product_type:
            return payload.product_type.lower()

        return "dress"

    @staticmethod
    def _first_matching_descriptor(
        payload: CaptionGeneratorInput,
        options: list[str],
    ) -> str | None:
        normalized_tags = {tag.lower().replace("-", " ") for tag in payload.tags}
        title = payload.product_title.lower()
        for option in options:
            if option in normalized_tags or option in title:
                return option

        return None

    def _hashtags(self, payload: CaptionGeneratorInput) -> list[str]:
        hashtags = [*DEFAULT_HASHTAGS]
        keyword = self._product_keyword(payload)
        if "oxford" in keyword and "#OxfordShoes" not in hashtags:
            hashtags[-1] = "#OxfordShoes"
        if "loafer" in keyword and "#Loafers" not in hashtags:
            hashtags[-1] = "#Loafers"
        if "monk" in keyword and "#MonkStrapShoes" not in hashtags:
            hashtags[-1] = "#MonkStrapShoes"

        return hashtags

    @staticmethod
    def _clean(value: str) -> str:
        return "\n".join(line.rstrip() for line in value.strip().splitlines())
