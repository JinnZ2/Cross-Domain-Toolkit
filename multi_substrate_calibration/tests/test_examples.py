"""Smoke tests: every worked example must still run. stdlib unittest only.

CONTRIBUTING asks each new example to come with a test. This is that test for
the examples already here: it runs each one as `__main__`, exactly as the README
tells a reader to, and fails if the example raises. Adding an example means
adding its module name below -- nothing else.

Run:  python -m unittest multi_substrate_calibration.tests.test_examples
"""

import io
import contextlib
import runpy
import unittest
import warnings

EXAMPLES = ("thermal_substrate", "acoustic_substrate")


class TestExamplesRun(unittest.TestCase):
    def test_every_example_runs_clean(self):
        for name in EXAMPLES:
            with self.subTest(example=name):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), warnings.catch_warnings():
                    # A test module that imported the example already put it in
                    # sys.modules; runpy warns about re-executing it, which is
                    # exactly what a smoke test means to do.
                    warnings.simplefilter("ignore", RuntimeWarning)
                    runpy.run_module(
                        f"multi_substrate_calibration.examples.{name}",
                        run_name="__main__",
                    )
                self.assertTrue(buf.getvalue().strip(),
                                f"{name} produced no output")


if __name__ == "__main__":
    unittest.main()
