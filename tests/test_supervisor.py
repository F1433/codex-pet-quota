import unittest
from types import SimpleNamespace
from unittest.mock import patch

from codex_pet_quota.supervisor import background_launch, codex_desktop_present


class SupervisorDetectionTests(unittest.TestCase):
    def test_frozen_build_relaunches_same_executable(self):
        command, working_directory = background_launch(
            r"F:\Tools\CodexPetQuota.exe", frozen=True
        )
        self.assertEqual(command, [r"F:\Tools\CodexPetQuota.exe", "--background"])
        self.assertEqual(str(working_directory), r"F:\Tools")

    @patch("codex_pet_quota.supervisor.enumerate_codex_windows")
    def test_detects_packaged_desktop_process(self, windows):
        windows.return_value = [SimpleNamespace(image_name="ChatGPT.exe")]
        self.assertTrue(codex_desktop_present())

    @patch("codex_pet_quota.supervisor.enumerate_codex_windows")
    def test_ignores_codex_helpers(self, windows):
        windows.return_value = [
            SimpleNamespace(image_name="codex-computer-use-swift.exe"),
            SimpleNamespace(image_name="pythonw.exe"),
        ]
        self.assertFalse(codex_desktop_present())


if __name__ == "__main__":
    unittest.main()
