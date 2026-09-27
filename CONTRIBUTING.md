# Contributing

Thanks for your interest. This is a small toy simulation, so please keep changes small and explicit.

1. Open an issue first for anything beyond a typo.
2. Create a branch, then `python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"`.
3. Before opening a PR, run `ruff check . && ruff format --check . && pytest`.
4. **Fail closed.** Any new input path must HOLD on invalid, non-finite, or ambiguous input, and needs a test that proves it.
5. If the demo output changes, update `tests/demo_output.txt` and the README in the same PR, and explain why in `CHANGELOG.md`.
6. **Claim hygiene.** Do not add efficacy, clinical, accessibility-outcome, or hardware claims. Tag results
   **SYNTHETIC** (seeded or hand-written) or **UNRUN** (not executed). Real EEG or headset data must not be committed.

By contributing, you agree that your contributions are licensed under the MIT License.
