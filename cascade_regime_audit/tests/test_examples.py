"""Smoke tests: every worked example must still run. stdlib unittest only.

CONTRIBUTING asks each new example to come with a test. This is that test for
the examples already here: it runs each one as `__main__`, exactly as the README
tells a reader to, and fails if the example raises. Adding an example means
adding its module name below -- nothing else.

Run:  python -m unittest cascade_regime_audit.tests.test_examples
"""

import io
import contextlib
import runpy
import unittest

EXAMPLES = ("model_collapse", "institutional_fragility")


class TestExamplesRun(unittest.TestCase):
    def test_every_example_runs_clean(self):
        for name in EXAMPLES:
            with self.subTest(example=name):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    runpy.run_module(
                        f"cascade_regime_audit.examples.{name}",
                        run_name="__main__",
                    )
                self.assertTrue(buf.getvalue().strip(),
                                f"{name} produced no output")


if __name__ == "__main__":
    unittest.main()
