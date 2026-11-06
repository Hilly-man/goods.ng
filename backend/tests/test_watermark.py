"""Uploaded product photos carry the seller + Goods.ng watermark on the full image and thumbnail."""

from io import BytesIO

from PIL import Image

from app.core.config import settings


def test_product_images_are_watermarked(make_seller, make_product, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "local_media_dir", str(tmp_path))
    seller = make_seller(store="Ada Gadgets")
    product = make_product(seller)

    buf = BytesIO()
    Image.new("RGB", (800, 600), (0, 0, 0)).save(buf, "PNG")
    r = seller.post(f"/seller/products/{product['id']}/images",
                    files=[("files", ("a.png", buf.getvalue(), "image/png"))])
    assert r.status_code == 200, r.text
    image = r.json()["images"][0]

    for url in (image["url"], image["thumb_url"]):
        relative = url.removeprefix(settings.media_base_url).lstrip("/")
        stored = Image.open(tmp_path / relative).convert("L")
        # The source is solid black; only the semi-transparent watermark can produce bright pixels.
        assert sum(1 for px in stored.tobytes() if px > 40) > 100
