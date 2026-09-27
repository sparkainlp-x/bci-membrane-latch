#!/usr/bin/env python3
"""
BCI → OES-32 membrane latch → hologram intents.

Track A only. Simulated EEG quality, not a clinical decoder.
Four commands fire only when residual is low (SAFE).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

W = 32
COHERENCE_FLOOR = 0.08
INTENTS = ("yes", "no", "next", "help")


def residual(x: List[float], xref: List[float]) -> float:
    return max(abs(a - b) for a, b in zip(x, xref))


def coherence(x: List[float], xref: List[float]) -> float:
    s = 0.0
    for a, b in zip(x, xref):
        p = min(1.0, abs(a - b) / 0.4)
        s += 2.0 * p * (1.0 - p)
    return 1.0 - s / max(1, len(x))


@dataclass
class Face:
    x: List[float] = field(default_factory=lambda: [0.0] * W)
    xref: List[float] = field(default_factory=lambda: [0.0] * W)
    R: float = 0.0
    C: float = 1.0
    safe: bool = True
    seq: int = 0

    def refresh(self) -> None:
        self.R = residual(self.x, self.xref)
        self.C = coherence(self.x, self.xref)
        self.safe = self.R <= COHERENCE_FLOOR
        self.seq += 1


@dataclass
class IntentEvent:
    seq: int
    intent: Optional[str]
    fired: bool
    reason: str
    R: float
    C: float


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
        q = min(1.0, max(0.0, quality))
        amp = 0.02 + (1.0 - q) * 0.35
        self.face.x = [self.rng.gauss(0.0, amp) for _ in range(W)]
        self.face.refresh()

    def slip_cap(self) -> None:
        self.sample_eeg(quality=0.15)

    def seat_cap(self) -> None:
        self.sample_eeg(quality=0.92)
        if self.face.safe:
            self.face.xref = list(self.face.x)
            self.face.refresh()

    def decode(self, raw_intent: str, decoder_p: float = 0.8) -> IntentEvent:
        raw = raw_intent if raw_intent in INTENTS else None
        if raw is None:
            ev = IntentEvent(self.face.seq, None, False, "unknown intent", self.face.R, self.face.C)
        elif not self.face.safe:
            ev = IntentEvent(self.face.seq, raw, False, "latched: residual too high", self.face.R, self.face.C)
        elif decoder_p < 0.6:
            ev = IntentEvent(self.face.seq, raw, False, "decoder unsure", self.face.R, self.face.C)
        else:
            ev = IntentEvent(self.face.seq, raw, True, f"hologram:{raw}", self.face.R, self.face.C)
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
            f"SAFE={str(ev.R <= COHERENCE_FLOOR):5s}  "
            f"{intent:4s} p={p:.2f}  →  {out}  ({ev.reason})"
        )
    print("-" * 56)
    print(f"fired {len(bci.fired)} commands")


if __name__ == "__main__":
    demo()
