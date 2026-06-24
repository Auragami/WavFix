"""Public core API for WavFix."""

from .errors import OutputPlanningError, WavFixCoreError
from .inspection import inspect_file
from .models import (
    FileInspection,
    InputFileSpec,
    ProcessRequest,
    ProcessResult,
    ProgressEvent,
    RepairAction,
    WavFormatKind,
)
from .planning import OutputPlanContext, plan_output_path
from .processing import process_request
from .scanner import scan_input_specs, scan_inputs
from .wav_parser import parse_wav_file

__all__ = [
    "FileInspection",
    "InputFileSpec",
    "OutputPlanContext",
    "OutputPlanningError",
    "ProcessRequest",
    "ProcessResult",
    "ProgressEvent",
    "RepairAction",
    "WavFixCoreError",
    "WavFormatKind",
    "inspect_file",
    "parse_wav_file",
    "plan_output_path",
    "process_request",
    "scan_input_specs",
    "scan_inputs",
]
