"""Generate watermarked demo photos for seeded listings.

    python -m app.seed_images            # fill every seeded listing that has no photos
    python -m app.seed_images --limit 10 # only the first 10

The drawings are intentionally simple product cards (brand, title, category palette), not stock
photos: they exist so the gallery, thumbnails, list cards and watermark can be exercised locally.
Run `python -m app.seed --demo` first.
"""

from __future__ import annotations

import argparse
import io
import re

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.time import utcnow
from app.integrations.storage import delete_stored_image, store_image
from app.models import Product, ProductImage, SellerProfile

PALETTES: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "phones-tablets": ((6, 78, 59), (16, 185, 129)),
    "computers-accessories": ((15, 23, 42), (59, 130, 246)),
    "electronics": ((49, 46, 129), (139, 92, 246)),
    "fashion": ((131, 24, 67), (244, 114, 182)),
    "shoes-bags": ((120, 53, 15), (245, 158, 11)),
    "home-furniture": ((30, 58, 95), (96, 165, 250)),
    "home-appliances": ((19, 78, 74), (45, 212, 191)),
    "vehicles": ((30, 41, 59), (100, 116, 139)),
    "automobile-parts": ((51, 65, 85), (148, 163, 184)),
    "property-real-estate": ((12, 74, 110), (14, 165, 233)),
    "beauty-personal-care": ((88, 28, 135), (232, 121, 249)),
    "sports-fitness": ((20, 83, 45), (132, 204, 22)),
    "baby-kids": ((103, 63, 11), (251, 191, 36)),
    "business-equipment": ((30, 58, 138), (129, 140, 248)),
    "industrial-equipment": ((55, 65, 81), (156, 163, 175)),
    "agriculture": ((22, 78, 43), (34, 197, 94)),
    "general-merchandise": ((67, 56, 202), (165, 180, 252)),
}
DEFAULT_PALETTE = ((6, 78, 59), (16, 185, 129))


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def gradient(w: int, h: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    im = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(h - 1, 1)
        draw.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return im


def wrapped(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=fnt) <= width or not line:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines[:4]


def card(product: Product, seller: SellerProfile, variant: int) -> bytes:
    top, bottom = PALETTES.get(product.subcategory.slug if product.subcategory else "", DEFAULT_PALETTE)
    if variant % 2:
        top, bottom = bottom, top
    im = gradient(1400, 1050, top, bottom)
    d = ImageDraw.Draw(im)

    # Decorative rings
    ring = tuple(min(255, c + 45) for c in top)
    for radius in (420, 560, 700):
        d.ellipse([700 - radius // 2, 525 - radius // 2, 700 + radius // 2, 525 + radius // 2],
                  outline=ring, width=2)

    card_box = (90, 90, 1310, 960)
    d.rounded_rectangle(card_box, radius=48, fill=(255, 255, 255))
    inner_w = card_box[2] - card_box[0] - 140

    brand = (product.brand or seller.store_name).upper()
    d.text((card_box[0] + 70, card_box[1] + 66), brand, font=font(30),
           fill=tuple(int(c * 0.7) for c in bottom))
    title_font = font(64)
    y = card_box[1] + 130
    for line in wrapped(d, product.title, title_font, inner_w):
        d.text((card_box[0] + 70, y), line, font=title_font, fill=(17, 24, 39))
        y += 78

    # Large monogram / product silhouette placeholder
    cx, cy = card_box[0] + 70 + 190, card_box[3] - 230
    d.rounded_rectangle([cx - 150, cy - 150, cx + 150, cy + 150], radius=36, fill=top)
    letter = (product.brand or product.title or "G")[0].upper()
    box = d.textbbox((0, 0), letter, font=font(170))
    d.text((cx - (box[2] - box[0]) / 2, cy - (box[3] - box[1]) / 2 - 10), letter, font=font(170),
           fill=(255, 255, 255))

    label = "NEW ARRIVAL" if variant % 2 == 0 else "PRODUCT DETAIL"
    d.rounded_rectangle([card_box[0] + 70, card_box[3] - 120, card_box[0] + 430, card_box[3] - 60],
                        radius=30, fill=top)
    d.text((card_box[0] + 100, card_box[3] - 108), label, font=font(26), fill=(255, 255, 255))

    meta = f"{product.condition.replace('_', ' ').title()}  ·  {product.city}, {product.state}"
    d.text((card_box[0] + 470, card_box[3] - 108), meta, font=font(26), fill=(75, 85, 99))

    if variant % 2 == 0:
        d.rounded_rectangle([card_box[2] - 250, card_box[1] + 60, card_box[2] - 70, card_box[1] + 120],
                            radius=30, fill=(240, 253, 244))
        d.text((card_box[2] - 220, card_box[1] + 72), "FOR SALE", font=font(24), fill=top)

    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--replace", action="store_true", help="regenerate images that already exist")
    args = parser.parse_args()
    if settings.environment not in ("development", "test"):
        raise SystemExit("Refusing to generate demo images outside development/test")

    with SessionLocal() as db:
        products = db.scalars(select(Product).options(selectinload(Product.images), selectinload(Product.subcategory),
                                                      selectinload(Product.seller)).where(
            Product.deleted_at.is_(None)).order_by(Product.created_at)).all()
        seeded = [p for p in products if re.search(r"-\d{4}$", p.slug)]
        if not args.replace:
            seeded = [p for p in seeded if not p.images]
        if args.limit:
            seeded = seeded[: args.limit]
        made = 0
        for p in seeded:
            if args.replace and p.images:
                for img in list(p.images):
                    delete_stored_image(img.storage_key)
                p.images.clear()
            for variant in range(2):
                stored = store_image(card(p, p.seller, variant), f"products/{p.id}",
                                     watermark=f"“{p.seller.store_name}” Listed on Goods.ng")
                p.images.append(ProductImage(url=stored.url, thumb_url=stored.thumb_url, storage_key=stored.key,
                                             width=stored.width, height=stored.height, position=variant,
                                             created_at=utcnow()))
                made += 1
            db.flush()
        db.commit()
        verb = "Regenerated" if args.replace else "Generated"
        print(f"{verb} {made} photos for {len(seeded)} seeded listings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
