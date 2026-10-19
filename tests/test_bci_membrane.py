"""Tests for the toy BCI membrane latch. All inputs are SYNTHETIC."""

from __future__ import annotations

import math
import random
import subprocess
import sys
from pathlib import Path

import pytest

from bci_membrane import (
    COHERENCE_FLOOR,
    INTENTS,
    RESIDUAL_TOLERANCE,
    BCIMembrane,
    W,
    coherence,
    demo,
    residual,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path(__file__).with_name("demo_output.txt")


def seated() -> BCIMembrane:
    bci = BCIMembrane()
    bci.seat_cap()
    assert bci.face.safe
    return bci


# --- residual contract (ADR-001) -------------------------------------------


def test_residual_is_max_abs_difference():
    x = [0.0] * W
    ref = [0.0] * W
    x[5] = -0.3
    x[9] = 0.2
    assert residual(x, ref) == pytest.approx(0.3)


def test_tolerance_boundary_is_inclusive():
    bci = seated()
    bci.face.xref = [0.0] * W
    bci.face.x = [0.0] * W
    bci.face.x[0] = RESIDUAL_TOLERANCE
    bci.face.refresh()
    assert bci.face.R == RESIDUAL_TOLERANCE
    assert bci.face.safe  # failure only when R > tolerance
    bci.face.x[0] = math.nextafter(RESIDUAL_TOLERANCE, 1.0)
    bci.face.refresh()
    assert not bci.face.safe


def test_coherence_floor_alias():
    assert COHERENCE_FLOOR == RESIDUAL_TOLERANCE


@pytest.mark.parametrize(
    "x, ref",
    [
        ([], []),
        ([0.0] * W, [0.0] * (W - 1)),
        ([0.0] * (W + 1), [0.0] * W),
    ],
)
def test_residual_rejects_empty_and_mismatched(x, ref):
    with pytest.raises(ValueError):
        residual(x, ref)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("pos", [0, 7, W - 1])
def test_residual_rejects_non_finite_any_position(bad, pos):
    x = [0.0] * W
    x[pos] = bad
    with pytest.raises(ValueError):
        residual(x, [0.0] * W)
    with pytest.raises(ValueError):
        residual([0.0] * W, x)


def test_coherence_invalid_is_zero():
    assert coherence([math.nan] * W, [0.0] * W) == 0.0
    assert coherence([], []) == 0.0


# --- gate behaviour ----------------------------------------------------------


def test_fresh_membrane_is_latched_until_seated():
    bci = BCIMembrane()
    assert not bci.face.safe
    ev = bci.decode("yes", 0.99)
    assert not ev.fired
    assert ev.reason == "latched: no reference seated"
    assert bci.fired == []


def test_seat_cap_seats_reference():
    bci = BCIMembrane()
    bci.seat_cap()
    assert bci.face.seated
    assert bci.face.xref == bci.face.x
    assert bci.face.R == 0.0
    assert bci.face.safe


@pytest.mark.parametrize("intent", INTENTS)
def test_each_intent_fires_when_safe_and_confident(intent):
    bci = seated()
    ev = bci.decode(intent, 0.6)
    assert ev.fired and ev.safe
    assert ev.reason == f"hologram:{intent}"
    assert bci.fired == [ev]


@pytest.mark.parametrize("p", [0.0, 0.41, 0.5999])
def test_low_decoder_p_holds(p):
    bci = seated()
    ev = bci.decode("yes", p)
    assert not ev.fired
    assert ev.reason == "decoder unsure"


def test_latch_on_slip_and_recover_on_reseat():
    bci = seated()
    bci.slip_cap()
    assert bci.face.R > RESIDUAL_TOLERANCE
    ev = bci.decode("help", 0.95)
    assert not ev.fired
    assert ev.reason == "latched: residual too high"
    bci.seat_cap()
    assert bci.decode("help", 0.95).fired


def test_unknown_intent_never_fires():
    bci = seated()
    for raw in ("maybe", "", "YES", None, 3):
        ev = bci.decode(raw, 0.99)  # type: ignore[arg-type]
        assert not ev.fired
        assert ev.intent is None
        assert ev.reason == "unknown intent"
    assert bci.fired == []


@pytest.mark.parametrize("p", [math.nan, math.inf, -math.inf, 1.5, -0.1, None, "0.9", True])
def test_invalid_decoder_p_fails_closed(p):
    bci = seated()
    ev = bci.decode("yes", p)  # type: ignore[arg-type]
    assert not ev.fired
    assert ev.reason == "invalid decoder_p"


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("pos", [0, 13, W - 1])
def test_non_finite_face_fails_closed(bad, pos):
    bci = seated()
    bci.face.x = list(bci.face.xref)
    bci.face.x[pos] = bad
    bci.face.refresh()
    assert bci.face.R == math.inf
    assert not bci.face.safe
    assert not bci.decode("yes", 0.99).fired


def test_truncated_face_fails_closed():
    bci = seated()
    bci.face.x = bci.face.xref[:4]  # would have been silently compared by zip()
    bci.face.refresh()
    assert not bci.face.safe
    assert not bci.decode("yes", 0.99).fired


def test_nan_quality_counts_as_worst():
    bci = seated()
    bci.sample_eeg(math.nan)
    assert not bci.face.safe


# --- determinism and demo snapshot ------------------------------------------


def _trace(bci: BCIMembrane):
    bci.seat_cap()
    a = (bci.face.R, list(bci.face.x))
    bci.slip_cap()
    return a, (bci.face.R, list(bci.face.x))


def test_determinism_seed_32():
    assert _trace(BCIMembrane()) == _trace(BCIMembrane(random.Random(32)))
    assert _trace(BCIMembrane()) != _trace(BCIMembrane(random.Random(33)))


def test_demo_output_snapshot(capsys):
    demo()
    assert capsys.readouterr().out == SNAPSHOT.read_text(encoding="utf-8")


def test_script_runs_as_file():
    out = subprocess.run(
        [sys.executable, str(ROOT / "bci_membrane" / "bci_membrane.py")],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    assert out == SNAPSHOT.read_text(encoding="utf-8")
    assert out.rstrip().endswith("fired 3 commands")
