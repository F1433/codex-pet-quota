import unittest

from codex_pet_quota.app_server import AppServerClient, AppServerError


class AppServerSafetyTests(unittest.TestCase):
    def test_generation_methods_are_rejected_before_send(self):
        client = AppServerClient(executable="unused")
        with self.assertRaises(AppServerError):
            client._request("turn/start", {})


if __name__ == "__main__":
    unittest.main()

