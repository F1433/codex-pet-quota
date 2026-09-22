import os
import tempfile
import unittest
from unittest import mock

from codex_pet_quota.models import AlertDecision, WeeklyQuotaView


@unittest.skipUnless(os.name == "nt", "Windows-only Tk smoke test")
class UiSmokeTests(unittest.TestCase):
    def test_window_builds_and_renders_weekly_value(self):
        from codex_pet_quota import ui

        with tempfile.TemporaryDirectory() as state_dir, mock.patch.dict(
            os.environ, {"CODEX_PET_QUOTA_DATA_DIR": state_dir}
        ), mock.patch.object(ui.QuotaWindow, "_tick", lambda self: None):
            window = ui.QuotaWindow()
            try:
                view = WeeklyQuotaView(
                    state="ready",
                    scope_key="test",
                    source="cli-rpc",
                    fetched_at=1,
                    remaining_percent=18.0,
                    used_percent=82.0,
                    resets_at=2000000000,
                )
                window._render(view, AlertDecision(True, True, "below-threshold"))
                window.root.update_idletasks()
                self.assertEqual(window.quota_text.get(), "周剩余 18%")
                self.assertIn("重置", window.reset_text.get())
                self.assertGreater(window.root.winfo_reqwidth(), 250)
                self.assertEqual(window.last_refresh, 0)
                self.assertFalse(window.fetching)
            finally:
                window.service.close()
                window.root.destroy()
