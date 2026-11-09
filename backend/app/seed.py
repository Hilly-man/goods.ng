"""Seed reference data (+ optional demo data) — `python -m app.seed [--demo]`.

Reference data (categories, plans) is idempotent and safe in every environment.
Demo data (users, sellers, listings) is refused outside development.
"""

import argparse
import random
from datetime import timedelta
from decimal import Decimal

from slugify import slugify
from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.core.time import utcnow
from app.data.ng_locations import NG_CITIES
from app.models import Category, City, Product, Profile, SellerProfile, Subscription, SubscriptionPlan, User
from app.models.enums import (
    ProductCondition,
    ProductStatus,
    SubscriptionStatus,
    UserRole,
    VerificationLevel,
)

CATEGORIES = [
    ("Phones & Tablets", "smartphone", ["Mobile Phones", "Tablets", "Phone Accessories", "Smart Watches"]),
    ("Computers & Accessories", "laptop", ["Laptops", "Desktop Computers", "Computer Accessories", "Printers & Scanners", "Networking"]),
    ("Electronics", "tv", ["TVs", "Audio & Music", "Cameras", "Video Games & Consoles", "Generators & Solar"]),
    ("Fashion", "shirt", ["Men's Clothing", "Women's Clothing", "Watches", "Jewellery", "Native Wear"]),
    ("Shoes & Bags", "footprints", ["Men's Shoes", "Women's Shoes", "Bags", "Luggage"]),
    ("Home & Furniture", "sofa", ["Furniture", "Home Décor", "Kitchen & Dining", "Bedding"]),
    ("Home Appliances", "refrigerator", ["Refrigerators & Freezers", "Air Conditioners", "Washing Machines", "Cookers & Ovens", "Small Appliances"]),
    ("Vehicles", "car", ["Cars", "Motorcycles & Tricycles", "Buses & Vans", "Trucks & Trailers"]),
    ("Automobile Parts", "wrench", ["Car Parts", "Tyres & Rims", "Car Electronics", "Car Care"]),
    ("Property & Real Estate", "building-2", ["Houses & Apartments for Rent", "Houses & Apartments for Sale", "Land & Plots", "Commercial Property", "Short Let"]),
    ("Beauty & Personal Care", "sparkles", ["Hair & Wigs", "Skincare", "Makeup", "Fragrances", "Bath & Body"]),
    ("Sports & Fitness", "dumbbell", ["Gym Equipment", "Sports Wear", "Bicycles", "Outdoor"]),
    ("Baby & Kids", "baby", ["Baby Gear", "Kids' Clothing", "Toys", "Baby Care"]),
    ("Business Equipment", "briefcase", ["Office Furniture", "POS & Retail", "Printing Equipment", "Restaurant & Catering"]),
    ("Industrial Equipment", "factory", ["Heavy Machinery", "Manufacturing Equipment", "Power Tools", "Safety Equipment"]),
    ("Agriculture", "sprout", ["Farm Machinery", "Livestock & Poultry", "Seeds & Fertilisers", "Farm Produce"]),
    ("General Merchandise", "package", ["Books & Stationery", "Musical Instruments", "Arts & Crafts", "Other"]),
]

PLANS = [
    ("premium_monthly", "Premium Monthly", Decimal("15000.00"), 30, 3, 1),
    ("premium_quarterly", "Premium Quarterly", Decimal("40000.00"), 90, 10, 2),
    ("business_annual", "Business Annual", Decimal("150000.00"), 365, 50, 3),
]
PLAN_FEATURES = ["Premium Seller badge", "WhatsApp contact button", "Click-to-call button", "Enhanced storefront & banner",
                 "Advanced listing analytics", "Featured listing credits", "Priority search visibility", "Priority support"]


def seed_cities(db) -> None:
    existing = {(c.state, c.name) for c in db.scalars(select(City))}
    for state, cities in NG_CITIES.items():
        for i, name in enumerate(cities):
            if (state, name) not in existing:
                db.add(City(state=state, name=name, sort_order=i))


def seed_reference(db) -> None:
    from app.modules.staff.roles import ensure_system_roles

    seed_cities(db)
    ensure_system_roles(db)
    for i, (name, icon, subs) in enumerate(CATEGORIES):
        slug = slugify(name)
        cat = db.scalars(select(Category).where(Category.slug == slug)).first()
        if not cat:
            cat = Category(name=name, slug=slug, icon=icon, sort_order=i)
            db.add(cat)
            db.flush()
        for j, sub in enumerate(subs):
            sslug = slugify(sub)
            if not db.scalars(select(Category).where(Category.slug == sslug)).first():
                db.add(Category(name=sub, slug=sslug, parent_id=cat.id, sort_order=j))
    for code, name, price, days, quota, order in PLANS:
        if not db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.code == code)).first():
            db.add(SubscriptionPlan(code=code, name=name, price=price, interval_days=days, featured_listing_quota=quota,
                                    features=PLAN_FEATURES, sort_order=order))
    db.commit()


DEMO_PASSWORD = "GoodsNG2026!"

SELLERS = [
    ("Chinedu Okafor", "chinedu@demo.goods.ng", "+2348031234501", "Okafor Phones Hub", "Lagos", "Ikeja", True, VerificationLevel.BUSINESS),
    ("Aisha Bello", "aisha@demo.goods.ng", "+2348031234502", "Aisha's Fashion House", "Abuja", "Wuse 2", True, VerificationLevel.IDENTITY),
    ("Tunde Adeyemi", "tunde@demo.goods.ng", "+2348031234503", "Tunde Autos", "Lagos", "Lekki", False, VerificationLevel.IDENTITY),
    ("Ngozi Eze", "ngozi@demo.goods.ng", "+2348031234504", "HomeEase Appliances", "Rivers", "Port Harcourt", True, VerificationLevel.BUSINESS),
    ("Ibrahim Musa", "ibrahim@demo.goods.ng", "+2348031234505", "Musa Agro Supplies", "Kano", "Kano", False, VerificationLevel.PHONE),
    ("Funke Johnson", "funke@demo.goods.ng", "+2348031234506", "Funke's Gadget Corner", "Oyo", "Ibadan", False, VerificationLevel.UNVERIFIED),
]

# (seller index, subcategory slug, title, brand, model, condition, price, negotiable, bnpl, qty)
LISTINGS = [
    (0, "mobile-phones", "Apple iPhone 15 Pro Max 256GB Natural Titanium", "Apple", "iPhone 15 Pro Max", "brand_new", 1500000, True, True, 4),
    (0, "mobile-phones", "Samsung Galaxy S24 Ultra 512GB", "Samsung", "Galaxy S24 Ultra", "brand_new", 1350000, True, True, 3),
    (0, "mobile-phones", "Apple iPhone 13 128GB Midnight — UK Used", "Apple", "iPhone 13", "foreign_used", 465000, True, True, 6),
    (0, "mobile-phones", "Tecno Camon 30 Pro 5G 512GB", "Tecno", "Camon 30 Pro", "brand_new", 389000, True, False, 10),
    (0, "mobile-phones", "Infinix Note 40 Pro 256GB", "Infinix", "Note 40 Pro", "brand_new", 299000, False, False, 12),
    (0, "tablets", "Apple iPad Air M2 11-inch 128GB Wi-Fi", "Apple", "iPad Air M2", "brand_new", 980000, True, True, 2),
    (0, "phone-accessories", "Oraimo FreePods 4 ANC Earbuds", "Oraimo", "FreePods 4", "brand_new", 38500, False, False, 30),
    (0, "smart-watches", "Apple Watch Series 9 45mm GPS", "Apple", "Series 9", "foreign_used", 310000, True, False, 2),
    (5, "laptops", "HP EliteBook 840 G6 Core i7 16GB 512GB SSD", "HP", "EliteBook 840 G6", "foreign_used", 395000, True, True, 5),
    (5, "laptops", "Apple MacBook Air M2 13-inch 8GB 256GB", "Apple", "MacBook Air M2", "brand_new", 1250000, True, True, 2),
    (5, "laptops", "Lenovo ThinkPad T480 Core i5 8GB 256GB", "Lenovo", "ThinkPad T480", "refurbished", 235000, True, False, 7),
    (5, "video-games-consoles", "Sony PlayStation 5 Slim Disc Edition", "Sony", "PS5 Slim", "brand_new", 820000, True, True, 3),
    (5, "computer-accessories", "Logitech MX Master 3S Wireless Mouse", "Logitech", "MX Master 3S", "brand_new", 95000, False, False, 15),
    (5, "audio-music", "JBL PartyBox 310 Bluetooth Speaker", "JBL", "PartyBox 310", "brand_new", 610000, True, False, 2),
    (3, "tvs", "LG 55-inch 4K UHD Smart TV (55UR8050)", "LG", "55UR8050", "brand_new", 545000, True, True, 4),
    (3, "tvs", "Hisense 43-inch Full HD Smart TV", "Hisense", "43A4K", "brand_new", 248000, True, True, 8),
    (3, "refrigerators-freezers", "Haier Thermocool 250L Double Door Refrigerator", "Haier Thermocool", "HRF-250", "brand_new", 465000, True, True, 5),
    (3, "air-conditioners", "Midea 1.5HP Split Inverter Air Conditioner", "Midea", "MSAF-12", "brand_new", 520000, True, True, 6),
    (3, "washing-machines", "Samsung 8kg Front Load Washing Machine", "Samsung", "WW80T", "brand_new", 610000, True, True, 3),
    (3, "generators-solar", "5KVA Inverter + 4 x 200Ah Batteries Solar Package", "Felicity", "5KVA", "brand_new", 2450000, True, True, 2),
    (3, "generators-solar", "Sumec Firman SPG3000E2 Generator", "Sumec Firman", "SPG3000E2", "brand_new", 395000, True, False, 9),
    (3, "cookers-ovens", "Scanfrost 4-Burner Gas Cooker with Oven", "Scanfrost", "SFC5402", "brand_new", 289000, True, False, 4),
    (1, "women-s-clothing", "Elegant Ankara Peplum Gown — Made to Order", "Aisha's", None, "brand_new", 45000, True, False, 20),
    (1, "native-wear", "Men's Senator Kaftan — Premium Cashmere", "Aisha's", None, "brand_new", 38000, True, False, 25),
    (1, "bags", "Ladies Leather Tote Handbag", "Zara", None, "brand_new", 52000, True, False, 10),
    (1, "watches", "Casio G-Shock GA-2100 Black", "Casio", "GA-2100", "brand_new", 89000, False, False, 6),
    (1, "fragrances", "Dior Sauvage Eau de Parfum 100ml", "Dior", "Sauvage EDP", "brand_new", 185000, True, False, 5),
    (1, "hair-wigs", "Bone Straight Human Hair Wig 24 inches", None, None, "brand_new", 265000, True, True, 4),
    (1, "men-s-shoes", "Clarks Desert Boots Suede", "Clarks", "Desert Boot", "brand_new", 120000, True, False, 6),
    (2, "cars", "Toyota Camry 2018 SE — Foreign Used, Accident Free", "Toyota", "Camry SE", "foreign_used", 18500000, True, False, 1),
    (2, "cars", "Lexus RX 350 2016 — Clean Title", "Lexus", "RX 350", "foreign_used", 27500000, True, False, 1),
    (2, "cars", "Honda Accord 2013 — Nigerian Used, Buy & Drive", "Honda", "Accord", "nigerian_used", 7800000, True, False, 1),
    (2, "cars", "Toyota Corolla 2015 LE", "Toyota", "Corolla LE", "foreign_used", 11200000, True, False, 1),
    (2, "motorcycles-tricycles", "Bajaj Boxer BM150 Motorcycle", "Bajaj", "Boxer BM150", "brand_new", 1150000, True, True, 3),
    (2, "tyres-rims", "Michelin Primacy 4 — 215/55 R17 (Set of 4)", "Michelin", "Primacy 4", "brand_new", 480000, True, False, 5),
    (4, "farm-machinery", "Mahindra 575 DI Tractor", "Mahindra", "575 DI", "brand_new", 24500000, True, False, 1),
    (4, "seeds-fertilisers", "NPK 15:15:15 Fertiliser — 50kg Bag", "Indorama", None, "brand_new", 38000, False, False, 200),
    (4, "livestock-poultry", "Day-Old Broiler Chicks (Carton of 50)", None, None, "brand_new", 42500, True, False, 40),
    (4, "farm-produce", "Premium Local Rice — 50kg Bag", None, None, "brand_new", 78000, True, False, 100),
    (4, "heavy-machinery", "Caterpillar 320D Excavator — Foreign Used", "Caterpillar", "320D", "foreign_used", 95000000, True, False, 1),
    (3, "furniture", "7-Seater L-Shaped Fabric Sofa", None, None, "brand_new", 650000, True, True, 3),
    (3, "office-furniture", "Executive Ergonomic Office Chair", None, None, "brand_new", 145000, True, False, 12),
    (3, "pos-retail", "Moniepoint-Compatible Android POS Terminal", None, None, "brand_new", 95000, True, False, 15),
    (5, "gym-equipment", "Adjustable Dumbbell Set 2 x 24kg", "Bowflex", "SelectTech 552", "brand_new", 420000, True, False, 3),
    (5, "bicycles", "Mountain Bike 26-inch 21-Speed", None, None, "brand_new", 165000, True, False, 6),
    (1, "toys", "Kids Ride-On Electric Car with Remote", None, None, "brand_new", 210000, True, False, 4),
    (1, "baby-gear", "Joie Travel System Stroller + Car Seat", "Joie", None, "brand_new", 340000, True, True, 3),
    (2, "houses-apartments-for-rent", "Newly Built 3-Bedroom Flat — Lekki Phase 1 (Annual)", None, None, "brand_new", 6500000, True, False, 1),
    (4, "land-plots", "600sqm Dry Land with C of O — Lugbe, Abuja", None, None, "brand_new", 15000000, True, False, 1),
    (0, "books-stationery", "Waec & Jamb Past Questions Bundle (2010–2025)", None, None, "brand_new", 12000, False, False, 50),
]

DESCRIPTIONS = {
    "brand_new": "Brand new and sealed with full manufacturer warranty. Original product — we do not sell replicas. "
                 "Delivery available nationwide; pickup from our store also possible. Buy with Goods.ng Protected "
                 "Checkout so your money is safeguarded until you receive the item.",
    "foreign_used": "Clean foreign-used item in excellent condition, thoroughly inspected and tested. No faults. "
                    "Inspection welcome before purchase. Pay through Goods.ng Protected Checkout for full buyer protection.",
    "nigerian_used": "Neatly used and well maintained. Everything works perfectly. Serious buyers only — "
                     "inspection allowed. Price is slightly negotiable.",
    "refurbished": "Professionally refurbished, tested and graded A. Comes with a 3-month seller warranty. "
                   "Battery health and specifications verified.",
}


def seed_demo(db) -> None:
    if settings.environment not in ("development", "test", "staging"):
        raise SystemExit("Refusing to seed demo data outside development, test or staging")
    pw = hash_password(DEMO_PASSWORD)
    if not db.scalars(select(User).where(User.email == "admin@goods.ng")).first():
        admin = User(email="admin@goods.ng", full_name="Goods.ng Admin", password_hash=pw, role=UserRole.SUPER_ADMIN,
                     account_type="staff",
                     email_verified=True, admin_permissions=[])
        admin.profile = Profile()
        db.add(admin)
    if not db.scalars(select(User).where(User.email == "buyer@demo.goods.ng")).first():
        b = User(email="buyer@demo.goods.ng", phone="+2348031234599", full_name="Adaeze Nwosu", password_hash=pw,
                 phone_verified=True, email_verified=True, admin_permissions=[])
        b.profile = Profile(state="Lagos", city="Yaba")
        db.add(b)
    db.flush()
    plan = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.code == "premium_monthly")).one()
    sellers = []
    now = utcnow()
    for name, email, phone, store, state, city, premium, level in SELLERS:
        u = db.scalars(select(User).where(User.email == email)).first()
        if not u:
            u = User(email=email, phone=phone, full_name=name, password_hash=pw, phone_verified=True,
                     email_verified=True, admin_permissions=[])
            u.profile = Profile(state=state, city=city)
            db.add(u)
            db.flush()
        s = db.scalars(select(SellerProfile).where(SellerProfile.user_id == u.id)).first()
        if not s:
            s = SellerProfile(user_id=u.id, store_name=store, slug=slugify(store), state=state, city=city,
                              description=f"{store} — trusted seller in {city}, {state}. Quality products, honest prices "
                                          f"and fast delivery.", business_phone=phone, whatsapp_number=phone,
                              whatsapp_enabled=premium, phone_enabled=premium, verification_level=level,
                              business_hours="Mon–Sat, 9am–6pm" if premium else None,
                              rating_avg=Decimal(random.choice(["4.50", "4.70", "4.80", "4.90", "4.60"])),
                              rating_count=random.randint(8, 140), completed_sales=random.randint(5, 300))
            db.add(s)
            db.flush()
            if premium:
                db.add(Subscription(seller_id=s.id, plan_id=plan.id, amount=0, status=SubscriptionStatus.ACTIVE,
                                    current_period_start=now - timedelta(days=1),
                                    current_period_end=now + timedelta(days=365)))
        sellers.append(s)
    db.flush()
    cats = {c.slug: c for c in db.scalars(select(Category))}
    rnd = random.Random(42)
    for i, (si, sub, title, brand, model, cond, price, neg, bnpl, qty) in enumerate(LISTINGS):
        slug = slugify(title)[:150] + f"-{i:04d}"
        if db.scalars(select(Product).where(Product.slug == slug)).first():
            continue
        s, c = sellers[si], cats[sub]
        price = Decimal(price)
        delivery = [{"type": "pickup", "label": f"Pickup in {s.city}", "fee": "0.00", "eta_days": 0}]
        if price < 5_000_000:
            delivery.append({"type": "courier", "label": "Courier delivery (nationwide)",
                             "fee": "3500.00" if price < 500000 else "7500.00", "eta_days": 3})
            delivery.append({"type": "seller_delivery", "label": f"Seller delivery within {s.state}",
                             "fee": "2000.00", "eta_days": 1})
        created = now - timedelta(hours=rnd.randint(1, 24 * 40))
        db.add(Product(
            seller_id=s.id, category_id=c.parent_id, subcategory_id=c.id, title=title, slug=slug,
            description=f"{title}.\n\n{DESCRIPTIONS[cond]}", brand=brand, model=model, condition=ProductCondition(cond),
            price=price, negotiable=neg, quantity=qty, state=s.state, city=s.city, delivery_options=delivery,
            protected_checkout_enabled=True, bnpl_enabled=bnpl and price <= 3_000_000, status=ProductStatus.ACTIVE,
            is_featured=i % 7 == 0, featured_until=now + timedelta(days=14) if i % 7 == 0 else None,
            views_count=rnd.randint(20, 2500), favourites_count=rnd.randint(0, 120), enquiries_count=rnd.randint(0, 40),
            published_at=created, created_at=created,
        ))
    db.commit()
    print(f"Demo data ready. All demo accounts use password: {DEMO_PASSWORD}")
    print("  admin@goods.ng (super admin) · buyer@demo.goods.ng (buyer) · chinedu@demo.goods.ng (premium seller)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        seed_reference(db)
        print("Reference data seeded (categories, plans).")
        if args.demo:
            seed_demo(db)


if __name__ == "__main__":
    main()
