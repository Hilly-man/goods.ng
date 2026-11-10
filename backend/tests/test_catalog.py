from tests.conftest import png_bytes


def test_category_tree(client):
    tree = client.get("/api/v1/categories").json()
    names = [c["name"] for c in tree]
    assert "Phones & Tablets" in names and "Agriculture" in names and len(tree) == 17
    phones = next(c for c in tree if c["slug"] == "phones-tablets")
    assert any(ch["slug"] == "mobile-phones" for ch in phones["children"])


def test_buyer_cannot_create_listing_without_seller_profile(make_user, leaf_category):
    u = make_user()
    r = u.post("/seller/products", {"title": "x" * 10})
    assert r.status_code in (403, 422)
    assert u.get("/seller/products").json()["error"]["code"] == "seller_profile_required"


def test_create_update_and_ownership(make_seller, make_product):
    s1, s2 = make_seller(), make_seller()
    p = make_product(s1)
    assert p["category"]["slug"] == "phones-tablets" and p["subcategory"]["slug"] == "mobile-phones"
    assert p["price"] == "1500000.00" and p["status"] == "active"
    r = s1.patch(f"/seller/products/{p['id']}", {"price": "1450000.00"})
    assert r.json()["price"] == "1450000.00"
    # another seller cannot touch it
    assert s2.patch(f"/seller/products/{p['id']}", {"price": "1.00"}).status_code == 403
    assert s2.delete(f"/seller/products/{p['id']}").status_code == 403


def test_html_is_stripped_from_listing(make_seller, make_product):
    s = make_seller()
    p = make_product(s, title="<script>alert(1)</script>Nice phone deal", description="<b>Bold</b> description that is long enough")
    assert "<script>" not in p["title"] and "<b>" not in p["description"]


def test_validation_rejects_bad_price_and_state(make_seller, make_product, leaf_category):
    s = make_seller()
    base = {"title": "Valid title here", "description": "A sufficiently long description text.",
            "category_id": leaf_category, "condition": "brand_new", "state": "Lagos", "city": "Ikeja"}
    assert s.post("/seller/products", {**base, "price": "-5"}).status_code == 422
    assert s.post("/seller/products", {**base, "price": "100", "state": "Atlantis"}).status_code == 422
    assert s.post("/seller/products", {**base, "price": "100.999"}).status_code == 422


def test_search_filters_and_sorting(client, make_seller, make_product):
    s = make_seller()
    make_product(s, title="Samsung Galaxy S24 Ultra", brand="Samsung", price="1200000", condition="brand_new")
    make_product(s, title="Tecno Spark 20 Pro", brand="Tecno", price="180000", condition="foreign_used", state="Abuja", city="Wuse 2")
    make_product(s, title="Apple iPhone 12 Mini", brand="Apple", price="350000", condition="nigerian_used")

    def q(**params):
        r = client.get("/api/v1/products", params=params)
        assert r.status_code == 200, r.text
        return [i["title"] for i in r.json()["items"]]

    assert q(q="galaxy") == ["Samsung Galaxy S24 Ultra"]
    assert q(q="iph") == ["Apple iPhone 12 Mini"]  # prefix search
    assert q(state="Abuja") == ["Tecno Spark 20 Pro"]
    assert set(q(condition=["foreign_used", "nigerian_used"])) == {"Tecno Spark 20 Pro", "Apple iPhone 12 Mini"}
    assert q(min_price="300000", max_price="400000") == ["Apple iPhone 12 Mini"]
    assert q(sort="price_asc")[0] == "Tecno Spark 20 Pro"
    assert q(sort="price_desc")[0] == "Samsung Galaxy S24 Ultra"
    assert q(category="phones-tablets", brand="samsung") == ["Samsung Galaxy S24 Ultra"]
    assert client.get("/api/v1/products", params={"min_price": 10, "max_price": 1}).status_code == 400
    # SQL-ish input is handled safely
    assert client.get("/api/v1/products", params={"q": "'; DROP TABLE products; --"}).status_code == 200


def test_inactive_listing_hidden(client, make_seller, make_product):
    s = make_seller()
    p = make_product(s)
    s.post(f"/seller/products/{p['id']}/status", {"status": "inactive"})
    assert client.get(f"/api/v1/products/{p['slug']}").status_code == 404
    assert client.get("/api/v1/products").json()["total"] == 0


def test_view_count_deduplicated(client, make_seller, make_product):
    s = make_seller()
    p = make_product(s)
    for _ in range(3):
        assert client.post(f"/api/v1/products/{p['slug']}/view").status_code == 204
    assert s.get(f"/seller/products/{p['id']}").json()["views_count"] == 1


def test_image_upload_validation(make_seller, make_product):
    s = make_seller()
    p = make_product(s)
    r = s.post(f"/seller/products/{p['id']}/images", files=[("files", ("a.png", png_bytes(), "image/png"))])
    assert r.status_code == 200, r.text
    img = r.json()["images"][0]
    assert img["url"].endswith(".webp") and img["thumb_url"].endswith("_t.webp")
    bad = s.post(f"/seller/products/{p['id']}/images",
                 files=[("files", ("evil.png", b"<?php system($_GET['x']); ?>", "image/png"))])
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_image"


def test_listing_photo_cap_free_vs_premium(db, make_seller, make_product):
    from tests.test_ads import _premium

    def files(n):
        return [("files", (f"{i}.png", png_bytes(), "image/png")) for i in range(n)]

    free = make_seller()
    p = make_product(free)
    over = free.post(f"/seller/products/{p['id']}/images", files=files(6))
    assert over.status_code == 400 and over.json()["error"]["code"] == "too_many_images"
    assert free.post(f"/seller/products/{p['id']}/images", files=files(5)).status_code == 200

    premium = _premium(make_seller(), db)
    p2 = make_product(premium)
    assert premium.post(f"/seller/products/{p2['id']}/images", files=files(10)).status_code == 200
    extra = premium.post(f"/seller/products/{p2['id']}/images", files=files(1))
    assert extra.status_code == 400 and extra.json()["error"]["code"] == "too_many_images"


def test_seller_photo_quota(make_seller, make_product, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_images_per_seller", 2)
    s = make_seller()
    p = make_product(s)
    two = [("files", ("a.png", png_bytes(), "image/png")), ("files", ("b.png", png_bytes(), "image/png"))]
    assert s.post(f"/seller/products/{p['id']}/images", files=two).status_code == 200
    assert s.get("/sellers/me/dashboard").json()["images_used"] == 2
    assert s.get("/sellers/me/dashboard").json()["images_limit"] == 2

    over = s.post(f"/seller/products/{p['id']}/images", files=[("files", ("c.png", png_bytes(), "image/png"))])
    assert over.status_code == 400 and over.json()["error"]["code"] == "seller_image_limit"

    img_id = s.get(f"/seller/products/{p['id']}").json()["images"][0]["id"]
    s.delete(f"/seller/products/{p['id']}/images/{img_id}")
    again = s.post(f"/seller/products/{p['id']}/images", files=[("files", ("d.png", png_bytes(), "image/png"))])
    assert again.status_code == 200


def test_favourites(make_user, make_seller, make_product):
    s, u = make_seller(), make_user()
    p = make_product(s)
    assert u.post(f"/products/{p['id']}/favourite").json()["favourite"] is True
    u.post(f"/products/{p['id']}/favourite")  # idempotent
    favs = u.get("/users/me/favourites").json()
    assert favs["total"] == 1 and favs["items"][0]["is_favourite"] is True
    u.delete(f"/products/{p['id']}/favourite")
    assert u.get("/users/me/favourites").json()["total"] == 0


def test_admin_category_management_requires_permission(make_user, make_admin):
    u = make_user()
    assert u.post("/categories/admin", {"name": "Drones"}).status_code == 403
    admin_wrong = make_admin(["users.manage"])
    assert admin_wrong.post("/categories/admin", {"name": "Drones"}).status_code == 403
    admin = make_admin(["categories.manage"])
    r = admin.post("/categories/admin", {"name": "Drones"})
    assert r.status_code == 201
    assert any(c["slug"] == "drones" for c in admin.get("/categories").json())


def test_category_counts_include_subcategories(client, make_seller, make_product):
    s = make_seller()
    make_product(s)
    make_product(s, title="Another phone listing")
    tree = client.get("/api/v1/categories").json()
    phones = next(c for c in tree if c["slug"] == "phones-tablets")
    mobile = next(c for c in phones["children"] if c["slug"] == "mobile-phones")
    assert mobile["listing_count"] == 2
    assert phones["listing_count"] == 2


def test_locations_and_city_validation(client, make_seller, make_product, leaf_category):
    loc = client.get("/api/v1/locations").json()
    assert len(loc["states"]) == 37 and "Ikeja" in loc["cities"]["Lagos"]
    assert "Wuse 2" in client.get("/api/v1/locations/Abuja/cities").json()
    s = make_seller()
    # city must belong to the chosen state; matching is case-insensitive and canonicalised
    r = s.post("/seller/products", {"title": "Nice phone for sale", "description": "A sufficiently long description.",
                                    "category_id": leaf_category, "condition": "brand_new", "price": "1000",
                                    "state": "Lagos", "city": "Kubwa"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "city"
    p = make_product(s, city="ikeja")
    assert p["city"] == "Ikeja"
    assert s.patch(f"/seller/products/{p['id']}", {"state": "Kano"}).status_code == 422  # Ikeja isn't in Kano


def test_subcategory_required_when_category_has_children(db, make_seller):
    from app.models import Category

    s = make_seller()
    root = db.query(Category).filter(Category.slug == "phones-tablets").one()
    r = s.post("/seller/products", {"title": "Nice phone for sale", "description": "A sufficiently long description.",
                                    "category_id": str(root.id), "condition": "brand_new", "price": "1000",
                                    "state": "Lagos", "city": "Ikeja"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "subcategory"


def test_new_filters_and_facets(client, db, make_seller, make_product):
    from datetime import timedelta

    from app.core.time import utcnow
    from app.models import Product

    s = make_seller()
    a = make_product(s, title="Samsung Galaxy A15 phone", brand="Samsung", price="150000", condition="brand_new", bnpl_enabled=True)
    make_product(s, title="Samsung Galaxy S21 used", brand="Samsung", price="320000", condition="foreign_used", bnpl_enabled=False)
    make_product(s, title="Tecno Camon 20 phone", brand="Tecno", price="210000", condition="foreign_used",
                 bnpl_enabled=False, protected_checkout_enabled=False)
    # make one listing old
    db.query(Product).filter(Product.title.like("Tecno%")).update({"created_at": utcnow() - timedelta(days=40)})
    db.commit()

    def titles(**params):
        return {i["title"] for i in client.get("/api/v1/products", params=params).json()["items"]}

    assert titles(bnpl="true") == {"Samsung Galaxy A15 phone"}
    assert titles(protected="true") == {"Samsung Galaxy A15 phone", "Samsung Galaxy S21 used"}
    assert titles(posted_within=30) == {"Samsung Galaxy A15 phone", "Samsung Galaxy S21 used"}
    assert titles(with_photos="true") == set()

    f = client.get("/api/v1/products/facets", params={"category": "mobile-phones"}).json()
    assert f["total"] == 3
    assert f["conditions"] == {"brand_new": 1, "foreign_used": 2}
    assert {b["name"]: b["count"] for b in f["brands"]} == {"Samsung": 2, "Tecno": 1}
    assert f["flags"]["bnpl"] == 1 and f["flags"]["protected"] == 2 and f["flags"]["with_photos"] == 0
    assert f["categories"]["parent"]["slug"] == "phones-tablets" and f["categories"]["current"] == "mobile-phones"
    assert next(c for c in f["categories"]["items"] if c["slug"] == "mobile-phones")["count"] == 3
    assert sum(r["count"] for r in f["price_ranges"]) == 3

    # Disjunctive: selecting a brand doesn't zero the other brands' counts, but narrows conditions.
    f2 = client.get("/api/v1/products/facets", params={"category": "mobile-phones", "brand": "Tecno"}).json()
    assert {b["name"]: b["count"] for b in f2["brands"]} == {"Samsung": 2, "Tecno": 1}
    assert f2["conditions"] == {"foreign_used": 1} and f2["total"] == 1
    _ = a


def test_public_stats_reflect_new_listings(client, make_seller, make_product):
    from app.core.cache import cache
    from app.modules.stats.router import CACHE_KEY

    cache.invalidate(CACHE_KEY)
    before = client.get("/api/v1/stats/public").json()
    assert {"live_ads", "new_ads_24h", "sellers", "verified_sellers", "completed_orders", "categories",
            "states_with_ads", "cities_with_ads", "updated_at"} <= before.keys()
    make_product(make_seller())
    cache.invalidate(CACHE_KEY)
    after = client.get("/api/v1/stats/public").json()
    assert after["live_ads"] == before["live_ads"] + 1
    assert after["new_ads_24h"] == before["new_ads_24h"] + 1
    assert after["sellers"] == before["sellers"] + 1
    assert after["categories"] == 17
