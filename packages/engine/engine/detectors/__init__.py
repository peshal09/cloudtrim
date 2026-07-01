"""Detector registry — one file per detector, each independently testable (§4)."""

from engine.detectors.base import DetectContext, Detector
from engine.detectors.registry import DETECTORS, run_detectors

__all__ = ["Detector", "DetectContext", "DETECTORS", "run_detectors"]
