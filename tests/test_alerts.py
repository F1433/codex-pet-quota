import tempfile
import unittest
from pathlib import Path

from codex_pet_quota.alerts import AlertEngine
from codex_pet_quota.models import WeeklyQuotaView
from codex_pet_quota.storage import AlertStateStore


def view(remaining, reset=2000, scope="scope"):
    return WeeklyQuotaView(
        state="ready",
        scope_key=scope,
        source="cli-rpc",
        fetched_at=1,
        remaining_percent=remaining,
        used_percent=100 - remaining,
        resets_at=reset,
    )


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = AlertEngine(AlertStateStore(Path(self.temp.name)))

    def tearDown(self):
        self.temp.cleanup()

    def test_strict_threshold(self):
        self.assertFalse(self.engine.evaluate(view(20), now=1000).should_notify)
        self.assertTrue(self.engine.evaluate(view(19.9), now=1001).should_notify)

    def test_once_per_cycle(self):
        self.assertTrue(self.engine.evaluate(view(19), now=1000).should_notify)
        self.assertFalse(self.engine.evaluate(view(18), now=1001).should_notify)
        self.assertFalse(self.engine.evaluate(view(17), now=1002).should_notify)

    def test_hysteresis_requires_two_high_reads(self):
        self.assertTrue(self.engine.evaluate(view(19), now=1000).badge_visible)
        self.assertTrue(self.engine.evaluate(view(26), now=1001).badge_visible)
        self.assertFalse(self.engine.evaluate(view(26), now=1002).badge_visible)

    def test_scope_isolation(self):
        self.assertTrue(self.engine.evaluate(view(10, scope="a"), now=1000).should_notify)
        self.assertTrue(self.engine.evaluate(view(10, scope="b"), now=1000).should_notify)

    def test_new_confirmed_cycle_can_alert_again(self):
        self.assertTrue(self.engine.evaluate(view(10, reset=2000), now=1000).should_notify)
        self.assertTrue(self.engine.evaluate(view(10, reset=900000), now=2100).should_notify)


if __name__ == "__main__":
    unittest.main()

