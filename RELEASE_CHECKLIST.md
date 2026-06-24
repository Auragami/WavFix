# WavFix 2.0 Final Release Checklist

Release date: `2026-06-24`.

This checklist assumes the macOS and Windows build artifacts have already been built. Do not rebuild unless a smoke test exposes a blocker.

## 1. Source And Docs Lock

- [ ] Confirm no intentional source changes remain unvalidated.
- [ ] Confirm release date is `2026-06-24` in README, CHANGELOG, release notes, package metadata, and User Guide.
- [ ] Confirm `version.txt`, `pyproject.toml`, `src/WavFix.spec`, `src/setup.py`, and app bundle metadata all say `2.0.0`.
- [ ] Confirm final `LICENSE` is included in both Mac and PC release packages.
- [ ] Confirm final `WavFix_User_Guide.pdf` is included in both Mac and PC release packages.
- [ ] Confirm `RELEASE_NOTES_v2.0.0.md` remains in the root release folder only, not inside the end-user install packages.
- [ ] Remove generated local noise: `__pycache__`, `.pyc`, `.DS_Store`, `.pytest_cache`, `.ruff_cache`, `.pyright`, and unintended build intermediates.

## 2. Quality Gate

Run once after the final source/doc lock:

```bash
make check
```

Equivalent commands if needed:

```bash
python3 -m ruff format --check src tests
python3 -m ruff check src tests
bash tools/typecheck.sh
python3 -m pytest -q
```

## 3. macOS Artifact Smoke

- [ ] Launch the built macOS artifact, not the source-tree app.
- [ ] Confirm logos, version text, Settings button, and theme colors display correctly.
- [ ] Confirm mixed file/folder picker works.
- [ ] Confirm drag-and-drop loads files and restores focus.
- [ ] Confirm file-name and Format/Process tooltips appear.
- [ ] Confirm single-click does not clear either viewer.
- [ ] Confirm double-click clears the input tree.
- [ ] Confirm double-click clears the output log.
- [ ] Confirm input row selection is visible and clears when clicking outside the input panel.
- [ ] Open Settings and confirm Theme, Performance, Update Alerts, Restore Notices, and Processing Options display correctly.
- [ ] Confirm Processing Options expand/collapse without window drift or clipping.
- [ ] Process a fixture set covering Pass, Repair, Convert, Skip/Error, and non-WAV pass-through.
- [ ] Confirm conversion warning, do-not-show-again behavior, and Restore Notices behavior.
- [ ] Confirm optional FFmpeg recommendation behavior only appears when FFmpeg is selected and unavailable.

## 4. Windows Artifact Smoke

- [ ] Launch the built Windows artifact (`build\WavFix.exe` for the PyInstaller build), not the source-tree app.
- [ ] Confirm executable uses `icons/icon.ico`.
- [ ] Confirm bundled logos and `version.txt` load correctly.
- [ ] Confirm `numpy`, `soundfile`, `soxr`, and SoundFile/libsndfile native dependencies are bundled.
- [ ] Launch without system FFmpeg installed and confirm built-in conversion works.
- [ ] Trigger conversion with FFmpeg disabled and confirm no FFmpeg recommendation appears.
- [ ] Enable FFmpeg in Settings while FFmpeg is unavailable and confirm the recommendation appears.
- [ ] Put FFmpeg on `PATH` or choose an executable and confirm the recommendation does not appear.
- [ ] Confirm file picker, drag-and-drop, tooltips, Settings, Restore Notices, and double-click clear behavior.
- [ ] Process a fixture set covering Pass, Repair, Convert, Skip/Error, and non-WAV pass-through.

## 5. Artifact Package Contents

For each platform package, confirm it includes:

- [ ] Built app/executable artifact (`.app` or `.exe` as applicable).
- [ ] `LICENSE`.
- [ ] `WavFix_User_Guide.pdf`.
- [ ] Any platform-specific install/readme note needed for users.

Keep these files in the root release folder, not inside the platform install packages:

- [ ] `RELEASE_NOTES_v2.0.0.md`.
- [ ] Checksum file, if created separately.
- [ ] `WavFix_v2.0.0_PC_BUILD_SOURCE.zip`, if archiving the Windows build source.

## 6. Checksums

- [ ] Zip each platform package before checksumming.
- [ ] Generate fresh checksums for every public release archive/file.
- [ ] Add checksums to release notes or a separate checksum file.
- [ ] Verify checksums against the packaged files after copying/uploading.

Do not run `shasum` directly on `WavFix.app`; it is a directory. Zip the containing platform package first, then checksum the `.zip`.

Suggested command on macOS/Linux:

```bash
cd "builds/Release v2.0"
ditto -c -k --keepParent "WavFix_v2.0.0_MAC" "WavFix_v2.0.0_MAC.zip"
zip -r "WavFix_v2.0.0_PC.zip" "WavFix_v2.0.0_PC"
shasum -a 256 "WavFix_v2.0.0_MAC.zip" "WavFix_v2.0.0_PC.zip"
```

Suggested command on Windows PowerShell:

```powershell
Get-FileHash .\WavFix_v2.0.0_PC.zip -Algorithm SHA256
```

## 7. GitHub Release

- [ ] Tag `v2.0.0`.
- [ ] Push release commit and tag.
- [ ] Draft GitHub release for `v2.0.0`.
- [ ] Attach macOS artifact/package.
- [ ] Attach Windows artifact/package.
- [ ] Attach checksums.
- [ ] Attach or include release notes.
- [ ] Verify public download links.
- [ ] Publish release.

## 8. Post-Publish Sanity

- [ ] Download the public macOS artifact and confirm it opens.
- [ ] Download the public Windows artifact and confirm it opens.
- [ ] Confirm README/release links point to the published assets.
- [ ] Send user/customer/social announcement only after public downloads are verified.
