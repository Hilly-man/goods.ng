"""Soft-deleted listings are purged with their stored image files after the retention window."""

from datetime import timedelta

from app.core.config import settings
from app.core.time import utcnow
from app.models import Product
from app.modules.products.service import purge_deleted_listings
from tests.conftest import png_bytes


def test_purge_deleted_listings_removes_rows_and_files(make_seller, make_product, db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "local_media_dir", str(tmp_path))
    s = make_seller()
    p = make_product(s)
    files = [("files", ("a.png", png_bytes(), "image/png")), ("files", ("b.png", png_bytes(), "image/png"))]
    assert s.post(f"/seller/products/{p['id']}/images", files=files).status_code == 200

    db.expire_all()
    product = db.get(Product, p["id"])
    keys = [i.storage_key for i in product.images]
    assert len(keys) == 2 and all((tmp_path / f"{k}.webp").exists() for k in keys)

    assert s.delete(f"/seller/products/{p['id']}").status_code == 204
    db.expire_all()
    product = db.get(Product, p["id"])
    product.deleted_at = utcnow() - timedelta(days=31)
    db.commit()

    result = purge_deleted_listings(db, retention_days=30)
    assert result == {"products": 1, "images": 2}
    db.expire_all()
    assert db.query(Product).filter_by(id=p["id"]).first() is None
    assert not any((tmp_path / f"{k}.webp").exists() for k in keys)
    assert not any((tmp_path / f"{k}_t.webp").exists() for k in keys)
