#!/usr/bin/env python3
"""
BCI → OES-32 membrane latch → hologram intents.

Track A only. Simulated EEG quality, not a clinical decoder.
Four commands fire only when residual is low (SAFE).

NOT a medical device. No real EEG is read. See README.md for scope.

Changes from the founder's original paste (v0.1.0, all fail-closed; see
CHANGELOG.md and docs/REVIEW.md for the full review):

* FIX-1  seat_cap() only seated the reference if the new sample was already
         SAFE against the *old* reference (initially all zeros). With the demo
         noise model that never happened, so nothing ever fired. seat_cap() now
         seats the calibration sample as the reference when it is valid.
* FIX-2  A fresh membrane started SAFE (x == xref == zeros, R = 0) and would
         fire intents before any cap was seated. SAFE now also requires a
         seated reference.
* FIX-3  decoder_p = NaN compared False against `< 0.6` and FIRED. decoder_p
         must now be a finite number in [0.6, 1.0] to fire.
* FIX-4  residual() silently truncated mismatched lengths (zip), raised on
         empty input, and could swallow NaN depending on position (max() with
         NaN is order-dependent). It now follows the oes32-residual contract
         (ADR-001): invalid input raises ValueError, and Face.refresh() turns
         that into R = inf, SAFE = False.
* NAMING COHERENCE_FLOOR is a residual tolerance; it is kept as an alias of
         RESIDUAL_TOLERANCE for compatibility.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

W = 32
RESIDUAL_TOLERANCE = 0.08
COHERENCE_FLOOR = RESIDUAL_TOLERANCE  # original (misleading) name, kept as alias
DECODER_P_MIN = 0.6
INTENTS = ("yes", "no", "next", "help")


def _validate(x: Sequence[float], xref: Sequence[float]) -> None:
    if len(x) == 0 or len(x) != len(xref):
        raise ValueError(f"length mismatch or empty: len(x)={len(x)}, len(xref)={len(xref)}")
    for v in (*x, *xref):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"non-finite or non-numeric component: {v!r}")


def residual(x: Sequence[float], xref: Sequence[float]) -> float:
    """OES-32 residual R = max_i |x[i] - xref[i]| (ADR-001). Raises ValueError on invalid input."""
    _validate(x, xref)
    return max(abs(a - b) for a, b in zip(x, xref, strict=True))


def coherence(x: Sequence[float], xref: Sequence[float]) -> float:
    """Diagnostic only (never gates). Note: 2p(1-p) is non-monotone in |x - xref|.

    Returns 0.0 for invalid input.
    """
    try:
        _validate(x, xref)
    except ValueError:
        return 0.0
    s = 0.0
    for a, b in zip(x, xref, strict=True):
        p = min(1.0, abs(a - b) / 0.4)
        s += 2.0 * p * (1.0 - p)
    return 1.0 - s / max(1, len(x))


@dataclass
class Face:
    x: List[float] = field(default_factory=lambda: [0.0] * W)
    xref: List[float] = field(default_factory=lambda: [0.0] * W)
    R: float = math.inf
    C: float = 0.0
    safe: bool = False
    seq: int = 0
    seated: bool = False

    def refresh(self) -> None:
        try:
            self.R = residual(self.x, self.xref)
        except ValueError:
            self.R = math.inf  # fail closed
        self.C = coherence(self.x, self.xref)
        self.safe = self.seated and math.isfinite(self.R) and self.R <= RESIDUAL_TOLERANCE
        self.seq += 1


@dataclass
class IntentEvent:
    seq: int
    intent: Optional[str]
    fired: bool
    reason: str
    R: float
    C: float
    safe: bool = False


def _valid_p(decoder_p: object) -> Optional[float]:
    if isinstance(decoder_p, bool) or not isinstance(decoder_p, (int, float)):
        return None
    p = float(decoder_p)
    if not math.isfinite(p) or p < 0.0 or p > 1.0:
        return None
    return p


class BCIMembrane:
    """
    quality: 0 = terrible contact / motion, 1 = clean cap.
    decoder_p: confidence the stub 'decoder' assigns to a guessed intent.
    """

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random(32)
        self.face = Face()
        self.face.refresh()
        self.last: Optional[IntentEvent] = None
        self.fired: List[IntentEvent] = []

    def sample_eeg(self, quality: float) -> None:
        """Map headset quality onto the 32-face. High noise → high residual."""
        q = min(1.0, max(0.0, quality))  # NaN -> 0.0 (worst quality)
        amp = 0.02 + (1.0 - q) * 0.35
        self.face.x = [self.rng.gauss(0.0, amp) for _ in range(W)]
        self.face.refresh()

    def slip_cap(self) -> None:
        self.sample_eeg(quality=0.15)

    def seat_cap(self) -> None:
        """Take a clean-cap calibration sample and seat it as the reference (FIX-1).

        The sample is trusted as the baseline if it is valid (finite, length W).
        A real system would need an independent contact-quality check (UNRUN).
        """
        self.sample_eeg(quality=0.92)
        try:
            _validate(self.face.x, [0.0] * W)
        except ValueError:
            self.face.seated = False
            self.face.refresh()
            return
        self.face.xref = list(self.face.x)
        self.face.seated = True
        self.face.refresh()

    def decode(self, raw_intent: str, decoder_p: float = 0.8) -> IntentEvent:
        f = self.face
        raw = raw_intent if isinstance(raw_intent, str) and raw_intent in INTENTS else None
        p = _valid_p(decoder_p)
        if raw is None:
            ev = IntentEvent(f.seq, None, False, "unknown intent", f.R, f.C, f.safe)
        elif not f.seated:
            ev = IntentEvent(f.seq, raw, False, "latched: no reference seated", f.R, f.C, f.safe)
        elif not f.safe:
            ev = IntentEvent(f.seq, raw, False, "latched: residual too high", f.R, f.C, f.safe)
        elif p is None:
            ev = IntentEvent(f.seq, raw, False, "invalid decoder_p", f.R, f.C, f.safe)
        elif p < DECODER_P_MIN:
            ev = IntentEvent(f.seq, raw, False, "decoder unsure", f.R, f.C, f.safe)
        else:
            ev = IntentEvent(f.seq, raw, True, f"hologram:{raw}", f.R, f.C, f.safe)
            self.fired.append(ev)
        self.last = ev
        return ev


HOLO = {
    "yes": "avatar nods / confirm booking",
    "no": "avatar shakes head / cancel",
    "next": "next hologram slide",
    "help": "call attendant + high-contrast help card",
}


def demo() -> None:
    bci = BCIMembrane()
    print("BCI membrane latch  ·  toy EEG  ·  not a medical device")
    print("-" * 56)

    steps = [
        ("seat cap", lambda: bci.seat_cap(), "yes", 0.88),
        ("ask next", None, "next", 0.81),
        ("cap slips", lambda: bci.slip_cap(), "help", 0.90),
        ("help while noisy", None, "help", 0.91),
        ("reseated", lambda: bci.seat_cap(), "help", 0.86),
        ("weak decode", None, "yes", 0.41),
    ]
    for label, prep, intent, p in steps:
        if prep:
            prep()
        ev = bci.decode(intent, decoder_p=p)
        out = HOLO.get(ev.intent or "", "—") if ev.fired else "HOLD"
        print(
            f"{label:18s}  R={ev.R:.3f}  C={ev.C:.3f}  "
            f"SAFE={str(ev.safe):5s}  "
            f"{intent:4s} p={p:.2f}  →  {out}  ({ev.reason})"
        )
    print("-" * 56)
    print(f"fired {len(bci.fired)} commands")


if __name__ == "__main__":
    demo()
