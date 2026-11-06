import uuid

from app.core.cache import cache


def _h(anon):
    return {"X-Anon-Id": anon, "X-Requested-With": "goodsng"}


def test_anonymous_recommendations_follow_search_and_external_landing(client, make_seller, make_product):
    cache.invalidate("feed:")
    s = make_seller()
    phone = make_product(s, title="Apple iPhone 13 Pro Max 256GB")
    other = make_product(s, title="Wooden dining table set for six")
    anon = str(uuid.uuid4())

    cold = client.get("/api/v1/recommendations/for-you", headers=_h(anon)).json()
    assert cold["personalised"] is False

    r = client.post("/api/v1/recommendations/signals", headers=_h(anon),
                    json={"kind": "landing", "source": "google", "query": "iPhone 13"})
    assert r.json() == {"recorded": True}
    # duplicate within 10 minutes is collapsed
    assert client.post("/api/v1/recommendations/signals", headers=_h(anon),
                       json={"kind": "landing", "source": "google", "query": "iphone 13"}).json() == {"recorded": False}

    rec = client.get("/api/v1/recommendations/for-you", headers=_h(anon)).json()
    assert rec["personalised"] is True
    ids = [i["id"] for i in rec["items"]]
    assert ids[0] == phone["id"]
    assert other["id"] not in ids[:1]
    assert rec["reasons"][0]["text"] == "Your Google search “iphone 13”"

    # a viewed listing is not recommended back
    client.post("/api/v1/recommendations/signals", headers=_h(anon), json={"kind": "view", "product_slug": phone["slug"]})
    rec = client.get("/api/v1/recommendations/for-you", headers=_h(anon)).json()
    assert phone["id"] not in [i["id"] for i in rec["items"]]

    assert client.delete("/api/v1/recommendations/history", headers=_h(anon)).json()["cleared"] == 2
    assert client.get("/api/v1/recommendations/for-you", headers=_h(anon)).json()["personalised"] is False


def test_signals_need_an_identity_and_valid_anon_id(client):
    r = client.post("/api/v1/recommendations/signals", json={"kind": "search", "query": "laptop"},
                    headers={"X-Anon-Id": "not-a-uuid", "X-Requested-With": "goodsng"})
    assert r.json() == {"recorded": False}


def test_anonymous_history_merges_into_account_on_sign_in(client, make_user):
    anon = str(uuid.uuid4())
    client.post("/api/v1/recommendations/signals", headers=_h(anon), json={"kind": "search", "query": "generator"})
    u = make_user()
    rec = u.get("/recommendations/for-you", headers={"X-Anon-Id": anon})
    body = rec.json()
    assert body["personalised"] is True
    assert body["reasons"][0]["text"] == "You searched “generator”"
