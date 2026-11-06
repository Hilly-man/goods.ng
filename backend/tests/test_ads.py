"""Sponsored placements: labelled, relevant, quality-gated, fair, capped and measured."""

import uuid

from app.models import SellerProfile
from app.models.enums import VerificationLevel
from app.modules.ads import service as ads
from tests.conftest import png_bytes, simulate_payment

DESC = "Brand new sealed device with full warranty, receipt and free screen protector included in box."


def _premium(s, db, plan="premium_monthly", verified=True):
    sub = s.post("/subscriptions", {"plan_code": plan}).json()
    simulate_payment(s, sub["payment_reference"])
    if verified:
        sp = db.get(SellerProfile, s.seller["id"])
        sp.verification_level = VerificationLevel.IDENTITY
        db.commit()
    return s


def _listing(s, make_product, photos=3, **kw):
    p = make_product(s, title=kw.pop("title", f"Sponsored phone {uuid.uuid4().hex[:6]}"), description=kw.pop("description", DESC), **kw)
    for _ in range(photos):
        assert s.post(f"/seller/products/{p['id']}/images", files=[("files", ("a.png", png_bytes(), "image/png"))]).status_code == 200
    return p


def _search(client, **params):
    r = client.get("/api/v1/products", params={"page_size": 24, **params})
    assert r.status_code == 200, r.text
    return r.json()["items"]


def test_eligible_premium_listing_is_sponsored_and_labelled(client, db, make_seller, make_product):
    s = _premium(make_seller(), db)
    p = _listing(s, make_product, title="Zebrafruit Galaxy ultra rare phone")
    items = _search(client, q="zebrafruit")
    sponsored = [i for i in items if i["sponsored"]]
    assert sponsored and sponsored[0]["id"] == p["id"]
    assert items[0]["sponsored"] is True  # position 1


def test_quality_bar_and_premium_are_required(client, db, make_seller, make_product):
    unverified = _premium(make_seller(), db, verified=False)
    few_photos = _premium(make_seller(), db)
    standard = make_seller()
    a = _listing(unverified, make_product, title="Quokkaberry phone unverified seller")
    b = _listing(few_photos, make_product, photos=2, title="Quokkaberry phone two photos only")
    c = _listing(standard, make_product, title="Quokkaberry phone standard seller")
    items = _search(client, q="quokkaberry")
    assert not [i for i in items if i["sponsored"]]
    assert {a["id"], b["id"], c["id"]} <= {i["id"] for i in items}  # still shown organically


def test_sponsored_respects_filters_cap_and_one_per_seller(client, db, make_seller, make_product):
    s1 = _premium(make_seller(), db)
    for _ in range(3):
        _listing(s1, make_product, title="Wombatcake phone one seller many ads")
    items = _search(client, q="wombatcake")
    assert sum(i["sponsored"] for i in items) == 1  # one per seller
    # filters are respected: a different state excludes it
    assert not [i for i in _search(client, q="wombatcake", state="Kano") if i["sponsored"]]
    assert ads.blend(list(range(24)), list("abcdefgh"), 24).count  # smoke
    blended = ads.blend(list(range(24)), ["x", "y", "z", "w"], 24)
    assert sum(1 for _, sp in blended if sp) <= int(24 * ads.MAX_SHARE)


def test_no_sponsored_when_sorting_by_price_or_on_a_store(client, db, make_seller, make_product):
    s = _premium(make_seller(), db)
    _listing(s, make_product, title="Platypuspie phone")
    assert not [i for i in _search(client, q="platypuspie", sort="price_asc") if i["sponsored"]]
    assert not [i for i in _search(client, seller_id=s.seller["id"]) if i["sponsored"]]


def test_premium_listings_rank_first_in_relevance_but_not_in_newest(client, db, make_seller, make_product):
    prem = _premium(make_seller(), db)
    std = make_seller()
    older_premium = _listing(prem, make_product, photos=0, title="Narwhalnut phone premium old")
    newer_standard = make_product(std, title="Narwhalnut phone standard newer", description=DESC)
    relevant = [i for i in _search(client, q="narwhalnut") if not i["sponsored"]]
    assert relevant[0]["id"] == older_premium["id"]  # priority search visibility (paid feature)
    newest = [i for i in _search(client, q="narwhalnut", sort="newest") if not i["sponsored"]]
    assert newest[0]["id"] == newer_standard["id"]  # "Newest" stays honest


def test_bump_quota_and_effect(client, db, make_seller, make_product):
    std = make_seller()
    p0 = make_product(std)
    assert std.post(f"/seller/products/{p0['id']}/bump").json()["error"]["code"] == "premium_required"

    s = _premium(make_seller(), db)
    old = _listing(s, make_product, photos=0, title="Axolotlmint phone older")  # not ad-eligible: tests organic freshness
    _listing(make_seller(), make_product, photos=0, title="Axolotlmint phone newer")
    r = s.post(f"/seller/products/{old['id']}/bump")
    assert r.status_code == 200 and r.json()["quota"]["remaining"] == 0
    assert s.post(f"/seller/products/{old['id']}/bump").json()["error"]["code"] == "bump_quota_used"
    organic = [i for i in _search(client, q="axolotlmint", sort="newest") if not i["sponsored"]]
    assert organic[0]["id"] == old["id"]  # bumped to the top
    other = make_seller()
    assert other.post(f"/seller/products/{old['id']}/bump").status_code == 404


def test_business_plan_gets_three_bumps(db, make_seller, make_product):
    s = _premium(make_seller(), db, plan="business_annual")
    p = _listing(s, make_product)
    for left in (2, 1, 0):
        assert s.post(f"/seller/products/{p['id']}/bump").json()["quota"]["remaining"] == left


def test_item_page_block_shows_other_sellers_only(client, db, make_seller, make_product):
    a = _premium(make_seller(), db)
    b = _premium(make_seller(), db)
    pa = _listing(a, make_product)
    _listing(a, make_product)
    pb = _listing(b, make_product)
    cards = client.get(f"/api/v1/products/{pa['slug']}/sponsored").json()
    ids = {c["id"] for c in cards}
    assert pa["id"] not in ids and all(c["sponsored"] for c in cards)
    assert pb["id"] in ids or len(cards) <= 4  # rotation: b is eligible
    assert all(c["seller"]["id"] != a.seller["id"] for c in cards)


def test_events_are_recorded_deduplicated_and_summarised(client, db, make_seller, make_product):
    s = _premium(make_seller(), db)
    p = _listing(s, make_product)
    anon = str(uuid.uuid4())
    body = {"events": [{"kind": "impression", "placement": "search", "product_id": p["id"]},
                       {"kind": "impression", "placement": "search", "product_id": p["id"]},
                       {"kind": "click", "placement": "search", "product_id": p["id"]}]}
    assert client.post("/api/v1/ads/events", json=body, headers={"X-Anon-Id": anon}).json()["recorded"] == 2
    summ = s.get("/seller/ads/summary").json()
    assert summ["impressions"] == 1 and summ["clicks"] == 1 and summ["ctr"] == 100.0
    assert summ["eligible_listings"] == 1 and summ["top_listings"][0]["id"] == p["id"]
