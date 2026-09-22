import unittest

from codex_pet_quota.pet_locator import classify_pet_pixels, parse_official_pet_state


class PetPixelClassifierTests(unittest.TestCase):
    def test_current_pet_palette_matches(self):
        pixels = (
            [(245, 245, 245)] * 7500
            + [(105, 60, 40)] * 1200
            + [(35, 65, 135)] * 300
            + [(170, 170, 170)] * 1000
        )
        matched, metrics = classify_pet_pixels(pixels)
        self.assertTrue(matched)
        self.assertGreaterEqual(metrics["score"], 8)

    def test_pet_on_dark_purple_background_matches(self):
        pixels = (
            [(245, 245, 245)] * 3000
            + [(105, 60, 40)] * 1200
            + [(35, 65, 135)] * 150
            + [(28, 20, 60)] * 5650
        )
        matched, metrics = classify_pet_pixels(pixels)
        self.assertTrue(matched)
        self.assertGreaterEqual(metrics["score"], 8)

    def test_right_click_white_menu_does_not_match(self):
        pixels = (
            [(245, 245, 245)] * 8500
            + [(105, 60, 40)] * 200
            + [(35, 65, 135)] * 300
            + [(170, 170, 170)] * 1000
        )
        matched, metrics = classify_pet_pixels(pixels)
        self.assertFalse(matched)
        self.assertLess(metrics["score"], 8)

    def test_plain_toolbar_does_not_match(self):
        matched, metrics = classify_pet_pixels([(245, 245, 245)] * 10000)
        self.assertFalse(matched)
        self.assertLess(metrics["score"], 8)


class OfficialPetStateTests(unittest.TestCase):
    def test_current_overlay_state_uses_official_origin(self):
        target = parse_official_pet_state(
            {
                "electron-avatar-overlay-open": True,
                "electron-avatar-overlay-bounds": {"x": 100, "y": 200},
            },
            scale=1.25,
        )
        self.assertIsNotNone(target)
        self.assertEqual(target.rect, (125, 250, 262, 388))
        self.assertEqual(target.confidence, "official-state-overlay")

    def test_legacy_nested_mascot_state(self):
        target = parse_official_pet_state(
            {
                "electron-persisted-atom-state": {
                    "electron-avatar-overlay-open": True,
                    "electron-avatar-overlay-bounds": {
                        "x": 10,
                        "y": 20,
                        "mascot": {"left": 4, "top": 5, "width": 80, "height": 90},
                    },
                }
            }
        )
        self.assertEqual(target.rect, (14, 25, 94, 115))
        self.assertEqual(target.confidence, "official-state-mascot")

    def test_closed_pet_has_no_target(self):
        target = parse_official_pet_state(
            {
                "electron-avatar-overlay-open": False,
                "electron-avatar-overlay-bounds": {"x": 100, "y": 200},
            }
        )
        self.assertIsNone(target)
