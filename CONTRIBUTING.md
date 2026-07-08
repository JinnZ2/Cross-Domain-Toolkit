# Contributing

This toolkit is meant to be forked and extended. Two rules keep it coherent:

1. **stdlib-only Python 3 (≥ 3.7).** No third-party dependencies, no build step.
   If a change seems to need a dependency, prefer a stdlib implementation or open
   an issue first.
2. **The core never imports its plugins.** New domains are added as worked
   `examples/`, not by special-casing a core module. In `multi_substrate_calibration`
   the determinacy gate consumes the fixed `BoundReading` contract and never
   imports a substrate; in `cascade_regime_audit` the detector takes six
   normalized signals and never knows the domain. Keep that inversion.

## Adding an example (the common case)

1. Create `your_package/examples/<domain>.py` that maps your domain onto the
   abstract surface (subclass `Substrate`, define a kernel + `Claim`, or map
   observables onto `SignalReads`).
2. Make it a runnable module (`if __name__ == "__main__":` with a short demo).
3. Add a test under `your_package/tests/test_*.py`.

## Running tests

```bash
# everything
python -m unittest discover -p 'test_*.py'

# one package
python -m unittest cascade_regime_audit.tests.test_cascade_audit
```

Every example must run clean (`python -m your_package.examples.<name>`) and the
full test suite must pass before you push.
