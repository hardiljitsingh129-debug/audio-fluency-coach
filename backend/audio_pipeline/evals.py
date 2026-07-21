from __future__ import annotations
import numpy as np
from typing import List

class AgreementMetrics:
    """
    Basic agreement utilities for event detection:
    - cohen_kappa from TP/FP/FN/TN
    - count_mae for per-minute (or per-clip) count error
    """
    @staticmethod
    def cohen_kappa(tp: int, fp: int, fn: int, tn: int) -> float:
        n = tp + fp + fn + tn
        if n == 0: return 0.0
        po = (tp + tn) / n
        pe = ((tp + fp) / n) * ((tp + fn) / n) + ((fn + tn) / n) * ((fp + tn) / n)
        if pe >= 1.0: return 0.0
        return float((po - pe) / (1 - pe))

    @staticmethod
    def count_mae(pred_counts: List[int], ref_counts: List[int]) -> float:
        p = np.array(pred_counts); r = np.array(ref_counts)
        return float(np.mean(np.abs(p - r)))
