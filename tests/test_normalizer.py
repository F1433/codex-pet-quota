import unittest

from codex_pet_quota.normalizer import normalize_weekly


def payload(weekly_used=None, five_hour_used=0, include_week=True):
    bucket = {
        "limitId": "codex",
        "primary": {"usedPercent": five_hour_used, "windowDurationMins": 300, "resetsAt": 100},
        "secondary": (
            {"usedPercent": weekly_used, "windowDurationMins": 10080, "resetsAt": 200}
            if include_week
            else None
        ),
    }
    return {"rateLimitsByLimitId": {"codex": bucket}}


class NormalizerTests(unittest.TestCase):
    def test_used_to_remaining(self):
        view = normalize_weekly(payload(82), "scope", 1)
        self.assertEqual(view.remaining_percent, 18)
        self.assertEqual(view.resets_at, 200)

    def test_boundary_values(self):
        self.assertEqual(normalize_weekly(payload(0), "s", 1).remaining_percent, 100)
        self.assertEqual(normalize_weekly(payload(100), "s", 1).remaining_percent, 0)

    def test_missing_week_is_not_replaced_by_five_hour(self):
        view = normalize_weekly(payload(include_week=False, five_hour_used=100), "s", 1)
        self.assertEqual(view.state, "unavailable")
        self.assertIsNone(view.remaining_percent)

    def test_invalid_week_is_not_one_hundred(self):
        for value in (None, float("nan"), -1, 101, "bad"):
            view = normalize_weekly(payload(value), "s", 1)
            self.assertEqual(view.state, "invalid")
            self.assertIsNone(view.remaining_percent)

    def test_model_specific_bucket_is_ignored(self):
        raw = {
            "rateLimitsByLimitId": {
                "codex_other": {
                    "limitId": "codex_other",
                    "primary": {"usedPercent": 99, "windowDurationMins": 10080, "resetsAt": 2},
                }
            }
        }
        self.assertEqual(normalize_weekly(raw, "s", 1).state, "unavailable")


if __name__ == "__main__":
    unittest.main()

