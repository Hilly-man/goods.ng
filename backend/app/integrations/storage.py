"""Object storage + secure image processing.

Uploaded images are validated by decoding them with Pillow (not trusting extension/MIME), size- and
pixel-limited, stripped of metadata (EXIF/GPS), re-encoded to WebP, and stored under random keys.
"""

import io
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

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


def _encode(img: Image.Image, max_side: int, quality: int) -> tuple[bytes, int, int]:
    im = img.copy()
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=quality, method=4)  # re-encode: drops EXIF/GPS and any payload
    return buf.getvalue(), im.width, im.height


def store_image(data: bytes, folder: str) -> StoredImage:
    img = _load(data)
    storage = get_storage()
    key = f"{folder}/{uuid.uuid4().hex}"
    full, w, h = _encode(img, 1280, 80)
    thumb, _, _ = _encode(img, 400, 72)
    url = storage.put(f"{key}.webp", full, "image/webp")
    thumb_url = storage.put(f"{key}_t.webp", thumb, "image/webp")
    return StoredImage(key=key, url=url, thumb_url=thumb_url, width=w, height=h)


def store_private_document(data: bytes, folder: str) -> str:
    """KYC documents: images re-encoded; stored in private (non-public) storage."""
    img = _load(data)
    full, _, _ = _encode(img, 2000, 85)
    return get_storage().put_private(f"{folder}/{uuid.uuid4().hex}.webp", full, "image/webp")
