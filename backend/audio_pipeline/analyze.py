"""
analyze.py — Orchestrates the clinical‑mode audio analysis pipeline.

Responsibilities:
- Decode and standardize audio (mono, 16 kHz, peak normalize).
- Assess input quality and derive a confidence tier.
- Segment speech with 10 ms VAD (no gap-merge for detection).
- Extract interpretable features (prosody, pausing, articulation rate).
- Detect disfluency events (blocks, repetitions, prolongations).
- Normalize event counts per voiced minute and produce tips and a rule-based index.

Non-diagnostic: outputs are decision-support only.
"""

from __future__ import annotations

from dataclasses import dataclass
import pickle
from typing import Dict, Optional

import numpy as np

# Local modules (same package)
from .io import AudioIO
from .quality import QualityAssessor, QualityReport
from .vad import VoiceActivity
from .rates import RateEstimator
from .features import FeatureExtractor
from .events import EventDetectors


# -----------------------------
# Configuration dataclass
# -----------------------------

@dataclass
class AnalysisConfig:
    """
    Runtime configuration for analysis.

    Attributes:
        mode: Targeting context for coaching/monitoring.
              - "assessment": articulate 3.0–4.5 syll/s
              - "prolonged":  1.5–2.5 syll/s
              - "conversation": 2.5–4.0 syll/s
        articulation_targets: Optional override for articulation bands
                              per mode. Dict[mode] = (low, high).
    """
    mode: str = "assessment"
    articulation_targets: Optional[Dict[str, tuple[float, float]]] = None

    def __post_init__(self) -> None:
        if self.articulation_targets is None:
            self.articulation_targets = {
                "assessment": (3.0, 4.5),
                "prolonged": (1.5, 2.5),
                "conversation": (2.5, 4.0),
            }


# -----------------------------
# Analyzer — main orchestrator
# -----------------------------

class Analyzer:
    """
    High-level orchestrator for the clinical‑mode audio analysis.

    Pipeline:
      1) Decode + standardize
      2) Quality assessment (SNR/clipping/duration) → confidence tier
      3) 10 ms VAD masks (raw for detection; 50 ms smoothed for plotting)
      4) Features (pause, F0, RMS, articulation rate via syllable nuclei)
      5) Events:
         - Blocks: 10–150 ms micro‑silences (raw 10 ms mask)
         - Repetitions: MFCC cosine around onsets, refractory dedupe
         - Prolongations: ≥300 ms low spectral flux + steady F0
      6) Event normalization (per voiced minute)
      7) Rule‑based index (0–100) + mode‑aware numeric tips

    Notes:
      - This module purposefully contains only orchestration logic and a simple
        rule-based score. It is not a diagnostic model and performs no PII storage.
    """

    # Reasonable defaults for quiet-room speech; noisy-mode fallbacks can be passed at call-sites.
    _REPETITION_SIM_THRESH = 0.94
    _REPETITION_REFRACTORY_S = 0.28
    _PROLONG_MIN_MS = 300
    _PROLONG_FLUX_THRESH = 0.0035
    _PROLONG_F0_CV_MAX = 0.12

    def __init__(self, sr: int = 16000, frame_ms: int = 10, config: Optional[AnalysisConfig] = None, calibrators_path: str | None = None) -> None:
        # Core components
        self.sr = sr
        self.frame_ms = frame_ms
        self.config = config or AnalysisConfig()

        # Subsystems (single-responsibility classes)
        self.io = AudioIO(target_sr=sr)
        self.qc = QualityAssessor(sr=sr)
        self.vad = VoiceActivity(sr=sr, frame_ms=frame_ms, mode=3)  # clinical sensitivity
        self.rates = RateEstimator(sr=sr)
        self.feats = FeatureExtractor(sr=sr)
        self.events = EventDetectors(sr=sr, frame_ms=frame_ms)
        self.calibrators = {}
        if calibrators_path:
            try:
               with open(calibrators_path, "rb") as f:
                self.calibrators = pickle.load(f)
            except FileNotFoundError:               
                print(f"Warning: calibrators file not found at {calibrators_path}. Using raw scores.")
                self.calibrators = {}
            except Exception:
                print(f"Warning: Error occurred while loading calibrators from {calibrators_path}. Using raw scores.")
                self.calibrators = {}
    # --------------- Public API ---------------

    def _attach_confidence(self, spans_with_scores, event_type):
        iso = self.calibrators.get(event_type)
        out = []
        for c in spans_with_scores:
            raw = float(c.get("raw_score", 0.0))
            raw = max(0.0, min(1.0, raw))
            try:
                conf = float(iso.predict([raw])[0]) if iso else raw
            except Exception:
                conf = raw
            conf = max(0.0, min(1.0, conf))
            out.append({
                "start": float(c["start"]),
                "end": float(c["end"]),
                "confidence": round(conf, 3),
            })
        return out

    def analyze(self, data: bytes, filename: str = "input") -> Dict:
        """
        Run the full analysis pipeline for a given audio file (bytes).

        Parameters:
            data: Raw audio bytes (WAV/MP3/OGG/FLAC supported via soundfile/librosa).
            filename: Original name for reporting.

        Returns:
            Dict with: file, index, confidence, quality, features, events, event_rates,
            masks (preview only), targets, tips.

        Raises:
            ValueError: When input is too short or contains insufficient speech.
            RuntimeError: If a hard dependency fails (rare).
        """
        # 1) Decode + standardize
        y_raw, sr_in = self.io.decode(data)
        y = self.io.standardize(y_raw, sr_in)

        # 2) Quality pre-check (before VAD-derived metrics)
        qr: QualityReport = self.qc.compute(y)

        # 3) 10 ms VAD masks (raw for detection; 50 ms smoothed for visualization only)
        masks = self.vad.masks(y)
        speech_spans = self.vad.spans_from_mask(masks.raw)
        qr.speech_ratio = float(sum((e - s) for s, e in speech_spans) / max(qr.duration_sec, 1e-6))
        confidence = self.qc.confidence(qr)

        # Guard rails: prevent over-interpretation on poor inputs
        if qr.duration_sec < 5.0:
            raise ValueError("Clip too short (<5 s). Please record a longer sample.")
        if qr.speech_ratio < 0.20:
            raise ValueError("Insufficient speech detected. Record longer or reduce background noise.")

        # 4) Features (interpretable prosody/pacing)
        features = self.feats.extract(y, speech_spans, qr.duration_sec)
        features["articulation_rate"] = float(self.rates.articulation_rate(y, speech_spans))
        # Optional: add more per-frame traces in future; keep features clip-level for API stability

        # 5) Event detection
        # 5a) Onsets for repetition windows
        onsets = self.rates.onsets(y)

        # 5b) Blocks: micro-silences (10–150 ms) from raw 10 ms mask
        block_spans = self.events.detect_blocks_scored(masks.raw, min_ms=10, max_ms=150)

        # 5c) Repetitions: MFCC cosine around onsets + refractory dedupe
        repetition_spans = self.events.detect_repetitions_scored(
            y,
            sr=self.sr,
            onset_times=onsets,
            win_ms=150,
            gap_ms=300,
            mfcc_bins=13,
            sim_thresh=self._REPETITION_SIM_THRESH,
            refractory_s=self._REPETITION_REFRACTORY_S,
        )

        # 5d) Prolongations: ≥300 ms low spectral flux + steady F0
        prolong_spans = self.events.detect_prolongations_scored(
            y,
            speech_spans=speech_spans,
            min_ms=self._PROLONG_MIN_MS,
            flux_thresh=self._PROLONG_FLUX_THRESH,
            f0_cv_max=self._PROLONG_F0_CV_MAX,
        )

        # 6) Normalize event counts per voiced minute
        voiced_min = max(1e-6, features["voiced_duration"] / 60.0)
        event_rates = {
            "blocks_per_min": round(len(block_spans) / voiced_min, 2),
            "repetitions_per_min": round(len(repetition_spans) / voiced_min, 2),
            "prolongations_per_min": round(len(prolong_spans) / voiced_min, 2),
        }

        # 7) Rule-based index and tips (mode-aware targets)
        a_lo, a_hi = self._articulation_band(self.config.mode)
        index = self._rule_index(features, a_lo, a_hi)
        tips = self._tips(features, a_lo, a_hi)

        block_spans = self._attach_confidence(self.events.detect_blocks_scored(masks.raw, min_ms=10, max_ms=150), "block")
        repetition_spans = self._attach_confidence(self.events.detect_repetitions_scored(
                y, 
                self.sr, 
                onsets,
                sim_thresh=self._REPETITION_SIM_THRESH, refractory_s=self._REPETITION_REFRACTORY_S
            ),
            "repetition"
        )
        prolong_spans = self._attach_confidence(self.events.detect_prolongations_scored(
                y, 
                speech_spans,
                min_ms=self._PROLONG_MIN_MS, flux_thresh=self._PROLONG_FLUX_THRESH
            ),
            "prolongation"
        )


        # Assemble response (keep stable for frontend)
        return {
            "file": filename,
            "index": float(index),
            "confidence": confidence,
            "quality": {
                "clipping_rate": qr.clipping_rate,
                "snr_proxy_db": qr.snr_proxy_db,
                "duration_sec": qr.duration_sec,
                "speech_ratio": qr.speech_ratio,
            },
            "features": features,  # clip-level interpretable metrics
            # "events": {
            #    "blocks": block_spans,
            #    "repetitions": repetition_spans,
            #    "prolongations": prolong_spans,
            #},
            "events": {
                "blocks": self._attach_confidence(block_spans, "block"),
                "repetitions": self._attach_confidence(repetition_spans, "repetition"),
                "prolongations": self._attach_confidence(prolong_spans, "prolongation"),
            },
            "event_rates": event_rates,
            # Preview masks — for timeline shading only (do NOT persist long arrays)
            "masks": {
                "raw": masks.raw[:1000],         # truncate for transport
                "smoothed": masks.smoothed[:1000],
                "frame_ms": masks.frame_ms,
            },
            "targets": {"articulation_rate": [a_lo, a_hi], "mode": self.config.mode},
            "tips": tips,
            "thresholds": {
                "sim_thresh": self._REPETITION_SIM_THRESH,
                "refractory_s": self._REPETITION_REFRACTORY_S,
                "flux_thresh": self._PROLONG_FLUX_THRESH,
                "f0_cv_max": self._PROLONG_F0_CV_MAX,
                "min_ms": self._PROLONG_MIN_MS,
            }
        }

    # --------------- Private helpers ---------------

    def _articulation_band(self, mode: str) -> tuple[float, float]:
        """Return (low, high) articulation‑rate target for the chosen mode."""
        return self.config.articulation_targets.get(mode, (3.0, 4.5))

    def _rule_index(self, feats: Dict[str, float], a_lo: float, a_hi: float) -> float:
        """
        Weighted distance-to-target score (0–100).
        Non-diagnostic: summarizes pacing/pausing/pitch stability against mode-aware bands.
        """
        weights = {
            "articulation_rate": 0.35,
            "pause_ratio": 0.35,
            "long_pause_share": 0.10,
            "f0_cv": 0.15,
            "rms_var": 0.05,
        }
        bands = {
            "articulation_rate": (a_lo, a_hi),
            "pause_ratio": (0.07, 0.10),
            "long_pause_share": (0.0, 0.20),
            "f0_cv": (0.05, 0.20),
            "rms_var": (0.0, None),  # lower is better; no explicit upper bound
        }

        def z_to_band(value: float, lo: float, hi: Optional[float]) -> float:
            if hi is None:  # lower is better
                ref = lo if lo is not None else 0.0
                return max(0.0, (value - ref) / max(abs(ref) + 1e-6, 1.0))
            mid = 0.5 * (lo + hi)
            span = 0.5 * (hi - lo)
            return abs((value - mid) / max(span, 1e-6))

        score = 100.0
        for k, w in weights.items():
            if k in feats and k in bands:
                z = z_to_band(float(feats[k]), bands[k][0], bands[k][1])
                score -= w * 20.0 * min(z, 2.0)  # cap penalty to avoid runaways
        return float(np.clip(score, 0, 100))

    def _tips(self, feats: Dict[str, float], a_lo: float, a_hi: float) -> list[Dict[str, str]]:
        """Produce up to three short, numeric, actionable coaching tips."""
        tips: list[Dict[str, str]] = []

        ar = feats.get("articulation_rate", 0.0)
        if ar < a_lo:
            tips.append({
                "title": "Increase articulation rate",
                "detail": f"{ar:.1f} syll/s vs {a_lo:.1f}–{a_hi:.1f} target. Use shorter clauses and steady pacing."
            })
        elif ar > a_hi:
            tips.append({
                "title": "Slow down slightly",
                "detail": f"{ar:.1f} syll/s vs {a_lo:.1f}–{a_hi:.1f} target. Add brief phrase‑final micro‑pauses."
            })

        pr = feats.get("pause_ratio", 0.0)
        if pr > 0.10:
            tips.append({
                "title": "Shorten long pauses",
                "detail": f"Pause ratio {(pr*100):.0f}% vs 7–10% target. Plan micro‑pauses at sentence ends."
            })

        cv = feats.get("f0_cv", 0.0)
        if cv > 0.20:
            tips.append({
                "title": "Stabilize intonation",
                "detail": f"F0 variability CV={cv:.2f} vs 0.05–0.20 target. Aim for steadier tone on key points."
            })

        return tips[:3]
