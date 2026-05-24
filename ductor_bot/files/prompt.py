"""Transport-agnostic media prompt building."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MediaInfo:
    """Metadata for a received media file (from any transport)."""

    caption: str | None
    file_name: str
    media_type: str
    original_type: str
    path: Path
    transcript: str | None = None
    transcript_method: str | None = None
    transcript_error: str | None = None


def build_media_prompt(
    info: MediaInfo,
    workspace: Path,
    *,
    transport: str = "",
) -> str:
    """Build the prompt injected into the orchestrator for a received file.

    Paths are relative to *workspace* so they work in both host and Docker.
    """
    rel_path: Path | str = info.path
    with contextlib.suppress(ValueError):
        rel_path = info.path.relative_to(workspace)

    via = f" via {transport}" if transport else ""
    lines = [
        "[INCOMING FILE]",
        f"The user sent you a file{via}.",
        f"Path: {rel_path}",
        f"Type: {info.media_type}",
        f"Original filename: {info.file_name}",
        "",
        "Check tools/media_tools/CLAUDE.md for file handling instructions.",
    ]

    if info.original_type in ("voice", "audio"):
        if info.transcript:
            lines.extend(
                [
                    "This is an audio/voice message and it was transcribed automatically.",
                    f"Transcription method: {info.transcript_method or 'unknown'}",
                    "",
                    "Transcript:",
                    info.transcript,
                    "",
                    "Respond to the transcript content. Only rerun transcription if the transcript looks clearly wrong.",
                ]
            )
        else:
            if info.transcript_error:
                lines.append(f"Automatic transcription failed: {info.transcript_error}")
            lines.append(
                "This is an audio/voice message. Use "
                f"tools/media_tools/transcribe_audio.py --file {rel_path} "
                "to transcribe it, then respond to the content. Check configured "
                "transcription.audio_command / DUCTOR_TRANSCRIBE_COMMAND before "
                "installing a new Whisper backend."
            )
    elif info.original_type in ("photo", "sticker") or info.media_type.startswith("image/"):
        lines.append(
            "This is an image. Inspect the attached image directly when available; "
            "otherwise use tools/media_tools/file_info.py for metadata. Respond to "
            "the user's caption/context, not just the file path."
        )
    elif info.original_type == "document":
        lines.append(
            "This is a document/file. Use tools/media_tools/read_document.py for "
            "text-like documents or tools/media_tools/file_info.py for metadata "
            "before responding."
        )

    if info.original_type in ("video", "video_note"):
        lines.append(
            "This is a video file. Use "
            f"tools/media_tools/process_video.py --file {rel_path} "
            "to extract keyframes and transcribe audio, then respond to the content."
        )

    if info.caption:
        lines.append("")
        lines.append(f"User message: {info.caption}")

    return "\n".join(lines)
