"""acoustic_substrate.py -- worked example: an acoustic substrate as PREDICT.

An acoustic array here does not report the present state directly; it runs a
short-horizon cascade model on the sound field to forecast where the tracked
quantity is heading. That makes it a PREDICT substrate. The determinacy gate
will hold its forecast against the fused GROUND state rather than averaging it
in -- so a confident forecast that contradicts the thermocouples drains
determinacy instead of silently biasing the estimate.

Run:  python -m multi_substrate_calibration.examples.acoustic_substrate
"""

from __future__ import annotations

from ..substrate import Calibration, Role, Substrate, SubstrateReading, make_reading


class AcousticForecaster(Substrate):
    modality = "acoustic"
    role = Role.PREDICT
    units = "K"  # forecasts the same quantity the ground layer measures

    def __init__(self, forecast_value: float, model_confidence: float,
                 reliability: float = 0.6) -> None:
        # Forecasters earn less reliability than a calibrated direct sensor.
        super().__init__(Calibration(reliability=reliability))
        self.forecast_value = forecast_value
        self.model_confidence = model_confidence

    def read(self) -> SubstrateReading:
        return make_reading(
            self, self.forecast_value, self.model_confidence,
            provenance={"horizon_s": 30},
        )


if __name__ == "__main__":
    from ..determinacy_gate import DeterminacyGate
    from .thermal_substrate import ThermalProbe

    ground = [ThermalProbe(snr=20.0).bound_read(), ThermalProbe(snr=15.0).bound_read()]
    gate = DeterminacyGate(epsilon=0.1, predict_tolerance=2.0)

    agreeing = AcousticForecaster(forecast_value=304.5, model_confidence=0.9)
    print("--- forecast agrees with ground ---")
    r1 = gate.evaluate(ground + [agreeing.bound_read()])
    print("determinacy:", round(r1.determinacy, 4), "| verdict:", r1.verdict.value)

    contradicting = AcousticForecaster(forecast_value=330.0, model_confidence=0.95)
    print("--- confident forecast contradicts ground ---")
    r2 = gate.evaluate(ground + [contradicting.bound_read()])
    print("determinacy:", round(r2.determinacy, 4), "| verdict:", r2.verdict.value)
    print("reason     :", r2.reason)
