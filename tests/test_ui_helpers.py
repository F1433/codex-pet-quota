import datetime as dt
import unittest

from codex_pet_quota.models import PetTarget
from codex_pet_quota.ui import format_reset_relative, translate_target


class ResetTimeFormattingTests(unittest.TestCase):
    def test_days_until_reset(self):
        now = dt.datetime.now().astimezone().replace(microsecond=0)
        reset = int((now + dt.timedelta(days=3, seconds=1)).timestamp())
        self.assertEqual(format_reset_relative(reset, now), "4天后重置")

    def test_today_and_expired(self):
        now = dt.datetime.now().astimezone().replace(microsecond=0)
        self.assertEqual(
            format_reset_relative(int((now + dt.timedelta(hours=2)).timestamp()), now),
            "今天重置",
        )
        self.assertEqual(
            format_reset_relative(int((now - dt.timedelta(seconds=1)).timestamp()), now),
            "即将重置",
        )


class DragFollowingTests(unittest.TestCase):
    def test_target_follows_cursor_delta(self):
        original = PetTarget(1, 2, (100, 200, 210, 310), 100, "pet", "official")
        moved = translate_target(original, -37, 24)
        self.assertEqual(moved.rect, (63, 224, 173, 334))
        self.assertEqual(moved.confidence, "cursor-drag-follow")
