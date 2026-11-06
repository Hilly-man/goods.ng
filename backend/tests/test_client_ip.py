"""Trusted-proxy handling for client IP resolution."""

from app.core.deps import resolve_client_ip

TRUSTED = ["10.0.0.0/8"]


def test_forwarded_header_is_ignored_without_trusted_proxies():
    assert resolve_client_ip("203.0.113.5", "1.2.3.4", []) == "203.0.113.5"


def test_forwarded_header_is_ignored_when_peer_is_not_a_trusted_proxy():
    assert resolve_client_ip("203.0.113.5", "1.2.3.4", TRUSTED) == "203.0.113.5"


def test_rightmost_untrusted_address_wins():
    assert resolve_client_ip("10.0.0.2", "1.2.3.4, 10.0.0.9", TRUSTED) == "1.2.3.4"


def test_multiple_trusted_proxies_are_skipped():
    assert resolve_client_ip("10.0.0.2", "1.2.3.4, 10.0.0.9, 10.0.0.8", TRUSTED) == "1.2.3.4"


def test_all_trusted_chain_falls_back_to_leftmost():
    assert resolve_client_ip("10.0.0.2", "10.0.0.9, 10.0.0.8", TRUSTED) == "10.0.0.9"


def test_invalid_forwarded_entries_are_ignored():
    assert resolve_client_ip("10.0.0.2", "not-an-ip, 1.2.3.4", TRUSTED) == "1.2.3.4"


def test_invalid_cidr_is_ignored():
    assert resolve_client_ip("10.0.0.2", "1.2.3.4", ["not-a-cidr"]) == "10.0.0.2"
