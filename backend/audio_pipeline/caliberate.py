from __future__ import annotations
import numpy as np
from typing import Tuple

class Calibrator:
    """
    Probability calibration scaffold (isotonic default; Platt optional).
    Provides reliability_curve and expected_calibration_error utilities.
    """
    def __init__(self, method: str = "isotonic"):
        self.method = method
        self.model = None

    def fit(self, p_valid: np.ndarray, y_valid: np.ndarray):
        if self.method == "platt":
            from sklearn.linear_model import LogisticRegression
            lr = LogisticRegression(max_iter=1000)
            lr.fit(p_valid.reshape(-1, 1), y_valid)
            self.model = ("platt", lr)
        else:
            from sklearn.isotonic import IsotonicRegression
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(p_valid, y_valid)
            self.model = ("isotonic", iso)

    def predict(self, p: np.ndarray) -> np.ndarray:
        if self.model is None: return p
        name, mdl = self.model
        if name == "platt":
            return mdl.predict_proba(p.reshape(-1,1))[:,1]
        return mdl.predict(p)

    @staticmethod
    def reliability_curve(p: np.ndarray, y: np.ndarray, n_bins: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        bins = np.linspace(0,1,n_bins+1)
        idx = np.digitize(p, bins) - 1
        mp, mo = [], []
        for b in range(n_bins):
            m = (idx == b)
            if np.any(m):
                mp.append(float(np.mean(p[m]))); mo.append(float(np.mean(y[m])))
        return np.array(mp), np.array(mo)

    @staticmethod
    def expected_calibration_error(p: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
        bins = np.linspace(0,1,n_bins+1)
        idx = np.digitize(p, bins) - 1
        ece, n = 0.0, len(p)
        for b in range(n_bins):
            m = (idx == b)
            if np.any(m):
                w = float(np.mean(m))
                ece += w * float(abs(np.mean(p[m]) - np.mean(y[m])))
        return float(ece)
