"""Unit tests for the trace core. stdlib unittest only.

Run:  python -m unittest runner_up_trace.tests.test_runner_up_trace
"""

import math
import os
import tempfile
import unittest

from runner_up_trace import (
    D_MAX, D_SWEEP, PARAMS, SEPARATION_FIELDS, BaseRow, Distribution,
    check_contract, entropy_from_topk, entropy_of, normalized_edit_distance,
    permute, report, resync, run_base_pass, score, selection_sets,
    separation_set, sustained_set, top_entropy_positions, topk_sensitivity,
    trace_positions, union_positions, write_separations,
)
from runner_up_trace.examples.synthetic_model import SyntheticModel


class TestEntropy(unittest.TestCase):
    def test_uniform_topk_entropy_is_log_k(self):
        k = 8
        top = [(t, math.log(1.0 / k)) for t in range(k)]
        self.assertAlmostEqual(entropy_from_topk(top), math.log(k), places=9)

    def test_peaked_entropy_is_zero(self):
        self.assertAlmostEqual(entropy_from_topk([(0, 0.0), (1, -50.0)]), 0.0, places=6)

    def test_renormalises_truncated_logprobs(self):
        # top-k that sums to 0.5 of the mass: entropy over the renormalised k
        top = [(0, math.log(0.25)), (1, math.log(0.25))]
        self.assertAlmostEqual(entropy_from_topk(top), math.log(2), places=9)

    def test_kind_is_declared(self):
        d_full = Distribution(top_k=[(0, 0.0)], full_entropy=0.3)
        d_topk = Distribution(top_k=[(0, 0.0)])
        self.assertEqual(entropy_of(d_full), (0.3, "full"))
        self.assertEqual(entropy_of(d_topk)[1], "topk")


class TestSeparationMath(unittest.TestCase):
    def test_edit_distance_identity_and_disjoint(self):
        self.assertEqual(normalized_edit_distance([1, 2, 3], [1, 2, 3]), 0.0)
        self.assertEqual(normalized_edit_distance([1, 2, 3], [4, 5, 6]), 1.0)
        self.assertEqual(normalized_edit_distance([], []), 0.0)

    def test_resync_requires_min_match_run_at_tail(self):
        base = [10, 11, 12, 13, 14, 15, 16, 17]
        self.assertEqual(resync([9, 9, 14, 15, 16, 17], base), 1)      # tail rejoined
        self.assertEqual(resync([14, 15, 16, 17, 9, 9], base), 0)      # rejoined then left
        self.assertEqual(resync([9, 9, 9, 16, 17], base), 0)           # run too short
        self.assertEqual(resync([1, 2], base), 0)                      # shorter than min


class TestContract(unittest.TestCase):
    def _row(self, **extra):
        r = {"case_id": "c", "model_id": "m", "i": 0, "branch_rank": 2, "D": 8,
             "ent_i": 1.0, "gap_i": 0.5, "resync_D": 0, "div_D": 0.7}
        r.update(extra)
        return r

    def test_exact_fields_pass(self):
        check_contract([self._row()])

    def test_label_field_refused(self):
        with self.assertRaises(ValueError):
            check_contract([self._row(label="frame-boundary")])
        with self.assertRaises(ValueError):
            check_contract([self._row(category="x")])

    def test_missing_field_refused(self):
        r = self._row()
        del r["div_D"]
        with self.assertRaises(ValueError):
            check_contract([r])

    def test_writer_enforces(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.jsonl")
            with self.assertRaises(ValueError):
                write_separations(path, [self._row(frame="x")])
            self.assertEqual(write_separations(path, [self._row()]), 1)

    def test_field_tuple_has_no_label(self):
        for banned in ("label", "category", "type", "frame"):
            self.assertNotIn(banned, SEPARATION_FIELDS)


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.model = SyntheticModel(seed=3)
        self.prompt = self.model.tokenize("abc")
        self.base = run_base_pass(self.model, self.prompt, max_tokens=40)

    def test_base_pass_is_greedy_and_full_entropy(self):
        for r in self.base:
            self.assertEqual(r.token_taken, r.top_k[0][0])
            self.assertEqual(r.entropy_kind, "full")
            self.assertEqual(r.k, 20)

    def test_truncated_adapter_declares_topk(self):
        m = SyntheticModel(seed=3, truncated=True)
        rows = run_base_pass(m, self.prompt, max_tokens=5)
        self.assertTrue(all(r.entropy_kind == "topk" for r in rows))

    def test_selection_is_declared_rule(self):
        top = top_entropy_positions(self.base, 5)
        ents = sorted((r.entropy_i for r in self.base), reverse=True)[:5]
        self.assertEqual(sorted(self.base[i].entropy_i for i in top), sorted(ents))
        sets = selection_sets(self.base, random_seed=0)
        self.assertEqual({s["rule"] for s in sets}, {"top_entropy", "random"})
        self.assertEqual({s["N"] for s in sets}, {10, 25, 50})
        self.assertTrue(union_positions(sets))

    def test_trace_forces_runner_up_and_records_full_length(self):
        traces = trace_positions(self.model, self.prompt, self.base, [0, 3], d_max=D_MAX)
        self.assertEqual(len(traces), 4)  # 2 positions x ranks (2, 3)
        for t in traces:
            self.assertEqual(t.continuation[0], t.forced_token)
            self.assertEqual(t.forced_token, self.base[t.i].runner_up(t.branch_rank)[0])
            self.assertNotEqual(t.forced_token, self.base[t.i].token_taken)
            self.assertEqual(len(t.continuation), D_MAX)

    def test_score_rows_are_one_per_i_branch_D_and_gap_is_positive(self):
        traces = trace_positions(self.model, self.prompt, self.base, [1, 2])
        rows = score(self.base, traces, "case", self.model.model_id)
        self.assertEqual(len(rows), 2 * 2 * len(D_SWEEP))
        check_contract(rows)
        for r in rows:
            self.assertGreaterEqual(r["gap_i"], 0.0)  # greedy token beats runner-up
            self.assertIn(r["resync_D"], (0, 1))
            self.assertTrue(0.0 <= r["div_D"] <= 1.0)
            self.assertEqual(r["ent_i"], self.base[r["i"]].entropy_i)


class TestPermuteAndClaims(unittest.TestCase):
    def setUp(self):
        model = SyntheticModel(seed=5)
        prompt = model.tokenize("permute")
        self.base = run_base_pass(model, prompt, max_tokens=60)
        self.sel = selection_sets(self.base, random_seed=5)
        traces = trace_positions(model, prompt, self.base, union_positions(self.sel))
        self.rows = score(self.base, traces, "c1", model.model_id)
        self.model_id = model.model_id

    def test_row_permutation_preserves_marginals_per_stratum(self):
        perm = permute(self.rows, seed=1, mode="row")
        self.assertEqual(len(perm), len(self.rows))
        check_contract(perm)
        def marg(rows):
            return sorted((r["D"], r["branch_rank"], r["resync_D"], round(r["div_D"], 6),
                           round(r["ent_i"], 6)) for r in rows)
        self.assertEqual(marg(perm), marg(self.rows))
        # position identity is kept; the tuple moved
        self.assertEqual(sorted(r["i"] for r in perm), sorted(r["i"] for r in self.rows))

    def test_position_permutation_is_a_relabelling(self):
        perm = permute(self.rows, seed=2, mode="position")
        self.assertEqual(sorted(r["i"] for r in perm), sorted(r["i"] for r in self.rows))
        # a position-blind summary is unchanged by it
        self.assertEqual(len(sustained_set(perm)), len(sustained_set(self.rows)))

    def test_permutation_is_seeded(self):
        self.assertEqual(permute(self.rows, 9), permute(self.rows, 9))

    def test_report_carries_params_and_all_claims_and_nulls(self):
        perm = permute(self.rows, seed=1)
        rep = report(self.rows, perm, self.sel, "c1", self.model_id)
        self.assertEqual(rep["params"], PARAMS)
        self.assertEqual([c["claim"] for c in rep["claims"]], ["RU-1", "RU-2", "RU-3", "RU-4", "RU-5"])
        self.assertEqual([n["null"] for n in rep["nulls"]], ["N1", "N2", "N3", "N4", "N5"])
        for c in rep["claims"]:
            self.assertIn(c["status"], ("held", "refuted", "not_evaluable"))
        self.assertIsNotNone(rep["summary_permuted"])
        self.assertEqual(rep["claims"][3]["status"], "not_evaluable")  # RU-4 needs 2 models

    def test_ru4_evaluates_with_two_models_same_case(self):
        rows2 = [dict(r, model_id="other") for r in self.rows]
        rep = report(self.rows + rows2, None, None)
        self.assertIn(rep["claims"][3]["status"], ("held", "refuted"))
        self.assertEqual(rep["claims"][3]["evidence"]["pairs"][0]["common"],
                         len({r["i"] for r in self.rows}))

    def test_separation_set_respects_declared_thresholds(self):
        strict = dict(PARAMS, div_min=1.01)
        self.assertEqual(separation_set(self.rows, 8, strict), set())

    def test_topk_sensitivity_identical_passes_is_one(self):
        self.assertEqual(set(topk_sensitivity(self.base, self.base).values()), {1.0})


if __name__ == "__main__":
    unittest.main()
