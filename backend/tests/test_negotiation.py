from datetime import timedelta

from app.core.time import utcnow
from app.models import Offer
from tests.conftest import ADDRESS


def _start(buyer, product, amount="1350000.00"):
    return buyer.post("/negotiations", {"product_id": product["id"], "amount": amount})


def test_offer_counter_accept_and_checkout_uses_agreed_price(client, make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller)
    n = _start(buyer, p).json()
    assert n["status"] == "open" and n["your_turn"] is False
    offer_id = n["offers"][-1]["id"]
    # seller counters
    n = seller.post(f"/negotiations/{n['id']}/respond",
                    {"offer_id": offer_id, "action": "counter", "amount": "1450000.00"}).json()
    assert n["offers"][-1]["made_by"] == "seller"
    # buyer counters again
    n = buyer.post(f"/negotiations/{n['id']}/respond",
                   {"offer_id": n["offers"][-1]["id"], "action": "counter", "amount": "1400000.00"}).json()
    # seller accepts
    n = seller.post(f"/negotiations/{n['id']}/respond", {"offer_id": n["offers"][-1]["id"], "action": "accept"}).json()
    assert n["status"] == "accepted" and n["agreed_price"] == "1400000.00"
    # Public price unchanged
    assert client.get(f"/api/v1/products/{p['slug']}").json()["price"] == "1500000.00"
    # Checkout with the negotiation uses agreed price
    q = buyer.post("/checkout/quote", {"product_id": p["id"], "negotiation_id": n["id"]}).json()
    assert q["unit_price"] == "1400000.00" and q["negotiated"] is True
    assert q["protection_fee"] == "5000.00"  # 1.5% capped at 5000
    assert q["total"] == "1405000.00"
    # Negotiation history preserved in the conversation
    conv = buyer.get(f"/conversations/{n['conversation_id']}").json()
    assert sum(1 for m in conv["messages"] if m["kind"] == "offer") == 3


def test_offer_rules(make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller)
    assert _start(buyer, p, "1500000.00").json()["error"]["code"] == "offer_too_high"
    assert _start(buyer, p, "1000.00").json()["error"]["code"] == "offer_too_low"
    assert _start(seller, p).json()["error"]["code"] == "own_listing"
    fixed = make_product(seller, negotiable=False, title="Fixed price phone")
    assert _start(buyer, fixed).json()["error"]["code"] == "not_negotiable"
    assert _start(buyer, p).status_code == 201
    assert _start(buyer, p).json()["error"]["code"] == "negotiation_exists"


def test_turns_and_stale_offers(make_seller, make_user, make_product):
    seller, buyer, stranger = make_seller(), make_user(), make_user()
    p = make_product(seller)
    n = _start(buyer, p).json()
    first = n["offers"][-1]["id"]
    # buyer cannot accept own offer
    assert buyer.post(f"/negotiations/{n['id']}/respond", {"offer_id": first, "action": "accept"}).json()["error"]["code"] == "not_your_turn"
    # outsiders see nothing
    assert stranger.get(f"/negotiations/{n['id']}").status_code == 404
    seller.post(f"/negotiations/{n['id']}/respond", {"offer_id": first, "action": "counter", "amount": "1480000"})
    # accepting the superseded offer id fails (concurrency / stale UI)
    r = seller.post(f"/negotiations/{n['id']}/respond", {"offer_id": first, "action": "accept"})
    assert r.json()["error"]["code"] == "stale_offer"
    # invalid counter direction
    last = seller.get(f"/negotiations/{n['id']}").json()["offers"][-1]["id"]
    r = buyer.post(f"/negotiations/{n['id']}/respond", {"offer_id": last, "action": "counter", "amount": "1490000"})
    assert r.json()["error"]["code"] == "counter_invalid"


def test_offer_expiry(db, make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller)
    n = _start(buyer, p).json()
    db.query(Offer).update({"expires_at": utcnow() - timedelta(minutes=1)})
    db.commit()
    r = seller.post(f"/negotiations/{n['id']}/respond", {"offer_id": n["offers"][-1]["id"], "action": "accept"})
    assert r.json()["error"]["code"] == "offer_expired"
    assert buyer.get(f"/negotiations/{n['id']}").json()["status"] == "expired"
    # buyer can start a fresh negotiation afterwards
    assert _start(buyer, p).status_code == 201


def test_other_buyer_cannot_use_accepted_offer(make_seller, make_user, make_product):
    seller, buyer, other = make_seller(), make_user(), make_user()
    p = make_product(seller)
    n = _start(buyer, p).json()
    seller.post(f"/negotiations/{n['id']}/respond", {"offer_id": n["offers"][-1]["id"], "action": "accept"})
    r = other.post("/checkout", {"product_id": p["id"], "negotiation_id": n["id"], "address": ADDRESS})
    assert r.status_code == 404


def test_messaging_and_read_receipts(make_seller, make_user, make_product):
    seller, buyer = make_seller(), make_user()
    p = make_product(seller)
    r = buyer.post("/conversations", {"product_id": p["id"], "body": "Is this <b>available</b>?"})
    assert r.status_code == 201
    cid = r.json()["conversation_id"]
    assert r.json()["message"]["body"] == "Is this available?"
    assert seller.get("/conversations/unread-count").json()["unread"] == 1
    convs = seller.get("/conversations").json()
    assert convs[0]["unread"] == 1 and convs[0]["role"] == "seller"
    seller.get(f"/conversations/{cid}")  # opening marks read
    assert seller.get("/conversations/unread-count").json()["unread"] == 0
    seller.post(f"/conversations/{cid}/messages", {"body": "Yes it is"})
    msgs = buyer.get(f"/conversations/{cid}").json()["messages"]
    assert msgs[0]["read_at"] is not None and len(msgs) == 2
    assert make_user().get(f"/conversations/{cid}").status_code == 404
