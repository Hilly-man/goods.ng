"""Branded transactional email layout shared by every notification."""

from __future__ import annotations

import html
import re
from urllib.parse import urljoin

from app.core.config import settings

BRAND = "Goods.ng"
TAGLINE = "Buy. Sell. Trade with Confidence."
SUPPORT_EMAIL = "support@goods.ng"
PHONE = "+234 201 330 0000"
PHONE_HREF = "tel:+2342013300000"
OFFICE = "Lagos, Nigeria"
SITE = settings.frontend_url.rstrip("/")
LOGO = f"{SITE}/icon-192.png"

CANVAS = "#f4f7f4"
CARD = "#ffffff"
INK = "#0f1611"
MUTED = "#55635a"
LINE = "#e2e8e3"
BRAND_DARK = "#18251d"
BRAND_700 = "#263a2d"
BRAND_50 = "#f2f7f3"
BRAND_200 = "#c5d8c9"
BRAND_300 = "#a0bda6"
ACCENT = "#b7ff73"
ACCENT_TEXT = "#3f6b1a"
FONT = "Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

SOCIAL = (
    ("Instagram", "https://instagram.com/goods.ng"),
    ("X", "https://x.com/goodsng"),
    ("TikTok", "https://tiktok.com/@goods.ng"),
    ("YouTube", "https://youtube.com/@goodsng"),
    ("WhatsApp", "https://wa.me/2342013300000"),
)

EVENT_META: dict[str, tuple[str, str | None, str]] = {
    "registration": ("Welcome", "Start exploring", "/"),
    "password_reset": ("Account security", "Reset password", "/forgot-password"),
    "staff_invite": ("Admin invitation", "Set your password", "/"),
    "flex_workplace": ("Goods Flex", "Confirm your workplace", "/flex"),
    "otp": ("Verification", None, "/"),
    "new_offer": ("Negotiation", "View offer", "/offers"),
    "counter_offer": ("Negotiation", "View counteroffer", "/offers"),
    "offer_accepted": ("Negotiation", "Complete your purchase", "/offers"),
    "offer_rejected": ("Negotiation", "Browse similar items", "/search"),
    "new_order": ("Orders", "View order", "/orders"),
    "payment_confirmed": ("Payment", "View order", "/orders"),
    "order_update": ("Order update", "View order", "/orders"),
    "seller_dispatch": ("Shipping", "Track order", "/orders"),
    "delivery_update": ("Delivery", "View order", "/orders"),
    "dispute": ("Buyer protection", "View dispute", "/orders"),
    "refund": ("Refunds", "View refund", "/orders"),
    "funds_released": ("Seller payouts", "View earnings", "/seller/earnings"),
    "bnpl_decision": ("Goods Flex", "Open Goods Flex", "/flex"),
    "repayment_reminder": ("Goods Flex", "View instalments", "/flex"),
    "guarantor_response": ("Goods Flex", "View request", "/flex"),
    "subscription": ("Premium Seller", "Manage subscription", "/seller/subscription"),
    "promotion": ("Listing promotion", "View listing", "/seller/products"),
    "verification": ("Verification", "View status", "/seller/verification"),
    "listing_moderation": ("Listing update", "View listing", "/seller/products"),
    "review": ("Reviews", "View storefront", "/seller"),
    "new_message": ("Messages", "Reply", "/messages"),
}


def _esc(value: str | None) -> str:
    return html.escape(value or "", quote=True)


def _absolute(link: str | None) -> str | None:
    if not link:
        return None
    if re.match(r"^https?://", link, re.I):
        return link
    return urljoin(f"{SITE}/", link.lstrip("/"))


def _paragraphs(body: str) -> str:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", body.strip()) if b.strip()]
    out = []
    for block in blocks:
        text = _esc(block).replace("\n", "<br>")
        out.append(
            f'<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:1.65;color:{MUTED};">{text}</p>'
        )
    return "".join(out)


def _code_box(code: str) -> str:
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="margin:24px 0;background:{BRAND_50};border:1px solid {BRAND_200};border-radius:12px;">'
        f'<tr><td align="center" style="padding:20px 16px;">'
        f'<div style="font-family:{FONT};font-size:11px;font-weight:700;letter-spacing:.14em;'
        f'text-transform:uppercase;color:{ACCENT_TEXT};">Your code</div>'
        f'<div style="margin:6px 0 4px;font-family:{FONT};font-size:34px;font-weight:800;'
        f'letter-spacing:.22em;color:{BRAND_DARK};">{_esc(code)}</div>'
        f'<div style="margin-top:14px;">'
        f'<span id="gng-copy" role="button" '
        f'onclick="var t=\'{_esc(code)}\';'
        f'if(navigator.clipboard){{navigator.clipboard.writeText(t).then('
        f'function(){{document.getElementById(\'gng-copy\').textContent=\'Copied\';}},'
        f'function(){{window.prompt(\'Copy your code:\',t);}});}}'
        f'else{{window.prompt(\'Copy your code:\',t);}}return false;" '
        f'style="display:inline-block;cursor:pointer;padding:9px 18px;border-radius:8px;background:{BRAND_700};'
        f'color:#ffffff;font-family:{FONT};font-size:13px;font-weight:700;text-decoration:none;">'
        f'Copy code</span></div>'
        f'<div style="margin-top:10px;font-family:{FONT};font-size:12px;line-height:1.5;color:{MUTED};">'
        f'Expires in {settings.otp_ttl_minutes} minutes. Never share this code. '
        f'If the button does not work, select the code above and copy it.</div>'
        f'</td></tr></table>'
    )


def _button(label: str, href: str) -> str:
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:28px 0 8px;">'
        f'<tr><td align="center" bgcolor="{BRAND_700}" style="border-radius:10px;">'
        f'<a href="{_esc(href)}" style="display:inline-block;padding:14px 26px;font-family:{FONT};'
        f'font-size:15px;font-weight:700;line-height:1;color:#ffffff;text-decoration:none;border-radius:10px;">'
        f'{_esc(label)}</a></td></tr></table>'
    )


def _footer() -> str:
    socials = " &nbsp;·&nbsp; ".join(
        f'<a href="{_esc(url)}" style="color:{BRAND_200};text-decoration:none;">{_esc(name)}</a>'
        for name, url in SOCIAL
    )
    links = " &nbsp;·&nbsp; ".join(
        f'<a href="{_esc(url)}" style="color:{BRAND_200};text-decoration:none;">{label}</a>'
        for label, url in (
            ("Help centre", f"{SITE}/faq"),
            ("Buyer protection", f"{SITE}/buyer-protection"),
            ("Notification settings", f"{SITE}/account/notifications"),
            ("Terms", f"{SITE}/terms"),
            ("Privacy", f"{SITE}/privacy"),
        )
    )
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td align="center" style="padding:0 16px 36px;">'
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" '
        f'style="width:100%;max-width:600px;background:{BRAND_DARK};border-radius:16px;">'
        f'<tr><td style="padding:26px 28px;">'
        f'<div style="font-family:{FONT};font-size:17px;font-weight:800;color:#ffffff;">'
        f'Goods<span style="color:{ACCENT};">.ng</span></div>'
        f'<div style="margin-top:4px;font-family:{FONT};font-size:13px;color:{BRAND_300};">{TAGLINE}</div>'
        f'<div style="margin-top:18px;font-family:{FONT};font-size:13px;line-height:1.8;color:{BRAND_200};">'
        f'<a href="mailto:{SUPPORT_EMAIL}" style="color:#ffffff;text-decoration:none;">{SUPPORT_EMAIL}</a>'
        f' &nbsp;·&nbsp; <a href="{PHONE_HREF}" style="color:#ffffff;text-decoration:none;">{PHONE}</a>'
        f' &nbsp;·&nbsp; {OFFICE}</div>'
        f'<div style="margin-top:12px;font-family:{FONT};font-size:12px;line-height:1.9;">{socials}</div>'
        f'<div style="margin-top:14px;padding-top:14px;border-top:1px solid rgba(255,255,255,.12);'
        f'font-family:{FONT};font-size:12px;line-height:1.9;">{links}</div>'
        f'<div style="margin-top:14px;font-family:{FONT};font-size:11px;line-height:1.7;color:{BRAND_300};">'
        f'© 2026 Goods.ng. All rights reserved.<br>'
        f'You received this because you have a Goods.ng account. '
        f'<a href="{SITE}/account/notifications" style="color:{BRAND_200};">Update your email preferences</a>.'
        f'</div></td></tr></table></td></tr></table>'
    )


def render_email(
    event_type: str,
    title: str,
    body: str,
    link: str | None = None,
    recipient_name: str | None = None,
    code: str | None = None,
) -> str:
    eyebrow, cta_label, default_path = EVENT_META.get(event_type, ("Notification", "Open Goods.ng", "/"))
    href = _absolute(link or default_path)
    first_name = (recipient_name or "").strip().split(" ")[0] if recipient_name else ""
    greeting = (
        f'<p style="margin:0 0 14px;font-family:{FONT};font-size:15px;line-height:1.65;color:{INK};">'
        f'Hi {_esc(first_name)},</p>' if first_name else ""
    )
    content = _code_box(code) if code else _paragraphs(body)
    button = _button(cta_label, href) if cta_label and href else ""
    preheader = _esc(title)
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="color-scheme" content="light only"><title>{_esc(title)}</title></head>'
        f'<body style="margin:0;padding:0;background:{CANVAS};">'
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{preheader}</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:{BRAND_DARK};">'
        f'<tr><td align="center" style="padding:22px 16px;">'
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" '
        f'style="width:100%;max-width:600px;"><tr><td align="left">'
        f'<a href="{SITE}" style="text-decoration:none;">'
        f'<img src="{LOGO}" width="36" height="36" alt="Goods.ng" '
        f'style="display:inline-block;vertical-align:middle;border-radius:9px;border:0;">'
        f'<span style="display:inline-block;vertical-align:middle;margin-left:10px;font-family:{FONT};'
        f'font-size:21px;font-weight:800;letter-spacing:-.02em;color:#ffffff;">'
        f'Goods<span style="color:{ACCENT};">.ng</span></span></a>'
        f'</td></tr></table></td></tr>'
        f'<tr><td style="height:3px;background:{ACCENT};font-size:0;line-height:0;">&nbsp;</td></tr></table>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:{CANVAS};"><tr><td align="center" style="padding:32px 16px;">'
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" '
        f'style="width:100%;max-width:600px;background:{CARD};border:1px solid {LINE};border-radius:16px;">'
        f'<tr><td style="padding:34px 32px 30px;">'
        f'<div style="font-family:{FONT};font-size:11px;font-weight:700;letter-spacing:.14em;'
        f'text-transform:uppercase;color:{ACCENT_TEXT};margin-bottom:10px;">{_esc(eyebrow)}</div>'
        f'<h1 style="margin:0 0 18px;font-family:{FONT};font-size:25px;line-height:1.25;'
        f'letter-spacing:-.02em;color:{INK};">{_esc(title)}</h1>'
        f'{greeting}{content}{button}'
        f'<p style="margin:22px 0 0;font-family:{FONT};font-size:13px;line-height:1.6;color:{MUTED};">'
        f'Need a hand? Email <a href="mailto:{SUPPORT_EMAIL}" style="color:{ACCENT_TEXT};'
        f'font-weight:600;text-decoration:none;">{SUPPORT_EMAIL}</a> or call {PHONE} '
        f'(Mon–Sat, 8am–8pm).</p>'
        f'</td></tr></table>'
        f'<div style="height:20px;font-size:0;line-height:0;">&nbsp;</div>'
        f'{_footer()}'
        f'</td></tr></table></body></html>'
    )


def render_text(title: str, body: str) -> str:
    return (
        f"{title}\n\n{body}\n\n"
        f"—\n{BRAND} · {TAGLINE}\n"
        f"Support: {SUPPORT_EMAIL} · {PHONE} · {OFFICE}\n"
        f"Manage notifications: {SITE}/account/notifications"
    )
