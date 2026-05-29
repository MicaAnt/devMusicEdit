# Orchestration-Inspired MIDI Edits

A compact validation package for three symbolic MIDI edits: `Shift_Octave`, `Double_Octave`, and `Make_Staccato`.

The repository is meant for quick review: the implementation is contained in one source file, and the demo provides pre-rendered original/transformed audio comparisons grouped by edit type.

## Demo

GitHub Pages:

- https://micaant.github.io/devMusicEdit/

## Edit Source

- [src/orchestration_edits.py](src/orchestration_edits.py)

The implementation keeps the edits small and explicit: target-instrument selection, symbolic note mutation, and a compact result object for generating examples.

## Edits

- `Shift_Octave`: shifts the selected non-drum instrument line one octave up or down while preserving note timing and duration.
- `Double_Octave`: keeps the original line and adds a duplicate line one octave above or below the selected instrument.
- `Make_Staccato`: shortens notes in the selected instrument line while preserving note starts and pitch content.

## Reference

This work follows the style and framing of Matthieu Cervera's `midi-editing` project, but it is a local extension for orchestration-oriented validation rather than an upstream modification.

- https://github.com/matthieu-cervera/midi-editing

## Reproducibility

The demo includes MP3 previews rendered with FluidSynth and a General MIDI soundfont, plus MIDI files for inspection. To verify the package locally:

```bash
python scripts/verify_demo_assets.py
```

To recreate the Python environment used for the edit code:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
