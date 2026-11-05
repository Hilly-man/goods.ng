import io
import os
import uuid
from decimal import Decimal

os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://localhost/goodsng_test")
os.environ["LOCAL_MEDIA_DIR"] = "/tmp/goodsng-test-media"
os.environ["RATE_LIMIT_PER_MINUTE"] = "100000"

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.core.cache import cache  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_reference  # noqa: E402

PASSWORD = "Passw0rd!x"


@pytest.fixture(scope="session", autouse=True)
def _schema():
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as c:
        tables = [r[0] for r in c.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'"))]
        c.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    with SessionLocal() as db:
        seed_reference(db)
    cache.reset()
    yield


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture
def client():
    return TestClient(app)


class Api:
    """Small helper around TestClient that tracks a bearer token per actor."""

    def __init__(self, client: TestClient, token: str | None = None, user: dict | None = None):
        self.c, self.token, self.user = client, token, user

    def h(self, extra=None):
        h = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        return {**h, **(extra or {})}

    def get(self, url, **kw):
        return self.c.get(f"/api/v1{url}", headers=self.h(kw.pop("headers", None)), **kw)

    def post(self, url, json=None, **kw):
        return self.c.post(f"/api/v1{url}", json=json, headers=self.h(kw.pop("headers", None)), **kw)

    def patch(self, url, json=None, **kw):
        return self.c.patch(f"/api/v1{url}", json=json, headers=self.h(kw.pop("headers", None)), **kw)

    def put(self, url, json=None, **kw):
        return self.c.put(f"/api/v1{url}", json=json, headers=self.h(kw.pop("headers", None)), **kw)

    def delete(self, url, **kw):
        return self.c.delete(f"/api/v1{url}", headers=self.h(kw.pop("headers", None)), **kw)


def _phone() -> str:
    return "+23480" + str(uuid.uuid4().int)[:8]


@pytest.fixture
def make_user(client):
    def _make(name="Test User", phone_verified=True, email=None) -> Api:
        email = email or f"u{uuid.uuid4().hex[:10]}@example.com"
        r = client.post("/api/v1/auth/register", json={"full_name": name, "email": email, "phone": _phone(),
                                                       "password": PASSWORD})
        assert r.status_code == 201, r.text
        api = Api(client, r.json()["access_token"], r.json()["user"])
        if phone_verified:
            code = api.post("/auth/otp/request", {}).json()["dev_code"]
            assert api.post("/auth/otp/verify", {"code": code}).status_code == 200
        return api

    return _make


@pytest.fixture
def make_seller(make_user):
    def _make(name="Seller", store=None) -> Api:
        api = make_user(name)
        r = api.post("/sellers", {"store_name": store or f"Store {uuid.uuid4().hex[:6]}", "state": "Lagos", "city": "Ikeja"})
        assert r.status_code == 201, r.text
        api.seller = r.json()
        return api

    return _make


@pytest.fixture
def leaf_category(db):
    from app.models import Category

    return str(db.query(Category).filter(Category.slug == "mobile-phones").one().id)


@pytest.fixture
def make_product(leaf_category):
    def _make(seller: Api, **overrides) -> dict:
        body = {
            "title": "Apple iPhone 15 Pro Max 256GB", "description": "Brand new sealed device with warranty and receipt.",
            "category_id": leaf_category, "brand": "Apple", "model": "15 Pro Max", "condition": "brand_new",
            "price": "1500000.00", "negotiable": True, "quantity": 2, "state": "Lagos", "city": "Ikeja",
            "delivery_options": [{"type": "pickup", "label": "Pickup", "fee": "0", "eta_days": 0},
                                 {"type": "courier", "label": "Courier", "fee": "3500", "eta_days": 2}],
            "bnpl_enabled": True,
        }
        body.update(overrides)
        r = seller.post("/seller/products", body)
        assert r.status_code == 201, r.text
        return r.json()

    return _make


@pytest.fixture
def make_admin(client, db):
    from app.core.security import hash_password
    from app.models import Profile, User
    from app.models.enums import UserRole

    def _make(permissions: list[str] | None = None, super_admin=False) -> Api:
        email = f"admin{uuid.uuid4().hex[:8]}@goods.ng"
        u = User(email=email, full_name="Admin", password_hash=hash_password(PASSWORD),
                 role=UserRole.SUPER_ADMIN if super_admin else UserRole.ADMIN, admin_permissions=permissions or [])
        u.profile = Profile()
        db.add(u)
        db.commit()
        r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return Api(client, r.json()["access_token"], r.json()["user"])

    return _make


ADDRESS = {"full_name": "Ada Buyer", "phone": "08031112222", "state": "Lagos", "city": "Yaba", "street": "12 Herbert Macaulay Way"}


def simulate_payment(api: Api, reference: str, outcome="success", paid_amount: Decimal | None = None):
    body = {"outcome": outcome}
    if paid_amount is not None:
        body["paid_amount"] = str(paid_amount)
    r = api.post(f"/dev/mock-provider/payments/{reference}/simulate", body)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def paid_order(make_seller, make_user, make_product):
    """Returns (buyer, seller, product, order_detail) for a funded protected-checkout order."""

    def _make(quantity=1, delivery_option_index=1):
        seller = make_seller()
        product = make_product(seller)
        buyer = make_user("Buyer")
        r = buyer.post("/checkout", {"product_id": product["id"], "quantity": quantity,
                                     "delivery_option_index": delivery_option_index, "address": ADDRESS})
        assert r.status_code == 201, r.text
        simulate_payment(buyer, r.json()["payment_reference"])
        order = buyer.get(f"/orders/{r.json()['order_id']}").json()
        return buyer, seller, product, order

    return _make


def png_bytes(w=64, h=64) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (w, h), (20, 120, 80)).save(buf, "PNG")
    return buf.getvalue()
