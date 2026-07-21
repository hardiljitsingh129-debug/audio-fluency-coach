# Audio IO / Standardization
# -------------------------
from __future__ import annotations
import io as _io
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple # type: ignore[import]

class AudioIO:
    """
    Audio decode and standardization.
    - Decodes common formats via soundfile; falls back to librosa.load.
    - Resamples to target_sr and peak-normalizes to avoid clipping.
    """

    def __init__(self, target_sr: int = 16000, peak_norm: float = 0.95):
        self.target_sr = target_sr
        self.peak_norm = peak_norm

    def decode(self, data: bytes) -> Tuple[np.ndarray, int]:
        # Try soundfile, fallback to librosa
        try:
            y, sr = sf.read(_io.BytesIO(data), dtype="float32", always_2d=False)
        except Exception:
            y, sr = librosa.load(_io.BytesIO(data), sr=None, mono=True)
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        return y.astype(np.float32), sr

    def standardize(self, y: np.ndarray, sr: int) -> np.ndarray:
        # Resample to target_sr and peak-normalize
        if sr != self.target_sr:
            y = librosa.resample(y, orig_sr=sr, target_sr=self.target_sr)
        peak = float(np.max(np.abs(y)) + 1e-6)
        y = (self.peak_norm / peak) * y
        return y.astype(np.float32)