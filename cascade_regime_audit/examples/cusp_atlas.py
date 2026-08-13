"""cusp_atlas.py -- eight domains whose folds are the same fold.

Run:  python -m cascade_regime_audit.examples.cusp_atlas

The detector ships with a spinodal constant, `H_SPINODAL = 2/sqrt(27)`, and an
abstract control parameter `h_eff`. That pairing is easy to mistake for a
universal physical constant. It is not: `2/sqrt(27)` is the fold of the cusp
catastrophe's *normal form*, the point where the cubic dV/dx = x^3 - a*x - h
stops having three roots. Any system with a saddle-node bifurcation is locally
that cubic under some change of variables -- but the change of variables is the
work, and it is domain-specific.

So this file is the missing half of the instrument. Each domain below owns a
quantity that is already known to be critical at a particular value: Euler's
buckling load, Semenov's ignition criterion, Griffith's fracture toughness, a
fishery's maximum sustainable yield. The mapper turns the domain's own
control-to-critical *ratio* into `h_eff` on the detector's scale, so that

    ratio = control / critical = 1     <->     h_eff = H_SPINODAL

and the detector's structural read means what the domain's own theory says.
Every constant below belongs to its field's standard treatment; none was
invented here. That is what makes these calibrations rather than analogies.

WHAT THIS DOES NOT CLAIM. Mapping the ratio linearly onto `h_eff` preserves the
one point that matters -- the fold -- but not the shape of the approach to it.
Two domains at ratio 0.5 are both "half way" only in the sense their own theory
means. Where a domain has a better-characterised normal form, use it; the linear
map is the honest default when it does not.
"""

from __future__ import annotations

from ..cascade_audit import H_SPINODAL, CascadeAudit, SignalReads


def h_eff_from_ratio(ratio: float) -> float:
    """Put a domain's control/critical ratio on the detector's scale.

    `ratio` is the domain's control parameter over its own critical value, so
    that 1.0 *is* the fold. Returns the equivalent `h_eff`, with 1.0 landing
    exactly on `H_SPINODAL`.
    """
    return max(0.0, ratio) * H_SPINODAL


# --- the eight domains ------------------------------------------------------
# Each returns the control/critical ratio for its domain. Feed the result
# through h_eff_from_ratio() to get the detector's structural parameter.

def buckling_ratio(load: float, youngs_modulus: float, second_moment: float,
                   length: float, end_condition: float = 1.0) -> float:
    """Structural buckling: axial load over the Euler critical load.

    P_cr = pi^2 * E * I / (K*L)^2, with K the effective-length factor (1.0
    pinned-pinned, 0.5 fixed-fixed, 2.0 cantilever). Past P_cr the straight
    configuration stops being a minimum -- the column has no undeflected state
    left to return to, which is the fold in its most tangible form.
    """
    critical = (3.141592653589793 ** 2) * youngs_modulus * second_moment
    critical /= (end_condition * length) ** 2
    return load / critical if critical > 0 else 0.0


def van_der_waals_ratio(reduced_temperature: float) -> float:
    """Van der Waals fluid: how far below the critical isotherm the state sits.

    In reduced units the critical point is (T_r, P_r, V_r) = (1, 1, 1). Above
    T_r = 1 the liquid-gas distinction does not exist; below it the isotherm
    develops the loop whose two turning points are spinodals, and the metastable
    phase can be driven until it vanishes. Returns 0 at and above the critical
    isotherm, rising as T_r falls and the two-phase region opens.
    """
    return max(0.0, 1.0 - reduced_temperature)


def semenov_ratio(heat_release: float, heat_removal_coefficient: float,
                  activation_temperature: float,
                  ambient_temperature: float) -> float:
    """Thermal runaway: the Semenov number against its ignition criterion.

    Semenov's tangency condition -- heat generation curve just touching the
    removal line -- gives the critical value psi_cr = 1/e ~= 0.3679. Past it no
    steady low-temperature state exists and the reaction runs away. `heat_release`
    is the pre-exponential release rate, `heat_removal_coefficient` the h*A
    product; both in consistent units.
    """
    psi_critical = 0.36787944117144233   # 1/e
    if heat_removal_coefficient <= 0 or ambient_temperature <= 0:
        return 0.0
    theta = activation_temperature / ambient_temperature
    if theta <= 0:
        return 0.0
    psi = heat_release / (heat_removal_coefficient * ambient_temperature * theta)
    return psi / psi_critical


def thermohaline_ratio(freshwater_flux: float, critical_flux: float) -> float:
    """Ice-albedo / AMOC shutdown: freshwater forcing over its critical value.

    Stommel's two-box ocean has two stable circulation states; freshwater input
    to the high-latitude box moves the system along a hysteresis loop until the
    overturning branch disappears at a saddle-node. `critical_flux` is the
    domain's own calibrated threshold -- the point of this mapper is that once
    you have it, the detector's structural read is defined.
    """
    return freshwater_flux / critical_flux if critical_flux > 0 else 0.0


def allee_ratio(population: float, allee_threshold: float) -> float:
    """Allee collapse: how far a population has fallen toward its threshold.

    With a strong Allee effect, dN/dt = rN(N/A - 1)(1 - N/K) has an unstable
    equilibrium at N = A below which the population goes to zero however
    favourable conditions become. Returns 1.0 at the threshold and rises as the
    population falls below it -- the ratio is inverted here because the danger
    is in the small direction.
    """
    if population <= 0:
        return 2.0                      # already past any recovery
    return allee_threshold / population


def voltage_stability_ratio(loading: float, max_loading: float) -> float:
    """Power grid: loading against the nose of the P-V curve.

    The nose is a saddle-node bifurcation in the power-flow equations: past
    `max_loading` no voltage solution exists at all, and the collapse is not a
    control failure but the absence of an operating point to control toward.
    """
    return loading / max_loading if max_loading > 0 else 0.0


def fracture_ratio(stress_intensity: float, fracture_toughness: float) -> float:
    """Griffith fracture: K_I against K_IC.

    Griffith's energy balance makes crack growth spontaneous once the released
    strain energy exceeds the surface energy cost -- sigma_c = sqrt(2*E*gamma /
    (pi*a)). Past K_IC the arrested-crack state does not exist; propagation is
    the only branch left.
    """
    return stress_intensity / fracture_toughness if fracture_toughness > 0 else 0.0


def fishery_ratio(harvest: float, intrinsic_growth: float,
                  carrying_capacity: float) -> float:
    """Fisheries: harvest against maximum sustainable yield.

    Logistic stock under constant-quota harvest, dN/dt = rN(1 - N/K) - H, folds
    at H = rK/4: the stable and unstable equilibria collide and the stock has
    nowhere to sit. MSY is famous as a *target*, and this is why targeting it
    exactly is targeting a bifurcation point.
    """
    msy = intrinsic_growth * carrying_capacity / 4.0
    return harvest / msy if msy > 0 else 0.0


DOMAINS = (
    ("structural buckling", "load / Euler P_cr",
     buckling_ratio(load=1.9e5, youngs_modulus=2.0e11, second_moment=8.3e-6,
                    length=6.0, end_condition=1.0)),
    ("van der Waals fluid", "1 - T_r", van_der_waals_ratio(reduced_temperature=0.62)),
    ("thermal runaway", "Semenov psi / (1/e)",
     semenov_ratio(heat_release=1.4e5, heat_removal_coefficient=42.0,
                   activation_temperature=9500.0, ambient_temperature=310.0)),
    ("AMOC shutdown", "freshwater flux / critical",
     thermohaline_ratio(freshwater_flux=0.29, critical_flux=0.35)),
    ("Allee collapse", "threshold / population",
     allee_ratio(population=880.0, allee_threshold=500.0)),
    ("grid voltage collapse", "loading / nose",
     voltage_stability_ratio(loading=0.94, max_loading=1.0)),
    ("Griffith fracture", "K_I / K_IC",
     fracture_ratio(stress_intensity=41.0, fracture_toughness=52.0)),
    ("fishery collapse", "harvest / MSY",
     fishery_ratio(harvest=1150.0, intrinsic_growth=0.42,
                   carrying_capacity=10000.0)),
)


def main() -> None:
    audit = CascadeAudit()
    # Identical statistical pressure for every domain, so the only column that
    # moves is the structural one. That is what keeping the two reads independent
    # buys: the six signals cannot tell these eight situations apart, and the
    # spinodal separates "stressed, and you can still act" from "committed."
    signals = SignalReads(critical_slowing_down=0.7, variance_inflation=0.65,
                          skew_to_alt_well=0.6, flickering=0.55,
                          diversity_collapse=0.65)

    print(f"spinodal h* = {H_SPINODAL:.4f}   (ratio 1.00 maps exactly onto it)\n")
    print(f"{'domain':<24}{'control':<26}{'ratio':>7}{'h_eff':>8}  regime")
    print("-" * 78)
    for name, control, ratio in DOMAINS:
        h_eff = h_eff_from_ratio(ratio)
        result = audit.audit(signals, h_eff)
        print(f"{name:<24}{control:<26}{ratio:>7.2f}{h_eff:>8.3f}  "
              f"{result.regime.value}")

    print("\nThe fishery and the fractured plate share no physics. They share a"
          "\nfold, and that is enough for one instrument to read both.")


if __name__ == "__main__":
    main()
