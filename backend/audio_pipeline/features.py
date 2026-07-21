# Features (F0, energy, pauses)
# -------------------------

from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np
import librosa
Span = Tuple[float, float]

class FeatureExtractor:
    def __init__(self, sr: int = 16000):
        self.sr = sr

    def pause_stats(self, speech_spans: List[Span], total_dur: float) -> Dict[str, float]:
        pauses: List[float] = []
        last_end = 0.0
        for s, e in speech_spans:
            if s > last_end:
                pauses.append(float(s - last_end))
            last_end = float(e)
        if last_end < total_dur:
            pauses.append(float(total_dur - last_end))
        pr = float(np.sum(pauses) / max(total_dur, 1e-6))
        rate = float(len(pauses) / max(total_dur, 1e-6))
        mean_p = float(np.mean(pauses) if pauses else 0.0)
        long_share = float(np.mean([p > 0.7 for p in pauses]) if pauses else 0.0)
        return {"pause_ratio": pr, "pause_rate": rate, "mean_pause": mean_p, "long_pause_share": long_share}

    def f0_stats(self, y: np.ndarray, speech_spans: List[Span]) -> Dict[str, float]:
        vals = []
        for s, e in speech_spans:
            seg = y[int(s*self.sr):int(e*self.sr)]
            if seg.size == 0:
                continue
            f0, _, _ = librosa.pyin(seg,
                                    fmin=librosa.note_to_hz('C2'),
                                    fmax=librosa.note_to_hz('C7'))
            if f0 is None:
                continue
            f0 = f0[~np.isnan(f0)]
            if f0.size:
                vals.append(f0)
        if not vals:
            return {"f0_mean": 0.0, "f0_sd": 0.0, "f0_cv": 0.0}
        f0_all = np.concatenate(vals)
        mean = float(np.median(f0_all))
        sd = float(np.std(f0_all))
        cv = float(sd / (mean + 1e-6))
        cv = float(min(cv, 0.6))  # clamp outliers
        return {"f0_mean": mean, "f0_sd": sd, "f0_cv": cv}

    def energy_var(self, y: np.ndarray, speech_spans: List[Span]) -> float:
        rms_vals = []
        for s, e in speech_spans:
            seg = y[int(s*self.sr):int(e*self.sr)]
            if seg.size == 0:
                continue
            rms = librosa.feature.rms(y=seg, frame_length=1024, hop_length=512).flatten()
            if rms.size:
                rms_vals.append(rms)
        if not rms_vals:
            return 0.0
        return float(np.var(np.concatenate(rms_vals)))

    def extract(self, y: np.ndarray, speech_spans: List[Span], total_dur: float) -> Dict[str, float]:
        feats = {}
        feats.update(self.pause_stats(speech_spans, total_dur))
        feats.update(self.f0_stats(y, speech_spans))
        feats["rms_var"] = self.energy_var(y, speech_spans)
        feats["total_duration"] = float(total_dur)
        feats["voiced_duration"] = float(sum((e - s) for s, e in speech_spans))
        feats["speech_ratio"] = float(feats["voiced_duration"] / max(total_dur, 1e-6))
        return feats