# Orchestration-Inspired MIDI Edits

This repository is a clean external-validation package for three symbolic MIDI edits developed in the reference frame of Matthieu Cervera and the `midi-editing` project. The review path is intentionally simple: inspect the edit code, then listen to pre-rendered original/transformed comparisons from MidiCaps/Lakh examples.

## Demo

Open the GitHub Pages demo:

- https://micaant.github.io/devMusicEdit/

The same page is available locally at:

- [docs/index.html](docs/index.html)

The demo is organized by edit type and includes MP3 audio controls for each original MIDI and its transformed counterpart. MIDI files are also included for reproducibility.

## Source Code

The three edits are implemented in:

- [src/orchestration_edits.py](src/orchestration_edits.py)

The file is designed to stay small and inspectable. It contains the edit classes, helper functions for selecting target instruments, and result descriptions used to generate the demo outputs.

## Edits

- `Shift_Octave`: moves the selected non-drum instrument line one octave up or down while preserving timing and note durations.
- `Double_Octave`: keeps the original line and adds a duplicate line one octave above or below the selected instrument.
- `Make_Staccato`: shortens notes in the selected instrument line while preserving note starts and pitch content.

## Upstream Reference

This work is a local orchestration-oriented extension built for review and comparison. It is not an upstream modification.

- Matthieu Cervera `midi-editing`: https://github.com/matthieu-cervera/midi-editing

## Running Locally

The supervisor-facing demo does not require running Python. To inspect it from a checkout, open `docs/index.html` in a browser.

To recreate a Python environment for code inspection or rerunning edits:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For local verification:

```bash
python scripts/verify_demo_assets.py
```
