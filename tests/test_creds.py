import os
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "workflow"))
import creds  # noqa: E402


class TestMaskSecret(unittest.TestCase):
    def test_mask_hides_all_but_first_three(self):
        self.assertEqual(creds.mask_secret("lpe85cbcnV1e30c"), "lpe****(len=15)")

    def test_mask_short_secret_fully_hidden(self):
        self.assertEqual(creds.mask_secret("ab"), "****")
        self.assertEqual(creds.mask_secret(""), "****")
        self.assertEqual(creds.mask_secret("abc"), "****")


class TestCredStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "creds.json")
        self.store = creds.CredStore(self.path)

    def test_add_then_get_roundtrip(self):
        self.store.add({"id": "sweez-1", "host": "my.sweez.ch",
                        "username": "colt@example.com", "secret": "x"})
        acct = self.store.get("sweez-1")
        self.assertEqual(acct["username"], "colt@example.com")
        self.assertEqual(acct["label"], "")
        self.assertEqual(acct["note"], "")
        self.assertIs(acct["manual_only"], False)

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.store.get("nope"))

    def test_add_missing_required_field_raises(self):
        with self.assertRaises(ValueError):
            self.store.add({"id": "a", "host": "h"})
        with self.assertRaises(ValueError):
            self.store.add({"id": "a", "host": "h", "username": ""})

    def test_add_duplicate_id_raises(self):
        self.store.add({"id": "a", "host": "h", "username": "u"})
        with self.assertRaises(ValueError):
            self.store.add({"id": "a", "host": "h", "username": "u2"})

    def test_saved_file_is_0600(self):
        self.store.add({"id": "a", "host": "h", "username": "u"})
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)

    def test_save_over_preexisting_file_is_still_0600(self):
        # Pre-create a creds.json with looser permissions, then save again
        # through the atomic-replace path and confirm it ends up at 0600.
        with open(self.path, "w") as f:
            f.write("[]")
        os.chmod(self.path, 0o644)
        self.store.add({"id": "a", "host": "h", "username": "u"})
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        # and no leftover temp file
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_reload_persists(self):
        self.store.add({"id": "a", "host": "h", "username": "u", "secret": "s"})
        reloaded = creds.CredStore(self.path)
        self.assertEqual(reloaded.get("a")["secret"], "s")

    def test_remove_and_reload_persists(self):
        self.store.add({"id": "a", "host": "h", "username": "u"})
        self.assertTrue(self.store.remove("a"))
        self.assertFalse(self.store.remove("a"))
        self.assertIsNone(creds.CredStore(self.path).get("a"))


if __name__ == "__main__":
    unittest.main()
