import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "workflow"))
import bbwf  # noqa: E402

SECRET = "lpe85cbcnV1e30c"


def run(argv):
    buf = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        bbwf.main(argv)
    return buf.getvalue()


class TestCredsCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = self._tmp.name
        run(["--base", self.base, "init", "--name", "t", "--in", "my.sweez.ch"])

    def argv(self, *rest):
        return ["--base", self.base, "creds", rest[0], "--name", "t", *rest[1:]]

    def add_s1(self):
        return run(self.argv("add", "--id", "s1", "--host", "my.sweez.ch",
                             "--user", "colt@example.com", "--secret", SECRET))

    def test_add_in_scope_then_list_masks_secret(self):
        out_add = self.add_s1()
        self.assertNotIn(SECRET, out_add)
        out = run(self.argv("list"))
        self.assertIn("lpe****(len=15)", out)
        self.assertNotIn(SECRET, out)
        self.assertIn("s1", out)

    def test_add_out_of_scope_host_refused(self):
        with self.assertRaises(SystemExit) as e:
            run(self.argv("add", "--id", "bad", "--host", "evil.com",
                          "--user", "u", "--secret", "x"))
        self.assertEqual(e.exception.code, 2)
        self.assertNotIn("bad", run(self.argv("list")))

    def test_add_duplicate_id_exits_2(self):
        self.add_s1()
        with self.assertRaises(SystemExit) as e:
            self.add_s1()
        self.assertEqual(e.exception.code, 2)

    def test_get_secret_prints_cleartext_only(self):
        self.add_s1()
        out = run(self.argv("get", "s1", "--field", "secret"))
        self.assertEqual(out.strip(), SECRET)

    def test_get_default_field_is_secret(self):
        self.add_s1()
        self.assertEqual(run(self.argv("get", "s1")).strip(), SECRET)

    def test_get_user_field(self):
        self.add_s1()
        self.assertEqual(run(self.argv("get", "s1", "--field", "user")).strip(),
                         "colt@example.com")

    def test_get_unknown_id_exits_2_no_traceback(self):
        with self.assertRaises(SystemExit) as e:
            run(self.argv("get", "nope"))
        self.assertEqual(e.exception.code, 2)

    def test_secret_stdin_round_trip(self):
        with mock.patch("sys.stdin", io.StringIO("topsecret\n")):
            run(self.argv("add", "--id", "s2", "--host", "my.sweez.ch",
                          "--user", "u", "--secret-stdin"))
        self.assertEqual(run(self.argv("get", "s2", "--field", "secret")).strip(),
                         "topsecret")

    def test_rm(self):
        self.add_s1()
        self.assertIn("removed", run(self.argv("rm", "s1")))
        self.assertIn("no such id", run(self.argv("rm", "s1")))


if __name__ == "__main__":
    unittest.main()
