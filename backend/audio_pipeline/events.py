from __future__ import annotations
from typing import List, Tuple
import numpy as np
import librosa

Seconds = float
Frames = int
Span = Tuple[Seconds, Seconds]

class EventDetectors:
    """
    Clinical-mode event detectors:
    - Blocks: 10–150 ms micro-silences from raw VAD mask
    - Prolongations: ≥300 ms low spectral flux (optionally steady F0)
    - Repetitions: local MFCC similarity within ~300 ms windows after onsets
    """
    def __init__(self, sr: int = 16000, frame_ms: int = 10):
        self.sr = sr
        self.frame_ms = frame_ms
        

    def detect_blocks(self, raw_mask: List[int], min_ms: int = 10, max_ms: int = 150) -> List[Span]:
        inv = [1 - x for x in raw_mask]
        spans = self._spans_from_mask(inv)
        blocks: List[Span] = []
        for s_f, e_f in spans:
            dur_ms = (e_f - s_f) * self.frame_ms
            if min_ms <= dur_ms <= max_ms:
                blocks.append((self._to_sec(s_f), self._to_sec(e_f)))
        return blocks

    def detect_prolongations(self, y: np.ndarray, speech_spans: List[Span],
                             min_ms: int = 300, flux_thresh: float = 3e-3,
                             f0_cv_max: float = 0.12) -> List[Span]:
        pros: List[Span] = []
        for s, e in speech_spans:
            dur_ms = (e - s) * 1000.0
            if dur_ms < min_ms: continue
            seg = y[int(s*self.sr):int(e*self.sr)]
            flux = self._spectral_flux(seg)
            if float(np.mean(flux)) < flux_thresh:
                f0, _, _ = librosa.pyin(seg, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"))
                keep = True
                if f0 is not None:
                    f0 = f0[~np.isnan(f0)]
                    if f0.size:
                        cv = float(np.std(f0) / (np.median(f0) + 1e-6))
                        keep = cv <= f0_cv_max
                if keep:
                    pros.append((s, e))
        return pros

    def detect_repetitions(self, y: np.ndarray, sr: int, onset_times: List[float],
                           win_ms: int = 150, gap_ms: int = 300, mfcc_bins: int = 13,
                           sim_thresh: float = 0.92, refractory_s: float = 0.25) -> List[Span]:
        reps: List[Span] = []
        win = int(sr * win_ms/1000); gap = int(sr * gap_ms/1000)
        for t in onset_times:
            c = int(t * sr)
            a = y[max(0, c-win):c]
            b = y[c:min(len(y), c+win)]
            if len(a) < win//2 or len(b) < win//2: continue
            mfcc_a = librosa.feature.mfcc(y=a, sr=sr, n_mfcc=mfcc_bins).mean(axis=1)
            mfcc_b = librosa.feature.mfcc(y=b, sr=sr, n_mfcc=mfcc_bins).mean(axis=1)
            cos = float(np.dot(mfcc_a, mfcc_b) / (np.linalg.norm(mfcc_a)*np.linalg.norm(mfcc_b) + 1e-8))
            if cos >= sim_thresh:
                reps.append((float(t), float(min(t + gap_ms/1000, len(y)/sr))))
        # refractory dedupe
        reps = self._dedupe_spans(reps, min_gap=refractory_s)
        return reps

    # helpers
    def _spectral_flux(self, y: np.ndarray, hop: int = 256, n_fft: int = 1024) -> np.ndarray:
        if y.size == 0: return np.array([0.0])
        S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop)) + 1e-8
        diff = np.diff(S, axis=1)
        flux = np.sqrt(np.sum(diff**2, axis=0)) / S.shape[0]
        return flux

    def _spans_from_mask(self, mask: List[int]) -> List[Tuple[int, int]]:
        spans: List[Tuple[int, int]] = []
        in_one = False; start = None
        for i, v in enumerate(mask):
            if v and not in_one:
                in_one = True; start = i
            elif not v and in_one:
                in_one = False; spans.append((start, i))
        if in_one and start is not None:
            spans.append((start, len(mask)))
        return spans

    def _dedupe_spans(self, spans: List[Span], min_gap: float) -> List[Span]:
        spans = sorted(spans)
        ded = []
        last_end = -1e9
        for s, e in spans:
            if s - last_end >= min_gap:
                ded.append((s, e)); last_end = e
            else:
                ps, pe = ded[-1]; ded[-1] = (ps, max(pe, e))
        return ded

    def _to_sec(self, frames: int) -> float:
        return frames * (self.frame_ms / 1000.0)
    
    # events.py additions — return raw score alongside each span

    def detect_repetitions_scored(self, y, sr, onset_times, win_ms=150, gap_ms=300,
                               mfcc_bins=13, sim_thresh=0.94, refractory_s=0.28):
        """Returns list of dicts: {start, end, raw_score} where raw_score = cosine similarity."""
        candidates = []
        win = int(sr * win_ms/1000); gap = int(sr * gap_ms/1000)
        for t in onset_times:
            c = int(t*sr); a = y[max(0,c-win):c]; b = y[c:min(len(y),c+win)]
            if len(a) < win//2 or len(b) < win//2: continue
            fa = librosa.feature.mfcc(y=a, sr=sr, n_mfcc=mfcc_bins).mean(axis=1)
            fb = librosa.feature.mfcc(y=b, sr=sr, n_mfcc=mfcc_bins).mean(axis=1)
            cos = float(np.dot(fa,fb)/(np.linalg.norm(fa)*np.linalg.norm(fb)+1e-8))
            if cos >= sim_thresh:  # widen recall net; calibration will re-rank
                candidates.append({"start": float(t), "end": float(min(t+gap_ms/1000, len(y)/sr)), "raw_score": cos})
        # dedupe on start proximity, keep highest-score in each cluster
        candidates.sort(key=lambda d: d["start"])
        deduped, last_end = [], -1e9
        for c in candidates:
            if c["start"] - last_end >= refractory_s:
                deduped.append(c); last_end = c["end"]
            elif c["raw_score"] > deduped[-1]["raw_score"]:
                deduped[-1] = c; last_end = c["end"]
        return deduped

    def detect_prolongations_scored(self, y, speech_spans, min_ms=300, flux_thresh=0.0035, f0_cv_max=0.12):
        """raw_score = inverse of flux (higher = more prolongation-like)."""
        candidates = []
        for s, e in speech_spans:
            if (e-s)*1000 < min_ms: continue
            seg = y[int(s*self.sr):int(e*self.sr)]
            flux = float(np.mean(self._spectral_flux(seg)))
            raw_score = float(np.clip(1.0 - (flux / (flux_thresh*2)), 0, 1))  # 1=very steady, 0=very changing
            candidates.append({"start": s, "end": e, "raw_score": raw_score, "flux": flux})
        return candidates

    def detect_blocks_scored(self, raw_mask, min_ms=10, max_ms=150):
        """raw_score based on how centrally the duration sits in the target band (140ms sweet spot)."""
        inv = [1-x for x in raw_mask]
        spans = self._spans_from_mask(inv)
        out = []
        for s_f, e_f in spans:
            dur_ms = (e_f - s_f) * self.frame_ms
            if min_ms <= dur_ms <= max_ms:
                # score peaks near 40-80ms (typical block duration), decays toward edges
                center = 60.0
                raw_score = float(np.exp(-((dur_ms - center) ** 2) / (2 * 40.0 ** 2)))
                out.append({"start": self._to_sec(s_f), "end": self._to_sec(e_f), "raw_score": raw_score, "duration_ms": dur_ms})
        return out

