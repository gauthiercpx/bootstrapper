"""Name derivation — the one place a typo silently produces a broken project."""

from __future__ import annotations

import pytest

from bootstrapper.core import naming


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Market API", "market-api"),
        ("market_api", "market-api"),
        ("MarketAPI", "market-api"),
        ("  Market   API  ", "market-api"),
        ("Marché Financier", "marche-financier"),
        ("my.cool/project", "my-cool-project"),
        ("2fa-service", "2fa-service"),
    ],
)
def test_slugify(value: str, expected: str) -> None:
    assert naming.slugify(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Market API", "market_api"),
        ("2fa service", "_2fa_service"),  # a package cannot start with a digit
        ("class", "class_"),  # nor be a keyword
        ("!!!", "app"),  # nor be empty
    ],
)
def test_package_name(value: str, expected: str) -> None:
    assert naming.package_name(value) == expected


def test_class_prefix_and_env_prefix() -> None:
    assert naming.class_prefix("market api") == "MarketApi"
    assert naming.env_prefix("Market API") == "MARKET_API_"
