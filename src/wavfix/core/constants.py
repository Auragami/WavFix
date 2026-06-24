"""Core constants used across the application."""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_EXTENSIONS = (
    ".aiff",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".raw",
    ".wav",
    ".jpg",
    ".jpeg",
    ".png",
    ".txt",
    ".pdf",
)

ACCEPTED_EXTENSIONS = set(SUPPORTED_EXTENSIONS)


@dataclass(frozen=True, slots=True)
class CompatibilityProfile:
    name: str
    supported_sample_rates: frozenset[int]
    preferred_sample_rate: int
    preferred_bit_depth: int
    allowed_channels: frozenset[int]


COMPATIBILITY_PROFILES: dict[str, CompatibilityProfile] = {
    "universal_pioneer_safe": CompatibilityProfile(
        name="universal_pioneer_safe",
        supported_sample_rates=frozenset({44100}),
        preferred_sample_rate=44100,
        preferred_bit_depth=24,
        allowed_channels=frozenset({2}),
    ),
    "preserve_supported_rate": CompatibilityProfile(
        name="preserve_supported_rate",
        supported_sample_rates=frozenset({44100, 48000, 88200, 96000}),
        preferred_sample_rate=44100,
        preferred_bit_depth=24,
        allowed_channels=frozenset({1, 2}),
    ),
}

SUPPORTED_PCM_BIT_DEPTHS = frozenset({16, 24})
