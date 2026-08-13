"""domain_atlas.py -- six fields, six claims, one protocol.

Run:  python -m falsification_ledger.examples.domain_atlas

The other examples each fork the ledger for one domain and follow it in depth.
This one runs six at once, to make a narrower point: the protocol does not know
what field it is in. Each domain below brings a standard estimator, a claim
stated in that estimator's own parameters, an up-front `refutation_set` naming
what would sink it, and a `logical_form` the symbolic checker can test
independently of the numeric tolerance.

The estimators are the ones their fields actually use -- Aki's b-value MLE, the
SIR relation between early growth and R0, the debt-stabilising primary balance,
a Chinchilla-form scaling law, error-budget burn rate, Maas-Hoffman salinity
tolerance. What varies across the six is everything except the discipline.

Each domain is driven with synthetic observations and carries a prepared update
in case it needs one. Four of the six are refuted: the claim is superseded on the
record with a rationale citing the entry that sank it, and the chain still
verifies. Two survive -- and the prepared update is *refused*, because the
protocol will not let a claim be revised to fit an observation it already
predicted. That refusal is the rule the whole package exists to mechanise, so it
is worth watching it fire on a claim that merely happened to be right.
"""

from __future__ import annotations

from ..ledger import Claim, Ledger, RefutationError


# --- 1. seismology ----------------------------------------------------------

def b_value_kernel(params, condition):
    """Gutenberg-Richter: expected count above magnitude M in a catalogue.

    log10 N = a - b*M. Aki's MLE for b from a magnitude sample is
    b = 1/(ln10 * (mean_magnitude - M_completeness)); here the claim carries a
    and b, and predicts the count at a magnitude.
    """
    return 10.0 ** (params["a"] - params["b"] * condition)


SEISMOLOGY = (
    b_value_kernel,
    Claim(
        statement="regional catalogue follows Gutenberg-Richter with b = 1.0",
        params={"a": 4.5, "b": 1.0},
        refutation_set=[
            "observed count at M5 differs from prediction by more than tolerance",
            "fitted b outside [0.7, 1.3] over a complete catalogue",
            "log10 N vs M is not linear above M_c",
        ],
        scope={"temporal": "2020-2026 catalogue", "spatial": "one subduction segment",
               "ontological": "events above completeness magnitude M_c = 3.0"},
        reference_class="shallow crustal earthquakes above M_c in the segment",
        logical_form="b > 0 and predicted > 0",
    ),
    [(5.0, 12.0, 3.0), (4.0, 90.0, 20.0)],   # (magnitude, observed N, tolerance)
    # b = log10(N4/N5) = log10(90/12) = 0.88; a = log10(90) + 0.88*4 = 5.45.
    # Both observations refit the catalogue, rather than nudging one parameter
    # until the last residual goes quiet.
    {"a": 5.45, "b": 0.88},
    "entries 0-1: both counts far above a (a=4.5, b=1.0) catalogue; "
    "refit on the pair gives b = 0.88, a = 5.45",
)


# --- 2. epidemiology --------------------------------------------------------

def r0_kernel(params, condition):
    """SIR early phase: exponential growth rate from R0 and recovery rate.

    Lambda = gamma * (R0 - 1). Given a serial-interval-derived gamma, the claim's
    R0 predicts the growth rate observed in early case counts.
    """
    return params["gamma"] * (params["R0"] - 1.0) * condition


EPIDEMIOLOGY = (
    r0_kernel,
    Claim(
        statement="outbreak has R0 = 2.5 with a 5-day infectious period",
        params={"R0": 2.5, "gamma": 0.2},
        refutation_set=[
            "early exponential growth rate outside tolerance of gamma*(R0-1)",
            "doubling time inconsistent with R0 for two consecutive weeks",
            "attack rate exceeds the 1 - 1/R0 herd-immunity bound",
        ],
        scope={"temporal": "first 6 weeks, before intervention",
               "spatial": "single metropolitan area",
               "ontological": "laboratory-confirmed cases"},
        reference_class="confirmed cases in the metro area pre-intervention",
        logical_form="R0 > 1 and gamma > 0",
    ),
    [(1.0, 0.42, 0.05), (2.0, 0.80, 0.10)],
    {"R0": 3.1, "gamma": 0.2},
    "entry 0: growth rate 0.42/day implies R0 near 3.1, not 2.5",
)


# --- 3. sovereign debt ------------------------------------------------------

def debt_stabilising_balance(params, condition):
    """Primary balance that holds the debt ratio flat.

    s* = ((r - g) / (1 + g)) * b, with r the effective nominal rate, g nominal
    growth, and b (the condition) the debt-to-GDP ratio. Positive means a
    surplus is required.
    """
    r, g = params["r"], params["g"]
    return ((r - g) / (1.0 + g)) * condition


SOVEREIGN_DEBT = (
    debt_stabilising_balance,
    Claim(
        statement="debt stabilises at r = 4.0%, g = 3.5% nominal",
        params={"r": 0.040, "g": 0.035},
        refutation_set=[
            "realised primary balance needed differs from s* beyond tolerance",
            "r - g turns negative for four consecutive quarters",
            "debt ratio rises while the primary balance meets s*",
        ],
        scope={"temporal": "fiscal years 2026-2030",
               "spatial": "one sovereign issuer",
               "ontological": "general-government gross debt"},
        reference_class="general-government debt of the issuer, nominal terms",
        logical_form="predicted == ((r - g) / (1 + g)) * x",
    ),
    [(1.20, 0.0135, 0.002), (0.90, 0.0101, 0.002)],
    {"r": 0.052, "g": 0.035},
    "entry 0: stabilising balance far above claim; effective rate revised to 5.2%",
)


# --- 4. ML scaling laws -----------------------------------------------------

def scaling_law_kernel(params, condition):
    """Chinchilla-form loss curve: L(N) = E + A / N^alpha, N in parameters."""
    return params["E"] + params["A"] / (condition ** params["alpha"])


SCALING_LAW = (
    scaling_law_kernel,
    Claim(
        statement="loss follows L(N) = E + A/N^alpha with alpha = 0.34",
        params={"E": 1.69, "A": 406.4, "alpha": 0.34},
        refutation_set=[
            "held-out loss at a new scale outside tolerance of the fit",
            "fitted alpha outside [0.28, 0.40] on a refit",
            "loss falls below the irreducible term E",
        ],
        scope={"temporal": "a single pretraining sweep",
               "spatial": "one model family and tokenizer",
               "ontological": "held-out cross-entropy in nats/token"},
        reference_class="dense decoder-only models, 10M-10B params, fixed data mix",
        logical_form="alpha > 0 and E > 0 and predicted > E",
    ),
    [(1.0e9, 2.05, 0.03), (4.0e9, 1.93, 0.03)],
    {"E": 1.69, "A": 406.4, "alpha": 0.29},
    "entry 0: loss at 1B above the curve; alpha refit shallower",
)


# --- 5. site reliability ----------------------------------------------------

def burn_rate_kernel(params, condition):
    """Error-budget burn rate: observed error rate over the budgeted rate.

    Budget = 1 - SLO. A burn rate of 1.0 spends the window's budget exactly on
    time; 14.4 exhausts a 30-day budget in about two days.
    """
    budget = 1.0 - params["slo"]
    return condition / budget if budget > 0 else float("inf")


RELIABILITY = (
    burn_rate_kernel,
    Claim(
        statement="service holds a 99.9% availability SLO",
        params={"slo": 0.999},
        refutation_set=[
            "measured burn rate differs from the claim beyond tolerance",
            "budget exhausted before the 30-day window closes",
            "two consecutive windows with burn rate above 2",
        ],
        scope={"temporal": "rolling 30-day windows",
               "spatial": "the public API tier",
               "ontological": "HTTP 5xx over total requests"},
        reference_class="externally-originated requests to the public API tier",
        logical_form="slo > 0 and slo < 1 and predicted >= 0",
    ),
    [(0.004, 4.0, 0.5), (0.0025, 2.5, 0.5)],
    {"slo": 0.995},
    "entry 0: burn rate consistent with a 99.5% service, not 99.9%",
)


# --- 6. soil salinity -------------------------------------------------------

def maas_hoffman_kernel(params, condition):
    """Maas-Hoffman crop salt tolerance: relative yield against soil salinity.

    Y = 100 - b*(EC_e - a) for EC_e > a, flat at 100 below the threshold a.
    `a` is the crop's salinity threshold in dS/m and `b` the percent yield lost
    per dS/m beyond it.
    """
    ec = condition
    if ec <= params["a"]:
        return 100.0
    return max(0.0, 100.0 - params["b"] * (ec - params["a"]))


SALINITY = (
    maas_hoffman_kernel,
    Claim(
        statement="this cultivar matches published maize tolerance (a=1.7, b=12)",
        params={"a": 1.7, "b": 12.0},
        refutation_set=[
            "relative yield at a measured EC_e outside tolerance",
            "yield loss detected below the claimed threshold a",
            "response to salinity is not linear above the threshold",
        ],
        scope={"temporal": "one growing season",
               "spatial": "three irrigated plots, same soil series",
               "ontological": "relative yield vs saturated-paste EC_e"},
        reference_class="this maize cultivar under furrow irrigation on the series",
        logical_form="a > 0 and b > 0 and predicted <= 100",
    ),
    [(4.0, 62.0, 5.0), (3.0, 78.0, 5.0)],
    {"a": 1.7, "b": 16.5},
    "entry 0: yield at EC_e 4.0 well below the published curve; b steepened",
)


ATLAS = (
    ("seismology", "b-value", SEISMOLOGY),
    ("epidemiology", "R0", EPIDEMIOLOGY),
    ("sovereign debt", "r - g", SOVEREIGN_DEBT),
    ("ML scaling", "alpha", SCALING_LAW),
    ("reliability", "SLO", RELIABILITY),
    ("soil salinity", "Maas-Hoffman b", SALINITY),
)


def run_domain(kernel, claim, observations, new_params, rationale):
    """Open a strict ledger, meet reality, and try the prepared update.

    The update is attempted either way. Where reality refuted the claim it is
    applied; where the claim held, `refute()` raises and the prepared params are
    dropped on the floor -- which is the point. Returns the ledger, its entries,
    and whether the update was allowed through.
    """
    led = Ledger(kernel, claim, strict_falsifiable=True, strict_scope=True,
                 strict_symbolic=True)
    entries = [led.record(condition=c, observed=o, tolerance=t, source="synthetic")
               for c, o, t in observations]
    try:
        led.refute(new_params, rationale=rationale)
        return led, entries, True
    except RefutationError:
        # The claim survived its test. Wanting to update it is not a licence to.
        return led, entries, False


def main() -> None:
    print("Six fields, one protocol. Every ledger below opens in strict mode:")
    print("unfalsifiable, under-scoped, or unformalised claims cannot even be"
          " entered.\n")
    print(f"{'domain':<16}{'parameter':<16}{'v1 residual':>13}{'update':>10}"
          f"{'->v':>5}{'logic':>7}{'chain':>7}")
    print("-" * 74)

    updated = 0
    for name, parameter, (kernel, claim, obs, new_params, why) in ATLAS:
        led, entries, allowed = run_domain(kernel, claim, obs, new_params, why)
        updated += allowed
        logic = "ok" if all(e.logical_ok for e in entries) else "VIOLATED"
        print(f"{name:<16}{parameter:<16}{entries[0].mismatch.residual:>13.4g}"
              f"{('applied' if allowed else 'REFUSED'):>10}{led.claim.version:>5}"
              f"{logic:>7}{str(led.verify()):>7}")

    print(f"\n{updated} claims were refuted and superseded on the record; "
          f"{len(ATLAS) - updated} held,")
    print("and for those the prepared parameter update was refused -- a claim that")
    print("survived its test may not be retuned. The parameters moved where reality")
    print("said so, and the kernels never moved at all.")

    # The audit certificate: what a third party checks without the ledger.
    led, _, _ = run_domain(*SEISMOLOGY)
    cert = led.audit_certificate(0)
    print(f"\naudit certificate for the seismology ledger's entry 0:"
          f"\n  root  {cert['root'][:32]}...\n  proof {len(cert['proof'])} sibling"
          f" hash(es) for {cert['entry_count']} entries")


if __name__ == "__main__":
    main()
