"""Smoke tests: every worked example must still run. stdlib unittest only.

Run:  python -m unittest runner_up_trace.tests.test_examples
"""

import contextlib
import io
import runpy
import unittest
import warnings

EXAMPLES = ("synthetic_model", "end_to_end", "http_adapter")


class TestExamplesRun(unittest.TestCase):
    def test_every_example_runs_clean(self):
        for name in EXAMPLES:
            with self.subTest(example=name):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    runpy.run_module(f"runner_up_trace.examples.{name}", run_name="__main__")
                self.assertTrue(buf.getvalue().strip(), f"{name} produced no output")


if __name__ == "__main__":
    unittest.main()
