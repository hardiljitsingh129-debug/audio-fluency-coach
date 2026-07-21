# Rates (syllable nuclei) and onsets
# -------------------------

from __future__ import annotations
from typing import List, Tuple
import numpy as np
import librosa
try:
    import parselmouth
except Exception:
    parselmouth = None
Seconds = float
Span = Tuple[Seconds, Seconds]

class RateEstimator:
    def __init__(self, sr: int = 16000):
        self.sr = sr
        self.parselmouth_ok = parselmouth is not None

    def syllable_nuclei(self, y: np.ndarray, speech_spans: List[Span]) -> List[Seconds]:
        if not self.parselmouth_ok:
            return []
        snd = parselmouth.Sound(y, self.sr)
        intensity = snd.to_intensity(time_step=0.01)  # 10 ms
        times = intensity.xs()
        vals = intensity.values.T.flatten()
        thr = float(np.median(vals) + 0.5 * np.std(vals))
        peaks = [times[i] for i in range(1, len(vals)-1)
                 if vals[i] > thr and vals[i] >= vals[i-1] and vals[i] >= vals[i+1]]
        # keep nuclei inside speech spans
        kept = []
        for t in peaks:
            if any(s <= t <= e for s, e in speech_spans):
                kept.append(float(t))
        return kept

    def articulation_rate(self, y: np.ndarray, speech_spans: List[Span]) -> float:
        voiced = float(sum((e - s) for s, e in speech_spans))
        if voiced <= 0:
            return 0.0
        nuclei = self.syllable_nuclei(y, speech_spans)
        if not nuclei:
            # fallback proxy: ~4 syll/s prior over voiced seconds
            return float(max(1.0, 4.0 * voiced) / voiced)
        return float(len(nuclei) / voiced)

    def onsets(self, y: np.ndarray, frame_len: int = 1024, hop: int = 256) -> List[Seconds]:
        # RMS derivative peaks as approximate onsets
        rms = librosa.feature.rms(y=y, frame_length=frame_len, hop_length=hop).flatten()
        dr = np.diff(rms, prepend=rms[:1])
        thr = np.percentile(dr, 95)
        peaks = np.where(dr >= thr)[0]
        times = librosa.frames_to_time(peaks, sr=self.sr, hop_length=hop)
        return [float(t) for t in times]