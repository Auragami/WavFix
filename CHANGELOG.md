# Changelog

All notable changes to WavFix are documented here.

## [Unreleased]

### Planned

- Linux support
- Optional auto-install updater
- Optional waveform analysis pop-out
- Expanded file inspection details

## [2.0.0] - 2026-06-24

### Highlights

- Replaced legacy fixed-offset WAV mutation with a parser/classifier-driven processing engine.
- Introduced deterministic per-file actions: `PASS_THROUGH`, `HEADER_FIX`, `CONVERT`, `REJECT`.
- Added true multithreaded core processing for significantly faster batch throughput.
- Added strict safety guarantees that prevent fake compatibility rewrites.

### Added

- Format-safe RIFF/WAVE parser and classifier (PCM, float, extensible PCM/float, unsupported, malformed)
- Deterministic action pipeline per file: `PASS_THROUGH`, `HEADER_FIX`, `CONVERT`, `REJECT`
- Safe header-only normalization path for extensible PCM WAVs
- In-process conversion backend (`numpy + soundfile + soxr`) for float/incompatible WAVs with explicit conversion consent
- Conversion metadata policy (`best_effort` / `strict_preserve`) for preservation vs strict rejection control
- Optional FFmpeg conversion backend with explicit opt-in, source selection, and official free-download guidance when missing
- Update checker for GitHub Releases with download, remind-later, and skip-version actions
- Configurable compatibility profiles (`preserve_supported_rate`, `universal_pioneer_safe`)
- CLI safety controls: `--allow-conversion`, `--profile`, `--multichannel-policy`, `--metadata-policy`
- Post-write output validation for repaired/converted files
- Parser/decision/core/CLI regression tests for format-safe behavior
- New branding assets in app packaging/UI (header logos plus `icon.ico`/`icon.icns`)

### Changed

- Replaced fixed-offset WAV mutation with chunk-aware parsing and decisioned execution
- Core result reporting now includes action buckets for unchanged/header-fixed/converted/rejected
- Modular package architecture under `src/wavfix` is now the primary runtime path (GUI + CLI)
- Settings access is via dedicated `Settings` button; `By Auragami` remains static branding text
- Process-column semantics now align to runtime behavior:
  - Tree labels: `Pass` (green), `Repair` (yellow), `Convert` (orange), `Skip/Error` (red), non-WAV neutral (blue)
  - Output log: pass/header/convert action lines (green), warnings/reject/errors (red), neutral/info lines (blue), summary severity (green/orange/red)

### Fixed

- Prevented unsafe relabeling of float WAVs as PCM
- Removed legacy assumption that `wFormatTag` can be read/written via absolute bytes `20:21`
- Ensured extensible PCM header normalization only occurs when safe and parse-verified
- Eliminated UI-state coupling from worker execution paths by using primitive worker arguments

## [1.1.0] - 2023-04-26

### Added

- Color theme (dark/light mode) state saves between sessions in user config

### Fixed

- Theme toggle no longer re-reads WAV data for all loaded files, removing lag on large selections

### Known Bugs

- Main window (`ttk.Treeview`) scaling differs across DPI configurations

## [1.0.1] - 2023-04-25

### Fixed

- Minor improvement to `edit_wav_file` logic for export efficiency

### Known Bugs

- Main window (`ttk.Treeview`) scaling differs across DPI configurations

## [1.0.0] - 2023-04-22

### Added

- UI consistency improvements across platforms
- Minor structural improvements for export efficiency

### Fixed

- Fixed v0.2 regression where non-conflicting folders were still saved with `_clean`

### Known Bugs

- Main window (`ttk.Treeview`) scaling differs across DPI configurations

## [0.2] - 2023-04-07

### Added

- `.raw` support
- Interface improvements
- Light/Dark mode toggle via "By Auragami" text

### Changed

- Path handling adjustments for cross-platform consistency

## [0.1] - 2023-04-02

### Added

- Initial release
