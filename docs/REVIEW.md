# Code review: founder's original script (v0.1.0)

Scope: the pasted `bci_membrane.py` (paste truncated in `demo()`; completed minimally as
`print(f"fired {len(bci.fired)} commands")` plus the `__main__` guard). All observations are
**SYNTHETIC**, from running the script with its built-in seed (`random.Random(32)`) on CPython 3.13.

## Original output (verbatim, unmodified script)

```text
BCI membrane latch  ·  toy EEG  ·  not a medical device
--------------------------------------------------------
seat cap            R=0.097  C=0.872  SAFE=False  yes  p=0.88  →  HOLD  (latched: residual too high)
ask next            R=0.097  C=0.872  SAFE=False  next p=0.81  →  HOLD  (latched: residual too high)
cap slips           R=0.781  C=0.760  SAFE=False  help p=0.90  →  HOLD  (latched: residual too high)
help while noisy    R=0.781  C=0.760  SAFE=False  help p=0.91  →  HOLD  (latched: residual too high)
reseated            R=0.119  C=0.845  SAFE=False  help p=0.86  →  HOLD  (latched: residual too high)
weak decode         R=0.119  C=0.845  SAFE=False  yes  p=0.41  →  HOLD  (latched: residual too high)
--------------------------------------------------------
fired 0 commands
```

An earlier, unverified description of this demo said "seat cap R=0.11 SAFE → nods; ask next → next slide;
cap slips R=0.64 → HOLD; reseated → attendant card; weak decode → HOLD". **That does not match the real
output.** The real run fires nothing, and R=0.11 would not be SAFE anyway because 0.11 > 0.08.

## Findings

| # | Finding | Effect | Status |
|---|---|---|---|
| 1 | `seat_cap()` seats the reference only if the new sample is already SAFE against the *old* reference. The initial reference is all zeros. A clean-cap sample (σ ≈ 0.048) has max\|x\| over 32 channels ≈ 0.1, which is above 0.08, so the reference never seats. | Demo fires 0 commands. The gate is permanently latched, so the design intent is not realised. | **Fixed (FIX-1).** `seat_cap()` seats a valid calibration sample as the reference. |
| 2 | A fresh `Face` starts with `x == xref == zeros`, so `R = 0` and `SAFE = True` before any cap is seated. | **Fail-open**: `BCIMembrane().decode("yes", 0.9)` fired. | **Fixed (FIX-2).** New `seated` flag. SAFE requires a seated reference. |
| 3 | `decoder_p = NaN`: `NaN < 0.6` is `False`, so the "unsure" branch is skipped. | **Fail-open**: NaN confidence FIRES. Also `inf`, `1.5` and so on fired. | **Fixed (FIX-3).** Requires a finite real in `[0.6, 1.0]`; otherwise `"invalid decoder_p"`. |
| 4a | NaN in `x`: `max()` with NaN is order-dependent. If NaN is the first element, R = NaN and `NaN <= 0.08` is False (closed). If NaN comes later, it is silently skipped and R can be finite and SAFE. | **Fail-open** depending on channel position. | **Fixed (FIX-4).** Non-finite input raises `ValueError` in `residual()`; `refresh()` sets `R = inf`, `SAFE = False`. |
| 4b | `±inf` in `x` gives R = inf (closed), but `inf` in both `x` and `xref` gives `inf − inf = NaN` (see 4a). | Fail-open edge case | Fixed by FIX-4. |
| 4c | `zip()` silently truncates mismatched lengths. A 4-channel face would be compared on only 4 channels. | **Fail-open** | Fixed by FIX-4 (length check; `zip(strict=True)`). |
| 4d | Empty lists: `max()` raises `ValueError`, which crashes `refresh()`. | Crash rather than a latch | Fixed by FIX-4 (caught, so the face is latched). |
| 5 | `import math` was unused. | Lint | Now used (`math.isfinite`). |
| 6 | `COHERENCE_FLOOR` is actually a residual tolerance compared with R. | Misleading name | Renamed `RESIDUAL_TOLERANCE`; `COHERENCE_FLOOR` kept as an alias. |
| 7 | The demo's SAFE column recomputed `ev.R <= COHERENCE_FLOOR` instead of reporting the gate's decision. | Could disagree with the gate (e.g. unseated) | `IntentEvent.safe` added; the demo prints it. |
| 8 | `coherence()` uses `2p(1−p)`, which peaks at p = 0.5 and returns to 0 at p = 1. A channel that is off by ≥ 0.4 counts as perfectly coherent, which is why "cap slips" still shows C ≈ 0.76. NaN also gives `min(1.0, NaN) = 1.0`, so it contributes 0. | Misleading diagnostic. It **never gates**, so there is no safety impact. | Documented. Formula unchanged (NaN or invalid input now returns 0.0). |
| 9 | `sample_eeg(NaN)`: `max(0.0, NaN)` returns 0.0, which means worst quality and high noise. | Already fail-closed | Tested, unchanged. |
| 10 | `decode()` trusts the cached `face.safe`. Mutating `face.x` without `refresh()` leaves a stale state. | API hazard | Documented limitation, unchanged. |
| 11 | `seat_cap()` now trusts any valid calibration sample. A real system would need an independent contact-quality check before seating a baseline. | Design limitation | Documented, **UNRUN**. |

## Demo output after fixes

See the README. The fixed demo fires 3 commands (`yes`, `next`, `help`), latches on the cap slip
(R = 0.768), and holds the weak decode for `"decoder unsure"`. That now matches the demo's evident
*intent* but not the unverified numbers quoted above. For example, R right after seating is 0.000,
not 0.11, because the reference is that sample.
