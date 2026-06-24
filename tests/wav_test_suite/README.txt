WavFix WAV Test Suite
=====================

This suite generates deterministic WAV fixtures and validates:
  - parser classification
  - decision outcomes
  - output planning behavior
  - processing behavior (with and without conversion)

Expected action labels in manifest.json:
  SHOULD_PASS
  SAFE_HEADER_FIX
  REQUIRES_CONVERSION
  REQUIRES_CONVERSION_OR_REJECT
  SHOULD_REJECT

Run:
  python tests/wav_test_suite/generate_wavs.py
  python tests/wav_test_suite/wav_test_suite.py
  python tests/wav_test_suite/wav_test_suite.py --regen
