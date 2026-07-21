# Quality assessment
# -------------------------

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class QualityReport:
    clipping_rate: float
    snr_proxy_db: float
    duration_sec: float
    speech_ratio: Optional[float] = None


class QualityAssessor:
    def __init__(self, sr: int = 16000):
        self.sr = sr

    def compute(self, y: np.ndarray) -> QualityReport:
        clip = float(np.mean(np.abs(y) > 0.98))
        hop = int(self.sr * 0.02)  # 20 ms
        if len(y) <= hop:
            return QualityReport(clip, 0.0, len(y) / self.sr)
        frames = np.array([np.mean(y[i:i+hop]**2) for i in range(0, len(y)-hop, hop)])
        p5, p95 = np.percentile(frames, [5, 95])
        snr = float(10.0 * np.log10((p95 + 1e-8) / (p5 + 1e-8)))
        return QualityReport(clip, snr, len(y) / self.sr)


    def confidence(self, qr: QualityReport) -> str: 
        if qr.snr_proxy_db >= 20.0 and qr.clipping_rate <= 0.01 and (qr.speech_ratio is None or qr.speech_ratio >= 0.5): 
            return "high" 
        if qr.snr_proxy_db < 10.0 or qr.clipping_rate > 0.02 or (qr.speech_ratio is not None and qr.speech_ratio < 0.3): 
            return "low" 
        return "moderate"
