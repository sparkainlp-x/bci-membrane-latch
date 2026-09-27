"""Toy BCI membrane latch: a fail-closed gate between simulated EEG quality and hologram intents.

Not a medical device. Not a clinical BCI decoder. No real EEG.
"""

from .bci_membrane import (
    COHERENCE_FLOOR,
    DECODER_P_MIN,
    HOLO,
    INTENTS,
    RESIDUAL_TOLERANCE,
    BCIMembrane,
    Face,
    IntentEvent,
    W,
    coherence,
    demo,
    residual,
)

__version__ = "0.1.0"

__all__ = [
    "BCIMembrane",
    "COHERENCE_FLOOR",
    "DECODER_P_MIN",
    "Face",
    "HOLO",
    "INTENTS",
    "IntentEvent",
    "RESIDUAL_TOLERANCE",
    "W",
    "coherence",
    "demo",
    "residual",
]
