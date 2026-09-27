# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-09-27

### Added
- Initial import of the founder's BCI membrane latch script as `bci_membrane/bci_membrane.py`
  (paste truncated in `demo()`; completed minimally).
- Package `__init__.py`, pytest suite (49 tests), demo snapshot, ruff config, CI on Python 3.10–3.13.
- README, LICENSE (MIT), CITATION.cff, CONTRIBUTING, SECURITY, CODEOWNERS, `docs/REVIEW.md`.

### Fixed (fail-closed; see docs/REVIEW.md)
- FIX-1: `seat_cap()` never seated the reference (chicken-and-egg against the all-zeros initial
  reference), so the demo fired 0 commands. It now seats a valid calibration sample.
- FIX-2: A fresh membrane was SAFE before any cap was seated. SAFE now requires a seated reference.
- FIX-3: `decoder_p = NaN` (and `inf`, values > 1, non-numbers) fired intents. It must now be a finite real in `[0.6, 1.0]`.
- FIX-4: `residual()` swallowed NaN depending on position, truncated mismatched lengths, and
  crashed on empty input. It now raises `ValueError` per the oes32-residual contract (ADR-001), and
  the membrane latches (`R = inf`, `SAFE = False`).

### Changed
- `COHERENCE_FLOOR` renamed to `RESIDUAL_TOLERANCE` (alias kept).
- `IntentEvent` gains `safe`; the demo's SAFE column reports the gate's decision.
- Demo output changed from `fired 0 commands` (original) to `fired 3 commands`. Both outputs are
  recorded verbatim in `docs/REVIEW.md`.

[0.1.0]: https://github.com/sparkainlp-x/bci-membrane-latch/releases/tag/v0.1.0
