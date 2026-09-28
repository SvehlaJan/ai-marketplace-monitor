from types import SimpleNamespace

import pytest

import ai_marketplace_monitor.monitor as monitor_module
from ai_marketplace_monitor.ai import AIResponse
from ai_marketplace_monitor.facebook import FacebookItemConfig, FacebookMarketplaceConfig
from ai_marketplace_monitor.listing import Listing
from ai_marketplace_monitor.monitor import MarketplaceMonitor
from ai_marketplace_monitor.notification import NotificationStatus


def test_failed_ai_evaluation_does_not_notify(
    monkeypatch: pytest.MonkeyPatch, listing: Listing
) -> None:
    notifications = []

    class FakeUser:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def notification_status(self, listing: Listing) -> NotificationStatus:
            return NotificationStatus.NOT_NOTIFIED

        def notify(self, listings: list[Listing], ratings: list[AIResponse], item: object) -> None:
            notifications.extend(listings)

    class FailingAI:
        config = SimpleNamespace(name="gemini")

        def evaluate(self, *args: object) -> AIResponse:
            raise RuntimeError("simulated API outage")

    monkeypatch.setattr(monitor_module, "User", FakeUser)
    monkeypatch.setattr(monitor_module.time, "sleep", lambda _: None)
    monitor = object.__new__(MarketplaceMonitor)
    monitor.config = SimpleNamespace(user={"email": SimpleNamespace(name="email")})
    monitor.ai_agents = [FailingAI()]
    monitor.logger = None
    item_config = FacebookItemConfig(
        name="desk", search_phrases=["PC stul"], rating=2, notify=["email"]
    )
    marketplace_config = FacebookMarketplaceConfig(name="facebook", notify=["email"])
    marketplace = SimpleNamespace(search=lambda _: iter([listing]))

    monitor.search_item(marketplace_config, marketplace, item_config)

    assert notifications == []
