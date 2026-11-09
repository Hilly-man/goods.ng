"""Uploaded product photos carry the centred Goods.ng mark (Jiji-style) on the full image and thumbnail;
other uploads (avatars, logos, evidence) are never watermarked."""

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


def test_mark_is_centred_and_avatars_are_not_watermarked(make_user, tmp_path, monkeypatch):
    from app.integrations.storage import _watermark

    img = _watermark(Image.new("RGB", (1000, 800), (0, 0, 0))).convert("L")
    w, h = img.size
    centre = img.crop((w // 4, h // 3, 3 * w // 4, 2 * h // 3))
    corner = img.crop((0, 0, w // 5, h // 5))
    assert max(centre.tobytes()) > 120 and max(corner.tobytes()) < 10  # mark in the middle, corners untouched

    monkeypatch.setattr(settings, "local_media_dir", str(tmp_path))
    u = make_user()
    buf = BytesIO()
    Image.new("RGB", (400, 400), (0, 0, 0)).save(buf, "PNG")
    r = u.post("/users/me/avatar", files={"file": ("me.png", buf.getvalue(), "image/png")})
    stored = Image.open(tmp_path / r.json()["avatar_url"].removeprefix(settings.media_base_url).lstrip("/")).convert("L")
    assert max(stored.tobytes()) < 10  # profile photos stay clean


def test_long_business_names_wrap_and_are_capped():
    from app.integrations.storage import _name_lines

    assert _name_lines("Okafor Phones Hub") == ["Okafor Phones Hub"]
    two = _name_lines("HomeEase Appliances & Electronics Mega Store Lagos")
    assert len(two) == 2 and all(len(x) <= 30 for x in two)
    capped = _name_lines("A" * 80)
    assert "".join(capped).endswith("…") and len("".join(capped)) <= 52
