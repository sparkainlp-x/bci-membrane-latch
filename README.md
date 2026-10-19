# bci-membrane-latch

A **toy simulation** of a fail-closed safety gate between a noisy, *simulated* EEG-quality signal and four hologram UI intents (`yes`, `no`, `next`, `help`). An intent fires only when the OES-32 residual against a seated reference is within tolerance **and** a stub decoder is confident enough. Otherwise the gate latches and holds.

> [!WARNING]
> **Not a medical device. Not a clinical BCI decoder. No real EEG is read. No accessibility efficacy claim is made.**
> Every signal in this repository comes from a seeded pseudo-random generator. The "decoder" is a number you pass in.
> Nothing here has been run against a headset, a person, or any clinical or assistive setting.

## What it is

- A ~200-line, standard-library-only Python model of a **latch**: `SAFE` ⇔ a reference is seated **and** `R ≤ 0.08`, where `R = max_i |x[i] − x_ref[i]|` over a 32-component "face".
- A simulated headset: `sample_eeg(quality)` draws 32 Gaussian values whose spread grows as contact quality drops. `seat_cap()` takes a clean-cap calibration sample and seats it as the reference; `slip_cap()` simulates a poor-contact sample.
- A gate, `decode(intent, decoder_p)`, that fires a hologram intent only when all of these hold: the intent is known, the face is SAFE, and `decoder_p` is a finite number in `[0.6, 1.0]`. Anything else is **HOLD** (fail-closed).

The context is disability-led interface design: the idea is that a noisy or slipped cap should produce *no action*, not a wrong one. That is a design intent, not a demonstrated outcome.

## What it is NOT

Not a medical device, a clinical or research BCI decoder, an EEG pipeline, an assistive-technology product, or evidence that any user can operate a hologram interface. It makes no claim about signal quality metrics, headset hardware, decoding accuracy, latency, or accessibility efficacy. The `coherence` value printed by the demo is a diagnostic number only. It never gates, and it is non-monotone (see [docs/REVIEW.md](docs/REVIEW.md)).

## Relationship to the OES-32 residual contract (ADR-001)

`residual()` follows the normative definition in [sparkainlp-x/oes32-residual](https://github.com/sparkainlp-x/oes32-residual) (ADR-001, Residual-canonical):

| Item | oes32-residual | this repo |
|---|---|---|
| Residual | `R = max_i \|x[i] − x_ref[i]\|` over 32 components | same |
| Failure rule | failure iff `R > tolerance` | latched iff `R > 0.08` (or no reference seated) |
| Invalid input | `ValueError` | `residual()` raises `ValueError`; the membrane converts it to `R = inf`, `SAFE = False` |

This is a downstream **consumer** of the contract, not a normative source. The tolerance `0.08` is a toy value for this simulation and is not calibrated to anything.

## Quickstart

```bash
git clone https://github.com/sparkainlp-x/bci-membrane-latch.git
cd bci-membrane-latch
python3 bci_membrane/bci_membrane.py
```

Output (seed 32, deterministic; **SYNTHETIC**):

```text
BCI membrane latch  ·  toy EEG  ·  not a medical device
--------------------------------------------------------
seat cap            R=0.000  C=1.000  SAFE=True   yes  p=0.88  →  avatar nods / confirm booking  (hologram:yes)
ask next            R=0.000  C=1.000  SAFE=True   next p=0.81  →  next hologram slide  (hologram:next)
cap slips           R=0.768  C=0.763  SAFE=False  help p=0.90  →  HOLD  (latched: residual too high)
help while noisy    R=0.768  C=0.763  SAFE=False  help p=0.91  →  HOLD  (latched: residual too high)
reseated            R=0.000  C=1.000  SAFE=True   help p=0.86  →  call attendant + high-contrast help card  (hologram:help)
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

## Behaviour changes from the original script

The founder's original paste never fired a command. Its `seat_cap()` only seated the reference if the new sample was already SAFE against the *old* all-zeros reference, which the demo noise model never satisfied. Its actual output was six HOLDs and `fired 0 commands`. This repository fixes that and three other fail-open or fail-crash issues. Each fix is minimal and documented in [docs/REVIEW.md](docs/REVIEW.md) and [CHANGELOG.md](CHANGELOG.md). The original script's verbatim output is recorded in the review.

## Tests

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```

The 49 tests cover: firing only when SAFE and `decoder_p ≥ 0.6`; latch on cap slip and recovery on reseat; unknown intents; NaN/±inf/out-of-range/non-numeric `decoder_p`; NaN/±inf anywhere in the face; empty and mismatched lengths; the inclusive tolerance boundary; determinism with seed 32; and a byte-exact snapshot of the demo output. CI runs on Python 3.10–3.13.

## Evidence tags

| Item | Tag |
|---|---|
| Demo output, test vectors | **SYNTHETIC** (seeded PRNG / hand-written) |
| Any real EEG, headset, user, or clinical result | **UNRUN** (none exists) |

Tag definitions: [sparkainlp-x/.github](https://github.com/sparkainlp-x/.github#evidence-tags).

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

## Citation and license

See [CITATION.cff](CITATION.cff). MIT, see [LICENSE](LICENSE). Security reports: [SECURITY.md](SECURITY.md).
