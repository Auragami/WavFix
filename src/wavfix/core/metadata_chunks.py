"""Metadata chunk policy helpers for conversion workflows."""

from __future__ import annotations

from .models import WavMetadata

_COMMON_METADATA_CHUNK_IDS: frozenset[str] = frozenset(
    {
        "LIST",
        "bext",
        "cue ",
        "smpl",
        "inst",
        "iXML",
        "axml",
        "cart",
        "DISP",
        "ID3 ",
        "id3 ",
        "JUNK",
        "PAD ",
    }
)


def is_common_metadata_chunk(chunk_id: str) -> bool:
    return chunk_id in _COMMON_METADATA_CHUNK_IDS


def unsupported_metadata_chunk_ids(metadata: WavMetadata) -> list[str]:
    unsupported: list[str] = []
    for chunk in metadata.chunks:
        if chunk.chunk_id in {"fmt ", "data"}:
            continue
        if not is_common_metadata_chunk(chunk.chunk_id):
            unsupported.append(chunk.chunk_id)
    return unsupported
