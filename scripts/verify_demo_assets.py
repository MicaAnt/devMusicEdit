#!/usr/bin/env python3
"""Verify that the static external-validation demo is self-contained."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX = DOCS / "index.html"
README = ROOT / "README.md"
STYLE = DOCS / "styles.css"

REQUIRED_EDITS = ("Shift_Octave", "Double_Octave", "Make_Staccato")
REQUIRED_README = (
    "Matthieu Cervera",
    "https://github.com/matthieu-cervera/midi-editing",
    *REQUIRED_EDITS,
)
FORBIDDEN_PUBLIC_TEXT = ("/" + "workspace", "." + "planning")


class DemoLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.audio_sources: list[str] = []
        self.links: list[str] = []
        self.stylesheets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "audio" and values.get("src"):
            self.audio_sources.append(values["src"])
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"])
        elif tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.stylesheets.append(values["href"])


def fail(message: str) -> None:
    raise SystemExit(f"Demo verification failed: {message}")


def is_external(reference: str) -> bool:
    return bool(urlparse(reference).scheme)


def assert_file(path: Path, label: str) -> None:
    if not path.is_file():
        fail(f"missing {label}: {path.relative_to(ROOT)}")
    if path.stat().st_size <= 0:
        fail(f"empty {label}: {path.relative_to(ROOT)}")


def resolve_docs_reference(reference: str) -> Path:
    return (DOCS / reference).resolve()


def main() -> None:
    assert_file(INDEX, "demo page")
    assert_file(README, "README")
    assert_file(STYLE, "stylesheet")

    html = INDEX.read_text(encoding="utf-8")
    css = STYLE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    parser = DemoLinkParser()
    parser.feed(html)

    unique_audio_sources = sorted(set(parser.audio_sources))
    if len(unique_audio_sources) != 24:
        fail(f"expected 24 unique audio references, found {len(unique_audio_sources)}")

    mp3_files = sorted((DOCS / "audio").glob("*.mp3"))
    if len(mp3_files) != 24:
        fail(f"expected 24 files in docs/audio, found {len(mp3_files)}")

    for source in unique_audio_sources:
        if not source.startswith("audio/") or not source.endswith(".mp3"):
            fail(f"unexpected audio reference: {source}")
        assert_file(resolve_docs_reference(source), "audio asset")

    midi_links = sorted({link for link in parser.links if link.startswith("midi/")})
    if len(midi_links) != 24:
        fail(f"expected 24 unique MIDI links, found {len(midi_links)}")
    for link in midi_links:
        if not link.endswith(".mid"):
            fail(f"unexpected MIDI reference: {link}")
        assert_file(resolve_docs_reference(link), "MIDI asset")

    for stylesheet in parser.stylesheets:
        if is_external(stylesheet):
            fail(f"external stylesheet is not expected: {stylesheet}")
        assert_file(resolve_docs_reference(stylesheet), "stylesheet reference")

    source_url = "https://github.com/MicaAnt/devMusicEdit/blob/main/src/orchestration_edits.py"
    if source_url not in parser.links:
        fail(f"missing source-code link to {source_url}")
    assert_file((ROOT / "src/orchestration_edits.py").resolve(), "edit source")

    for edit in REQUIRED_EDITS:
        if f">{edit}<" not in html:
            fail(f"missing edit heading in docs/index.html: {edit}")
        if edit not in readme:
            fail(f"missing edit name in README.md: {edit}")

    for required in REQUIRED_README:
        if required not in readme:
            fail(f"missing README text: {required}")

    for label, text in (("docs/index.html", html), ("docs/styles.css", css), ("README.md", readme)):
        for forbidden in FORBIDDEN_PUBLIC_TEXT:
            if forbidden in text:
                fail(f"forbidden public path marker {forbidden!r} in {label}")

    print("Demo verification passed")
    print(f"Checked {len(mp3_files)} MP3 files in docs/audio")
    print("Checked edit headings: " + ", ".join(REQUIRED_EDITS))
    print("Checked Matthieu Cervera upstream citation")


if __name__ == "__main__":
    main()
