# VAD / Masks / Spans
# -------------------------

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
try:
    import webrtcvad
except Exception:
    webrtcvad = None
Seconds = float
Frames = int
Span = Tuple[Seconds, Seconds]

@dataclass
class Masks:
    raw: List[int]         # 10 ms raw speech/silence mask (no gap merge)
    smoothed: List[int]    # 50 ms smoothed mask for visualization (not for detection)
    frame_ms: int


class VoiceActivity:
    def __init__(self, sr: int = 16000, frame_ms: int = 10, mode: int = 3):
        assert frame_ms in (10, 20, 30), "webrtcvad requires 10/20/30 ms frames"
        self.sr = sr
        self.frame_ms = frame_ms
        self.mode = mode
        if webrtcvad is None:
            raise RuntimeError("webrtcvad not available. pip install webrtcvad")

    def masks(self, y: np.ndarray) -> Masks:
        vad = webrtcvad.Vad(self.mode)
        flen = int(self.sr * self.frame_ms / 1000)
        raw = []
        for i in range(0, len(y) - flen + 1, flen):
            frm = (y[i:i+flen] * 32767).astype(np.int16).tobytes()
            raw.append(1 if vad.is_speech(frm, self.sr) else 0)
        # 50 ms smoothing for visualization only
        k = max(1, int(50 / self.frame_ms))
        kernel = np.ones(k, dtype=float) / k
        sm = np.convolve(raw, kernel, mode="same")
        smoothed = (sm >= 0.5).astype(int).tolist()
        return Masks(raw=raw, smoothed=smoothed, frame_ms=self.frame_ms)

    def spans_from_mask(self, mask: List[int]) -> List[Span]:
        spans: List[Span] = []
        in_speech = False
        start_f: Optional[int] = None
        for i, v in enumerate(mask):
            if v and not in_speech:
                in_speech = True; start_f = i
            elif not v and in_speech:
                in_speech = False
                spans.append((self._to_sec(start_f), self._to_sec(i)))
        if in_speech and start_f is not None:
            spans.append((self._to_sec(start_f), self._to_sec(len(mask))))
        return spans

    def _to_sec(self, frame_index: int) -> Seconds:
        return frame_index * (self.frame_ms / 1000.0)