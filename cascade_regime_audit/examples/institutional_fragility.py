"""institutional_fragility.py -- instantiate the cascade audit for an institution.

An institution (team, agency, market) approaching a fragility cascade shows the
same six signatures. The control parameter h_eff here is a consolidation ratio:
how much of decision-making has concentrated into a single apex channel. Past the
spinodal, the distributed-authority well is gone -- dissent no longer changes
outcomes -- and the institution cannot self-correct without external forcing.

Run:  python -m cascade_regime_audit.examples.institutional_fragility
"""

from __future__ import annotations

from ..cascade_audit import CascadeAudit, SignalReads


def read_signals(survey) -> SignalReads:
    return SignalReads(
        # decisions take longer to reverse after a shock (committees loop)
        critical_slowing_down=survey["reversal_lag"],
        # budget / staffing swings grow more erratic
        variance_inflation=survey["volatility"],
        # narratives lean toward the preferred official story
        skew_to_alt_well=survey["narrative_skew"],
        # policy flip-flops between two stances
        flickering=survey["policy_flicker"],
        # criticism is met with MORE unified messaging, not reflection
        coherence_under_contradiction=survey["messaging_lockstep_under_criticism"],
        # independent voices / redundant teams get merged away
        diversity_collapse=survey["consolidation_of_voice"],
    )


def main():
    audit = CascadeAudit(fire_threshold=0.6, pressure_threshold=0.5)

    healthy = read_signals({
        "reversal_lag": 0.3, "volatility": 0.35, "narrative_skew": 0.4,
        "policy_flicker": 0.2, "messaging_lockstep_under_criticism": 0.3,
        "consolidation_of_voice": 0.35,
    })
    r1 = audit.audit(healthy, h_eff=0.2)
    print("healthy   :", r1.regime.value, "| pressure", round(r1.pressure, 2))

    stressed = read_signals({
        "reversal_lag": 0.7, "volatility": 0.65, "narrative_skew": 0.7,
        "policy_flicker": 0.6, "messaging_lockstep_under_criticism": 0.85,
        "consolidation_of_voice": 0.6,
    })
    r2 = audit.audit(stressed, h_eff=0.3)  # high pressure, still below spinodal
    print("stressed  :", r2.regime.value, "| pressure", round(r2.pressure, 2),
          "| margin", round(r2.distance_to_spinodal, 3))
    print("            ", r2.note)

    captured = audit.audit(stressed, h_eff=0.5)  # same signals, past the spinodal
    print("captured  :", captured.regime.value, "| over_spinodal",
          captured.over_spinodal)
    print("            ", captured.note)


if __name__ == "__main__":
    main()
