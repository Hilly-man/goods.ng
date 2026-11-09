"""Object storage + secure image processing.

Uploaded images are validated by decoding them with Pillow (not trusting extension/MIME), size- and
pixel-limited, stripped of metadata (EXIF/GPS), re-encoded to WebP, and stored under random keys.
"""

import io
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import AppError

Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


@dataclass
class StoredImage:
    key: str
    url: str
    thumb_url: str
    width: int
    height: int


class LocalStorage:
    def __init__(self, root: str, base_url: str):
        self.root = Path(root)
        self.base_url = base_url.rstrip("/")

    def put(self, key: str, data: bytes, content_type: str) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"{self.base_url}/{key}"

    def put_private(self, key: str, data: bytes, content_type: str) -> str:
        path = self.root.parent / "private" / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def delete(self, key: str) -> None:
        try:
            (self.root / key).unlink()
        except FileNotFoundError:
            pass


class S3Storage:  # pragma: no cover - requires cloud credentials
    def __init__(self):
        import boto3

        self.bucket = settings.s3_bucket
        self.client = boto3.client("s3", endpoint_url=settings.s3_endpoint_url)

    def put(self, key, data, content_type):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type,
                               CacheControl="public, max-age=31536000, immutable")
        return f"{settings.media_base_url.rstrip('/')}/{key}"

    def put_private(self, key, data, content_type):
        self.client.put_object(Bucket=self.bucket, Key=f"private/{key}", Body=data, ContentType=content_type,
                               ServerSideEncryption="AES256")
        return f"private/{key}"

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)


def get_storage():
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage(settings.local_media_dir, settings.media_base_url)


def _load(data: bytes) -> Image.Image:
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(f"Image exceeds {settings.max_upload_mb}MB limit", code="file_too_large")
    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()
        img = Image.open(io.BytesIO(data))
        if img.format not in ALLOWED_FORMATS:
            raise AppError("Only JPEG, PNG and WebP images are allowed", code="invalid_image")
        img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as e:
        raise AppError("File is not a valid image", code="invalid_image") from e
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


_FONT_CANDIDATES = {
    True: ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf"],
    False: ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"],
}


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """DejaVu on the server (installed in the Docker image), Arial on macOS dev, Pillow's font as a last resort."""
    for path in _FONT_CANDIDATES[bold]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


# ---------------- listing-photo watermark (Jiji-style: brand mark centred, white, semi-transparent) ----------------
_SHIELD = [(0.50, 0.00), (0.95, 0.15), (0.95, 0.48), (0.92, 0.62), (0.84, 0.76), (0.70, 0.89), (0.50, 1.00),
           (0.30, 0.89), (0.16, 0.76), (0.08, 0.62), (0.05, 0.48), (0.05, 0.15)]
_TICK = [(0.27, 0.52), (0.44, 0.68), (0.75, 0.35)]
_MARK_OPACITY = 190   # of 255 — clearly visible, never hides the item (Jiji's mark is ~50–60%)
_MARK_WIDTH = 0.42    # share of the photo's width


def _name_lines(name: str, per_line: int = 26, limit: int = 52) -> list[str]:
    """Long business names wrap onto two balanced lines (and are cut with … past `limit`)."""
    name = " ".join(name.split())
    if len(name) > limit:
        name = name[: limit - 1].rstrip() + "…"
    if len(name) <= per_line:
        return [name]
    words, best = name.split(" "), None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        if best is None or max(len(a), len(b)) < max(len(best[0]), len(best[1])):
            best = (a, b)
    return list(best) if best else [name[:per_line], name[per_line:]]


def _mark_layer(business: str | None) -> Image.Image:
    """White mark on transparent background, drawn 4× for smooth edges:
         [shield]  Listed on Goods.ng
                   BUSINESS NAME        <- larger, bold
       Without a business name: [shield] Goods.ng (logo only)."""

    h = 240  # shield height in the oversampled drawing
    gap = int(h * 0.16)
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    if business:
        top, names = "Listed on Goods.ng", _name_lines(business)
        top_font, name_font = _font(int(h * 0.27), bold=False), _font(int(h * 0.42), bold=True)
        tw = max([draw.textlength(top, font=top_font)] + [draw.textlength(n, font=name_font) for n in names])
    else:
        name_font = _font(int(h * 0.62), bold=True)
        tw = draw.textlength("Goods.ng", font=name_font)
    full_w = int(h + gap + tw + h * 0.1)
    mask = Image.new("L", (full_w, h), 0)
    d = ImageDraw.Draw(mask)
    d.polygon([(x * h, y * h) for x, y in _SHIELD], fill=255)
    d.line([(x * h, y * h) for x, y in _TICK], fill=0, width=int(h * 0.11), joint="curve")
    x = h + gap
    if business:
        # "Listed on Goods.ng" then the business name (1–2 lines), vertically centred on the shield.
        t_box = d.textbbox((0, 0), top, font=top_font)
        asc, desc = name_font.getmetrics()
        t_h, line_h, spacing = t_box[3] - t_box[1], int((asc + desc) * 0.95), int(h * 0.08)
        block = t_h + spacing + line_h * len(names)
        if block > h:  # two-line names: grow the canvas, keep the shield centred
            grow = block - h + int(h * 0.1)
            bigger = Image.new("L", (mask.width, h + grow), 0)
            bigger.paste(mask, (0, grow // 2))
            mask, d = bigger, ImageDraw.Draw(bigger)
        y0 = (mask.height - block) // 2
        d.text((x, y0 - t_box[1]), top, font=top_font, fill=225)  # slightly lighter than the name
        for i, n in enumerate(names):
            d.text((x, y0 + t_h + spacing + i * line_h), n, font=name_font, fill=255)
    else:
        box = d.textbbox((0, 0), "Goods.ng", font=name_font)
        d.text((x, (h - (box[3] - box[1])) // 2 - box[1]), "Goods.ng", font=name_font, fill=255)
    return mask


def _watermark(img: Image.Image, business: str | bool = True) -> Image.Image:
    """Centre the white Goods.ng mark (with the seller's business name, if given) on a listing photo."""
    from PIL import ImageFilter

    name = business if isinstance(business, str) else None
    base = img.convert("RGBA")
    w, h = base.size
    mask = _mark_layer(name)
    # Fit: about 55% of the photo's width with a name (42% logo-only), never wider than 86% or taller than 22%.
    target_w = int(w * (0.55 if name else _MARK_WIDTH))
    max_h = h * (0.30 if mask.height > 300 else 0.22)  # a two-line name may stand a little taller
    target_w = min(target_w, int(w * 0.86), int(mask.width * max_h / mask.height))
    target_w = max(120, min(target_w, w))
    target_h = max(1, round(mask.height * target_w / mask.width))
    mask = mask.resize((target_w, target_h), Image.LANCZOS)
    pad = max(4, target_h // 6)
    layer = Image.new("RGBA", (target_w + 2 * pad, target_h + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("L", layer.size, 0)  # soft shadow keeps it readable on white/bright photos
    shadow.paste(mask.point(lambda v: v * 85 // 255), (pad, pad + 1))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(1, target_h // 30)))
    layer.paste((0, 0, 0, 255), (0, 0), shadow)
    layer.paste((255, 255, 255, 255), (pad, pad), mask.point(lambda v: v * _MARK_OPACITY // 255))
    base.alpha_composite(layer, ((w - layer.width) // 2, (h - layer.height) // 2))
    return base.convert("RGB")


def _encode(img: Image.Image, max_side: int, quality: int) -> tuple[bytes, int, int]:
    im = img.copy()
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=quality, method=4)  # re-encode: drops EXIF/GPS and any payload
    return buf.getvalue(), im.width, im.height


def store_image(data: bytes, folder: str, watermark: bool | str = False) -> StoredImage:
    """Listing photos only: `watermark=<business name>` (or True for the logo alone).
    Never used for avatars, logos, evidence or KYC documents."""
    img = _load(data)
    if watermark:
        img = _watermark(img, watermark)
    storage = get_storage()
    key = f"{folder}/{uuid.uuid4().hex}"
    full, w, h = _encode(img, 1280, 80)
    thumb, _, _ = _encode(img, 400, 72)
    url = storage.put(f"{key}.webp", full, "image/webp")
    thumb_url = storage.put(f"{key}_t.webp", thumb, "image/webp")
    return StoredImage(key=key, url=url, thumb_url=thumb_url, width=w, height=h)


def delete_stored_image(storage_key: str) -> None:
    """Remove both the full image and its thumbnail (same key, different suffix)."""
    storage = get_storage()
    storage.delete(f"{storage_key}.webp")
    storage.delete(f"{storage_key}_t.webp")


def store_private_document(data: bytes, folder: str) -> str:
    """KYC documents: images re-encoded; stored in private (non-public) storage."""
    img = _load(data)
    full, _, _ = _encode(img, 2000, 85)
    return get_storage().put_private(f"{folder}/{uuid.uuid4().hex}.webp", full, "image/webp")
