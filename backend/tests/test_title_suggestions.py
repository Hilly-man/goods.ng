import uuid


def test_title_suggestions_use_details(make_seller):
    s = make_seller()
    r = s.post("/seller/products/title-suggestions", {
        "brand": "Apple", "model": "iPhone 15 Pro Max", "condition": "foreign_used",
        "description": "Clean iPhone 15 Pro Max 256GB in Natural Titanium with box and charger.",
    })
    assert r.status_code == 200, r.text
    suggestions = r.json()["suggestions"]
    assert 1 <= len(suggestions) <= 3
    assert all(8 <= len(x) <= 140 for x in suggestions)
    joined = " | ".join(suggestions)
    assert "256GB" in joined and "Natural Titanium" in joined and "Foreign Used" in joined
    assert "Apple Apple" not in joined


def test_title_suggestions_include_category(make_seller, leaf_category):
    s = make_seller()
    r = s.post("/seller/products/title-suggestions", {
        "category_id": leaf_category, "brand": "Samsung", "model": "Galaxy S24",
        "condition": "brand_new", "description": "Sealed unit with 512GB storage.",
    })
    assert r.status_code == 200, r.text
    assert any("Mobile Phones" in x for x in r.json()["suggestions"])


def test_title_suggestions_dedupe_brand_in_model(make_seller):
    s = make_seller()
    r = s.post("/seller/products/title-suggestions", {
        "brand": "Apple", "model": "Apple iPhone 15", "condition": "brand_new",
        "description": "Brand new sealed.",
    })
    joined = " | ".join(r.json()["suggestions"])
    assert "Apple Apple" not in joined


def test_title_suggestions_detect_vehicle_year_and_colour(make_seller):
    s = make_seller()
    r = s.post("/seller/products/title-suggestions", {
        "brand": "Toyota", "model": "Camry LE", "condition": "foreign_used",
        "description": "2010 Toyota Camry LE, black, automatic, 98,000 miles, clean title.",
    })
    joined = " | ".join(r.json()["suggestions"])
    assert "2010" in joined and "Black" in joined and "Foreign Used" in joined


def test_title_suggestions_require_seller(client):
    r = client.post("/api/v1/seller/products/title-suggestions", json={"brand": "Apple"})
    assert r.status_code in (401, 403)


def test_title_suggestions_unknown_category(make_seller):
    s = make_seller()
    r = s.post("/seller/products/title-suggestions", {"category_id": str(uuid.uuid4()), "brand": "Apple"})
    assert r.status_code == 404


def test_title_suggestions_return_empty_without_details(make_seller):
    s = make_seller()
    r = s.post("/seller/products/title-suggestions", {})
    assert r.status_code == 200 and r.json()["suggestions"] == []
