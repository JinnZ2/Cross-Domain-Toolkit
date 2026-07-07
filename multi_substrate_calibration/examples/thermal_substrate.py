"""thermal_substrate.py -- worked example: wiring a thermal feed into the gate.

A thermocouple reads the present state directly, so it is a GROUND substrate.
Its native confidence comes from the sensor's signal-to-noise; its demonstrated
reliability (from calibration against a reference) discounts that confidence into
the shared frame. Nothing in determinacy_gate.py had to change to accept it.

Run:  python -m multi_substrate_calibration.examples.thermal_substrate
"""

from __future__ import annotations

from ..substrate import Calibration, Role, Substrate, SubstrateReading, make_reading


class ThermalProbe(Substrate):
    modality = "thermal"
    role = Role.GROUND
    units = "K"

    def __init__(self, snr: float, reliability: float = 0.95) -> None:
        # A sensor known to track a reference within ~5% gets reliability ~0.95.
        super().__init__(Calibration(reliability=reliability))
        self.snr = snr

    def read(self) -> SubstrateReading:
        # native confidence from signal-to-noise: saturating map into [0, 1].
        native = self.snr / (self.snr + 1.0)
        temperature_k = 300.0 + self._sample()
        return make_reading(self, temperature_k, native, provenance={"snr": self.snr})

    def _sample(self) -> float:
        # stand-in for a real ADC read; deterministic here for the demo.
        return 4.2


if __name__ == "__main__":
    from ..determinacy_gate import DeterminacyGate

    probe_a = ThermalProbe(snr=20.0)
    probe_b = ThermalProbe(snr=9.0)
    reads = [probe_a.bound_read(), probe_b.bound_read()]

    gate = DeterminacyGate(epsilon=0.1, predict_tolerance=2.0)
    result = gate.evaluate(reads)
    print("state estimate :", round(result.state_estimate, 3), "K")
    print("determinacy    :", round(result.determinacy, 4))
    print("verdict        :", result.verdict.value)
    print("reason         :", result.reason)
