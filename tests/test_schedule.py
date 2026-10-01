from datetime import time
from types import SimpleNamespace

import pytest
from schedule import Scheduler

import ai_marketplace_monitor.monitor as monitor_module
from ai_marketplace_monitor.facebook import FacebookItemConfig, FacebookMarketplaceConfig
from ai_marketplace_monitor.monitor import MarketplaceMonitor


def test_all_daily_start_times_are_scheduled(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = Scheduler()
    monkeypatch.setattr(monitor_module, "schedule", scheduler)

    class FakeMarketplace:
        def configure(self, *_: object, **__: object) -> None:
            pass

    marketplace = FakeMarketplace()
    marketplace_config = FacebookMarketplaceConfig(name="facebook", start_at=["10:00", "17:00"])
    item_config = FacebookItemConfig(name="desk", search_phrases=["desk"])
    config = SimpleNamespace(
        marketplace={"facebook": marketplace_config},
        item={"desk": item_config},
    )
    monitor = object.__new__(MarketplaceMonitor)
    monitor.config = config
    monitor.active_marketplaces = {"facebook": marketplace}
    monitor.browser = None
    monitor.keyboard_monitor = None
    monitor.logger = None
    monitor.load_config_file = lambda: config
    monitor.load_ai_agents = lambda: None
    monitor._select_translator = lambda _: None

    monitor.schedule_jobs()

    assert len(scheduler.jobs) == 2
    assert {job.at_time for job in scheduler.jobs} == {time(10, 0), time(17, 0)}
    assert all(job.tags == {"desk"} for job in scheduler.jobs)


def test_fixed_daily_times_wait_until_scheduled_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler = Scheduler()
    schedule_api = SimpleNamespace(
        every=scheduler.every,
        get_jobs=scheduler.get_jobs,
        jobs=scheduler.jobs,
        idle_seconds=lambda: scheduler.idle_seconds,
        clear=scheduler.clear,
        run_pending=scheduler.run_pending,
    )
    monkeypatch.setattr(monitor_module, "schedule", schedule_api)
    monkeypatch.setattr(monitor_module, "calculate_file_hash", lambda _: "same")

    class FakeKeyboardMonitor:
        def start(self) -> None:
            pass

    class FakeMarketplace:
        def configure(self, *_: object, **__: object) -> None:
            pass

    class StopAfterSchedulingError(Exception):
        pass

    def stop_at_first_wait(*_: object, **__: object) -> None:
        raise StopAfterSchedulingError

    monkeypatch.setattr(monitor_module, "KeyboardMonitor", FakeKeyboardMonitor)
    monkeypatch.setattr(monitor_module, "doze", stop_at_first_wait)

    marketplace_config = FacebookMarketplaceConfig(name="facebook", start_at=["10:00", "17:00"])
    item_config = FacebookItemConfig(name="desk", search_phrases=["desk"])
    config = SimpleNamespace(
        marketplace={"facebook": marketplace_config},
        item={"desk": item_config},
    )
    monitor = object.__new__(MarketplaceMonitor)
    monitor.config = config
    monitor.config_files = []
    monitor.config_hash = "same"
    monitor.active_marketplaces = {"facebook": FakeMarketplace()}
    monitor.browser = None
    monitor.logger = None
    monitor.defer_login_until_credentials = False
    monitor.load_config_file = lambda: config
    monitor.load_ai_agents = lambda: None
    monitor._select_translator = lambda _: None
    monitor._launch_browser = lambda: object()
    monitor.handle_pause = lambda: None
    searches = []
    monitor.search_item = lambda *args: searches.append(args)

    with pytest.raises(StopAfterSchedulingError):
        monitor.start_monitor()

    assert searches == []
    assert len(scheduler.jobs) == 2
