from app.schemas import (
    GenerationSettings,
    PlatformName,
    PromptBuilderInput,
    PromptBuilderOutput,
    PromptProductImageInput,
    PromptProductInput,
)

PLATFORM_FORMATS: dict[PlatformName, dict[str, str]] = {
    "instagram": {"aspect_ratio": "9:16", "asset_type": "video"},
    "pinterest": {"aspect_ratio": "2:3", "asset_type": "image"},
    "facebook": {"aspect_ratio": "4:5", "asset_type": "image"},
    "x": {"aspect_ratio": "16:9", "asset_type": "image"},
}

NEGATIVE_PROMPT = (
    "wrong shoe, different shoe, changed silhouette, changed color, missing red sole, "
    "incorrect sole color, extra logos, fake branding, sneakers, boots, sandals, "
    "distorted leather, warped stitching, deformed toe box, duplicate shoes, extra "
    "laces, missing straps, blurry product, low quality, watermark, text overlay, "
    "cropped product, hands covering shoe, unrelated props"
)


class PromptBuilderService:
    def build(self, payload: PromptBuilderInput) -> PromptBuilderOutput:
        platform_format = PLATFORM_FORMATS[payload.platform]
        aspect_ratio = payload.aspect_ratio or platform_format["aspect_ratio"]
        asset_type = "video" if platform_format["asset_type"] == "video" else "image"

        settings = GenerationSettings(
            platform=payload.platform,
            aspect_ratio=aspect_ratio,
            asset_type=asset_type,
            creative_style=payload.creative_style,
            reference_image_url=payload.product_image.url,
            lighting="premium studio lighting with controlled highlights on leather",
            camera_direction=self._camera_direction(payload.platform),
            duration_seconds=6 if asset_type == "video" else None,
        )

        return PromptBuilderOutput(
            higgsfield_prompt=self._higgsfield_prompt(payload, settings),
            negative_prompt=self._negative_prompt(payload.product),
            generation_settings=settings,
        )

    def build_from_parts(
        self,
        product: PromptProductInput,
        product_image: PromptProductImageInput,
        content_pillar: str,
        angle: str,
        platform: PlatformName,
        aspect_ratio: str | None = None,
        creative_style: str = "premium editorial menswear product advertisement",
    ) -> PromptBuilderOutput:
        return self.build(
            PromptBuilderInput(
                product=product,
                product_image=product_image,
                content_pillar=content_pillar,
                angle=angle,
                platform=platform,
                aspect_ratio=aspect_ratio,
                creative_style=creative_style,
            ),
        )

    def _higgsfield_prompt(
        self,
        payload: PromptBuilderInput,
        settings: GenerationSettings,
    ) -> str:
        product = payload.product
        tag_text = ", ".join(product.tags) if product.tags else "no tags"
        red_sole_instruction = self._red_sole_instruction(product.tags)
        product_type = product.product_type or "men's dress shoe"
        image_note = (
            f"Reference image alt text: {payload.product_image.alt_text}."
            if payload.product_image.alt_text
            else "Reference image is the source of truth."
        )

        return " ".join(
            [
                "Create a Higgsfield-ready product creative using the provided",
                "reference image as the strict source of truth.",
                f"Product: {product.title}.",
                f"Product type: {product_type}.",
                f"Tags: {tag_text}.",
                image_note,
                "Preserve the exact shoe identity: same silhouette, material, toe",
                "shape, lace or strap structure, stitching, color, sole shape, and",
                "visible product proportions.",
                red_sole_instruction,
                "Do not redesign, restyle, recolor, replace, or invent a different",
                "shoe.",
                f"Content pillar: {payload.content_pillar}.",
                f"Creative angle: {payload.angle}",
                f"Platform: {settings.platform}.",
                f"Aspect ratio: {settings.aspect_ratio}.",
                f"Asset type: {settings.asset_type}.",
                f"Creative style: {settings.creative_style}.",
                "Scene should feel premium, controlled, realistic, and suitable for",
                "a PelleVista menswear product campaign.",
            ],
        )

    @staticmethod
    def _negative_prompt(product: PromptProductInput) -> str:
        product_specific_terms = [
            "do not change product title",
            f"not {product.title}" if product.title else "",
        ]
        return ", ".join(
            term for term in [NEGATIVE_PROMPT, *product_specific_terms] if term
        )

    @staticmethod
    def _camera_direction(platform: PlatformName) -> str:
        if platform == "instagram":
            return "vertical hero product framing with gentle motion potential"

        if platform == "pinterest":
            return "vertical catalog-style composition with full shoe visible"

        if platform == "facebook":
            return "balanced feed composition with product centered"

        return "wide social composition with product fully visible"

    @staticmethod
    def _red_sole_instruction(tags: list[str]) -> str:
        tag_text = " ".join(tags).lower().replace("-", " ")
        if "red sole" in tag_text:
            return (
                "The red sole is a key brand detail and must remain visible, accurate, "
                "and attached to the same shoe."
            )

        return "If the sole is visible, keep it faithful to the reference image."
