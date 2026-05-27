"""YouTube transcript loader using yt-dlp."""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

from doxa.schema import DoxaError, SourceRecord, normalize_ws


def _read_subtitle_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".json3":
        data = json.loads(text)
        events = data.get("events") or []
        parts: list[str] = []
        for event in events:
            for segment in event.get("segs") or []:
                if "utf8" in segment:
                    parts.append(segment["utf8"])
        return normalize_ws(" ".join(parts))
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("WEBVTT", "Kind:", "Language:")) or "-->" in stripped:
            continue
        lines.append(stripped)
    return normalize_ws(" ".join(lines))


def load_youtube(url: str) -> SourceRecord:
    try:
        import yt_dlp
    except ImportError as exc:
        raise DoxaError("YouTube ingestion requires the youtube extra: install doxa[youtube].") from exc
    with tempfile.TemporaryDirectory(prefix="doxa-youtube-") as tmp:
        outtmpl = str(Path(tmp) / "%(id)s.%(ext)s")
        opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "subtitlesformat": "json3/vtt/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        subtitle_files = sorted(Path(tmp).glob("*.*"))
        subtitle_text = ""
        for path in subtitle_files:
            if path.suffix in {".json3", ".vtt"}:
                subtitle_text = _read_subtitle_file(path)
                if subtitle_text:
                    break
        if not subtitle_text:
            raise DoxaError("No English subtitles or auto-captions were available for this YouTube URL.")
    source_id = "src_" + uuid.uuid5(uuid.NAMESPACE_URL, url).hex[:12]
    return SourceRecord(
        id=source_id,
        title=str(info.get("title") or url),
        author=str(info.get("uploader") or ""),
        date=str(info.get("upload_date") or ""),
        url=url,
        path=url,
        text=subtitle_text,
    )

