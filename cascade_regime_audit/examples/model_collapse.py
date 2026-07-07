"""model_collapse.py -- instantiate the cascade audit for model collapse.

Model collapse: a generative model trained on its own (or peers') synthetic
output loses tail diversity and drifts toward a degenerate distribution. Map its
observables onto the six generic signals, and use the synthetic-data fraction as
the control parameter h_eff (past the spinodal, the real-data well that anchors
diversity has vanished and further training cannot recover it).

Run:  python -m cascade_regime_audit.examples.model_collapse
"""

from __future__ import annotations

from ..cascade_audit import CascadeAudit, SignalReads


def read_signals(generation_stats) -> SignalReads:
    """Map training-telemetry onto the six signals. `generation_stats` is a dict
    of whatever the training loop already logs."""
    return SignalReads(
        # recovery from a perturbed prompt gets slower as modes merge
        critical_slowing_down=generation_stats["recovery_lag"],
        # per-token logit variance across a batch swings more as tails thin
        variance_inflation=generation_stats["logit_var_ratio"],
        # output distribution leans toward the high-frequency majority mode
        skew_to_alt_well=generation_stats["mode_skew"],
        # generations flicker between a few canned templates
        flickering=generation_stats["template_bimodality"],
        # when fed contradictory context, the model gets MORE confident, not less
        coherence_under_contradiction=generation_stats["confidence_on_contradiction"],
        # effective vocabulary / n-gram diversity collapses
        diversity_collapse=generation_stats["diversity_loss"],
    )


def main():
    audit = CascadeAudit(fire_threshold=0.6, pressure_threshold=0.5)

    # generation 3: stressed but real data still anchors the distribution
    early = read_signals({
        "recovery_lag": 0.55, "logit_var_ratio": 0.6, "mode_skew": 0.5,
        "template_bimodality": 0.4, "confidence_on_contradiction": 0.7,
        "diversity_loss": 0.5,
    })
    r1 = audit.audit(early, h_eff=0.25)  # 25% synthetic, below spinodal
    print("gen 3 :", r1.regime.value, "| pressure", round(r1.pressure, 2),
          "| margin", round(r1.distance_to_spinodal, 3))
    print("        ", r1.note)

    # generation 8: synthetic fraction past the spinodal; diversity well gone
    late = read_signals({
        "recovery_lag": 0.8, "logit_var_ratio": 0.85, "mode_skew": 0.8,
        "template_bimodality": 0.75, "confidence_on_contradiction": 0.9,
        "diversity_loss": 0.85,
    })
    r2 = audit.audit(late, h_eff=0.45)  # past H_SPINODAL ~= 0.385
    print("gen 8 :", r2.regime.value, "| pressure", round(r2.pressure, 2),
          "| fired", r2.fired)
    print("        ", r2.note)


if __name__ == "__main__":
    main()
