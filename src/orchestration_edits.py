from __future__ import annotations

import copy
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import pretty_midi


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_GM_INFO = PROJECT_ROOT / "upstream" / "midi-editing" / "GM_info" / "GM_instruments.pkl"


if UPSTREAM_GM_INFO.exists():
    with UPSTREAM_GM_INFO.open("rb") as f:
        GM_INSTRUMENTS = pickle.load(f)
else:
    GM_INSTRUMENTS = {}


def instrument_name(program: int) -> str:
    info = GM_INSTRUMENTS.get(program)
    if info is None:
        return pretty_midi.program_to_instrument_name(program)
    return info["name"]


def _coerce_midi(midi_or_path) -> pretty_midi.PrettyMIDI:
    if isinstance(midi_or_path, pretty_midi.PrettyMIDI):
        return midi_or_path
    return pretty_midi.PrettyMIDI(str(midi_or_path))


def clone_midi(midi_or_path) -> pretty_midi.PrettyMIDI:
    return copy.deepcopy(_coerce_midi(midi_or_path))


def grouped_non_drum_instruments(midi_or_path) -> dict[int, List[pretty_midi.Instrument]]:
    midi = _coerce_midi(midi_or_path)
    groups: dict[int, List[pretty_midi.Instrument]] = {}
    for inst in midi.instruments:
        if inst.is_drum:
            continue
        groups.setdefault(inst.program, []).append(inst)
    return groups


def available_instruments(midi_or_path) -> List[dict]:
    groups = grouped_non_drum_instruments(midi_or_path)
    rows = []
    for program, instruments in sorted(groups.items()):
        rows.append(
            {
                "program": program,
                "name": instrument_name(program),
                "tracks": len(instruments),
                "notes": sum(len(inst.notes) for inst in instruments),
            }
        )
    return rows


def choose_program(
    midi_or_path,
    *,
    program: Optional[int] = None,
    instrument: Optional[str] = None,
) -> int:
    groups = grouped_non_drum_instruments(midi_or_path)
    if program is not None:
        if program not in groups:
            raise ValueError(f"Program {program} not found in MIDI.")
        return program

    if instrument is not None:
        normalized = instrument.strip().lower()
        matches = [prog for prog in groups if instrument_name(prog).lower() == normalized]
        if not matches:
            raise ValueError(f"Instrument {instrument!r} not found in MIDI.")
        if len(matches) > 1:
            raise ValueError(f"Instrument {instrument!r} is ambiguous in this MIDI.")
        return matches[0]

    if len(groups) == 1:
        return next(iter(groups))

    choices = ", ".join(f"{row['program']}:{row['name']}" for row in available_instruments(midi_or_path))
    raise ValueError(
        "Please select `program` or `instrument` explicitly for multi-instrument MIDI files. "
        f"Available choices: {choices}"
    )


def save_midi(midi: pretty_midi.PrettyMIDI, output_path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(output_path))
    return output_path


@dataclass
class EditResult:
    midi: pretty_midi.PrettyMIDI
    source_program: int
    source_instrument: str
    edit_info: str
    prompt: str
    changed_notes: int
    affected_tracks: int
    extra: dict


class BaseOrchestrationEdit:
    type_name = "BaseOrchestrationEdit"

    def __init__(self, *, program: Optional[int] = None, instrument: Optional[str] = None):
        self.program = program
        self.instrument = instrument

    def _selected_group(self, midi: pretty_midi.PrettyMIDI) -> tuple[int, List[pretty_midi.Instrument]]:
        program = choose_program(midi, program=self.program, instrument=self.instrument)
        groups = grouped_non_drum_instruments(midi)
        return program, groups[program]

    def apply(self, midi_or_path) -> EditResult:
        raise NotImplementedError


class Shift_Octave(BaseOrchestrationEdit):
    type_name = "Shift_Octave"
    DIRECTIONS = {"up": 12, "down": -12}

    def __init__(self, *, direction: str, program: Optional[int] = None, instrument: Optional[str] = None):
        super().__init__(program=program, instrument=instrument)
        if direction not in self.DIRECTIONS:
            raise ValueError(f"direction must be one of {sorted(self.DIRECTIONS)}")
        self.direction = direction

    def apply(self, midi_or_path) -> EditResult:
        midi = clone_midi(midi_or_path)
        program, group = self._selected_group(midi)
        delta = self.DIRECTIONS[self.direction]
        changed_notes = 0
        clipped_notes = 0

        for inst in group:
            for note in inst.notes:
                new_pitch = note.pitch + delta
                bounded = min(127, max(0, new_pitch))
                if bounded != new_pitch:
                    clipped_notes += 1
                note.pitch = bounded
                changed_notes += 1

        source_name = instrument_name(program)
        edit_info = f"instrument {source_name} line shifted {self.direction} by one octave"
        prompt = f"Shift the {source_name} up by one octave." if self.direction == "up" else f"Shift the {source_name} down by one octave."
        return EditResult(
            midi=midi,
            source_program=program,
            source_instrument=source_name,
            edit_info=edit_info,
            prompt=prompt,
            changed_notes=changed_notes,
            affected_tracks=len(group),
            extra={"direction": self.direction, "clipped_notes": clipped_notes},
        )


class Double_Octave(BaseOrchestrationEdit):
    type_name = "Double_Octave"
    DIRECTIONS = {"above": 12, "below": -12}

    def __init__(self, *, direction: str, program: Optional[int] = None, instrument: Optional[str] = None):
        super().__init__(program=program, instrument=instrument)
        if direction not in self.DIRECTIONS:
            raise ValueError(f"direction must be one of {sorted(self.DIRECTIONS)}")
        self.direction = direction

    def apply(self, midi_or_path) -> EditResult:
        midi = clone_midi(midi_or_path)
        program, group = self._selected_group(midi)
        delta = self.DIRECTIONS[self.direction]
        added_notes = 0
        skipped_notes = 0

        for inst in group:
            doubled = pretty_midi.Instrument(program=inst.program, is_drum=False, name=f"{inst.name or instrument_name(inst.program)} octave {self.direction}")
            for note in inst.notes:
                new_pitch = note.pitch + delta
                if not 0 <= new_pitch <= 127:
                    skipped_notes += 1
                    continue
                doubled.notes.append(
                    pretty_midi.Note(
                        velocity=note.velocity,
                        pitch=new_pitch,
                        start=note.start,
                        end=note.end,
                    )
                )
                added_notes += 1
            midi.instruments.append(doubled)

        source_name = instrument_name(program)
        edit_info = f"instrument {source_name} line doubled one octave {self.direction}"
        prompt = (
            f"Double the {source_name} one octave above."
            if self.direction == "above"
            else f"Double the {source_name} one octave below."
        )
        return EditResult(
            midi=midi,
            source_program=program,
            source_instrument=source_name,
            edit_info=edit_info,
            prompt=prompt,
            changed_notes=added_notes,
            affected_tracks=len(group),
            extra={"direction": self.direction, "skipped_notes": skipped_notes},
        )


class Make_Staccato(BaseOrchestrationEdit):
    type_name = "Make_Staccato"

    def __init__(
        self,
        *,
        program: Optional[int] = None,
        instrument: Optional[str] = None,
        length_factor: float = 0.7,
        min_duration_sec: float = 0.03,
    ):
        super().__init__(program=program, instrument=instrument)
        self.length_factor = length_factor
        self.min_duration_sec = min_duration_sec

    def apply(self, midi_or_path) -> EditResult:
        midi = clone_midi(midi_or_path)
        program, group = self._selected_group(midi)
        changed_notes = 0

        for inst in group:
            for note in inst.notes:
                duration = note.end - note.start
                new_duration = max(duration * self.length_factor, self.min_duration_sec)
                note.end = min(note.start + new_duration, note.end)
                changed_notes += 1

        source_name = instrument_name(program)
        edit_info = f"instrument {source_name} line made staccato with note lengths scaled to {self.length_factor}"
        prompt = f"Make the {source_name} line staccato."
        return EditResult(
            midi=midi,
            source_program=program,
            source_instrument=source_name,
            edit_info=edit_info,
            prompt=prompt,
            changed_notes=changed_notes,
            affected_tracks=len(group),
            extra={"length_factor": self.length_factor, "min_duration_sec": self.min_duration_sec},
        )


def describe_edit_result(result: EditResult) -> str:
    lines = [
        f"type: {result.prompt}",
        f"source instrument: {result.source_instrument} (program {result.source_program})",
        f"edit_info: {result.edit_info}",
        f"changed_notes: {result.changed_notes}",
        f"affected_tracks: {result.affected_tracks}",
    ]
    for key, value in result.extra.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def list_available_instruments(midi_or_path) -> List[str]:
    return [f"{row['program']}: {row['name']} ({row['tracks']} tracks, {row['notes']} notes)" for row in available_instruments(midi_or_path)]
