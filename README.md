# bci-membrane-latch

A **toy simulation** of a fail-closed safety gate between a noisy, *synthetic* EEG-like signal-quality value and four hologram UI intents (`yes`, `no`, `next`, `help`). An intent fires only when the OES-32 residual against a seated reference is within tolerance **and** a stub decoder is confident enough. Otherwise the gate latches and holds.

> [!WARNING]
> **Synthetic EEG-like signals only. Not a medical device. Not for diagnosis, treatment or monitoring of any condition, and no health claims are made.**
> Every signal in this repository comes from a seeded pseudo-random generator, and the "decoder" is a number you pass in.
> Nothing here has been run against a headset or a person, and it must not be used to control any real system.

## What it is

- A ~200-line, standard-library-only Python model of a **latch**: `SAFE` ⇔ a reference is seated **and** `R ≤ 0.08`, where `R = max_i |x[i] − x_ref[i]|` over a 32-component "face".
- A simulated cap: `sample_eeg(quality)` draws 32 synthetic Gaussian values whose spread grows as the simulated contact quality drops. `seat_cap()` takes a clean-cap calibration sample and seats it as the reference; `slip_cap()` simulates a poor-contact sample.
- A gate, `decode(intent, decoder_p)`, that fires a hologram intent only when all of these hold: the intent is known, the face is SAFE, and `decoder_p` is a finite number in `[0.6, 1.0]`. Anything else is **HOLD** (fail-closed).

The design intent is that a noisy or slipped simulated cap should produce *no action*, not a wrong one. That is a design intent, not a demonstrated outcome.

## Quickstart

```bash
git clone https://github.com/sparkainlp-x/bci-membrane-latch.git
cd bci-membrane-latch
python3 bci_membrane/bci_membrane.py
```

Output (seed 32, deterministic; **SYNTHETIC**):

```text
BCI membrane latch  ·  synthetic EEG-like  ·  not a medical device
--------------------------------------------------------
seat cap            R=0.000  C=1.000  SAFE=True   yes  p=0.88  →  avatar nods / confirm booking  (hologram:yes)
ask next            R=0.000  C=1.000  SAFE=True   next p=0.81  →  next hologram slide  (hologram:next)
cap slips           R=0.768  C=0.763  SAFE=False  help p=0.90  →  HOLD  (latched: residual too high)
help while noisy    R=0.768  C=0.763  SAFE=False  help p=0.91  →  HOLD  (latched: residual too high)
reseated            R=0.000  C=1.000  SAFE=True   help p=0.86  →  show high-contrast help card  (hologram:help)
weak decode         R=0.000  C=1.000  SAFE=True   yes  p=0.41  →  HOLD  (decoder unsure)
--------------------------------------------------------
fired 3 commands
```

`R = 0.000` right after seating is expected: the reference *is* that sample. The "ask next" and "weak decode" steps do not take a new sample, so they reuse the current face.

As a library:

```python
from bci_membrane import BCIMembrane

bci = BCIMembrane()          # seeded with random.Random(32)
bci.decode("yes", 0.9)       # HOLD: no reference seated yet
bci.seat_cap()
bci.decode("yes", 0.9)       # fires "hologram:yes"
bci.slip_cap()
bci.decode("help", 0.9)      # HOLD: latched, residual too high
```

## Limitations

- Not a medical device, a BCI decoder, an EEG pipeline or an assistive-technology product, and not evidence that anyone can operate a hologram interface.
- No real EEG, headset or person has been involved. The signal model is 32 synthetic Gaussian values; it does not model any physiological signal.
- No claim is made about signal quality metrics, headset hardware, decoding accuracy, latency or accessibility outcomes.
- The tolerance `0.08` and the decoder floor `0.6` are toy values and are not calibrated to anything.
- `seat_cap()` trusts any finite calibration sample as the reference. A real system would need an independent contact-quality check (**UNRUN**).
- The `coherence` value printed by the demo is informational only. It never gates, and it is non-monotone (see [docs/REVIEW.md](docs/REVIEW.md)).

## Relationship to the OES-32 residual contract (ADR-001)

`residual()` follows the normative definition in [sparkainlp-x/oes32-residual](https://github.com/sparkainlp-x/oes32-residual) (ADR-001, Residual-canonical):

| Item | oes32-residual | this repo |
|---|---|---|
| Residual | `R = max_i \|x[i] − x_ref[i]\|` over 32 components | same |
| Failure rule | failure iff `R > tolerance` | latched iff `R > 0.08` (or no reference seated) |
| Invalid input | `ValueError` | `residual()` raises `ValueError`; the membrane converts it to `R = inf`, `SAFE = False` |

This is a downstream **consumer** of the contract, not a normative source. The tolerance `0.08` is a toy value for this simulation and is not calibrated to anything.

## Behaviour changes from the original script

The founder's original paste never fired a command. Its `seat_cap()` only seated the reference if the new sample was already SAFE against the *old* all-zeros reference, which the demo noise model never satisfied. Its actual output was six HOLDs and `fired 0 commands`. This repository fixes that and three other fail-open or fail-crash issues. Each fix is minimal and documented in [docs/REVIEW.md](docs/REVIEW.md) and [CHANGELOG.md](CHANGELOG.md). The original script's verbatim output is recorded in the review.

## Tests

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
python -W error -m pytest
```

The 49 tests cover: firing only when SAFE and `decoder_p ≥ 0.6`; latch on cap slip and recovery on reseat; unknown intents; NaN/±inf/out-of-range/non-numeric `decoder_p`; NaN/±inf anywhere in the face; empty and mismatched lengths; the inclusive tolerance boundary; determinism with seed 32; and a byte-exact snapshot of the demo output. CI runs on Python 3.10–3.13 with warnings treated as errors.

## Evidence labels

| Item | Label |
|---|---|
| Demo output, test vectors | **SYNTHETIC** (seeded PRNG / hand-written) |
| Any real EEG, headset or user result | **UNRUN** (none exists) |
| REPORTED or TARGET figures | none in this repository |

Label definitions: [sparkainlp-x/.github](https://github.com/sparkainlp-x/.github#evidence-tags).

## Layout

```text
bci_membrane/
  __init__.py
  bci_membrane.py      # model + demo (runnable as a script)
tests/
  test_bci_membrane.py
  demo_output.txt      # demo snapshot
docs/REVIEW.md         # code review, bugs found and fixed, original output
```

## How to cite

See [CITATION.cff](CITATION.cff). Cite the concept DOI [10.5281/zenodo.23462506](https://doi.org/10.5281/zenodo.23462506) for all versions,
or the version DOI [10.5281/zenodo.23462507](https://doi.org/10.5281/zenodo.23462507) for v0.1.0.

> Brisson, J.-F. (2026). *bci-membrane-latch: a toy fail-closed OES-32 residual gate between synthetic EEG-like signal quality and hologram intents* (Version 0.1.0) [Computer software]. Spark AI NLP, Fredericton, New Brunswick, Canada. https://github.com/sparkainlp-x/bci-membrane-latch

The residual contract it consumes: [oes32-residual](https://github.com/sparkainlp-x/oes32-residual), DOI [10.5281/zenodo.22985520](https://doi.org/10.5281/zenodo.22985520).

## License

Copyright (c) 2026 Jean-François Brisson, Spark AI NLP.

Released under the MIT License; see [LICENSE](LICENSE). Security reports: [SECURITY.md](SECURITY.md).
