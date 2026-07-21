# Synthetic ground truth generator (deterministic, so you can label = 1 for injected, 0 for spurious)
import matplotlib
import numpy as np
from vad import VoiceActivity
from rates import RateEstimator
from events import EventDetectors
import os
import pickle

def make_synthetic_clip(sr=16000, dur=6.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(sr*dur)) / sr
    
    # 1. Base signal: Mix multiple frequencies to simulate basic voice harmonics
    y = 0.1 * np.sin(2*np.pi*180*t) + 0.05 * np.sin(2*np.pi*360*t)
    
    # 2. Add realistic background ambient hum (White noise floor)
    y += rng.normal(0, 0.005, size=y.shape)
    y = y.astype(np.float32)
    
    injected = []

    # Inject blocks: change from absolute 0.0 to a realistic low-amplitude room-noise floor
    for start in [1.0, 3.5]:
        d = rng.uniform(0.03, 0.09)
        i = int(start*sr); n = int(d*sr)
        y[i:i+n] = rng.normal(0, 0.002, size=n)  # Realistic room silence
        injected.append(("block", start, start+d))

    # Inject repetitions: add slight random amplitude jitter to simulate natural human speech variations
    for start in [2.0, 4.5]:
        win = int(0.15*sr)
        i = int(start*sr)
        if i+2*win < len(y):
            y[i+win:i+2*win] = y[i:i+win] * rng.uniform(0.9, 1.1, size=win)
            injected.append(("repetition", start, start+0.3))

    # Inject prolongations: add micro-fluctuations in amplitude over time
    start = 5.0; d = 0.4
    i = int(start*sr); n = int(d*sr)
    if i+n < len(y):
        y[i:i+n] = (0.15 + 0.02 * np.sin(2*np.pi*5*t[i:i+n])) * np.sin(2*np.pi*180*t[i:i+n])
        injected.append(("prolongation", start, start+d))

    return y, sr, injected

"""
def make_synthetic_clip(sr=16000, dur=6.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(sr*dur)) / sr
    y = 0.2 * np.sin(2*np.pi*180*t).astype(np.float32)
    injected = []  # (type, start, end)

    # inject 2 blocks (true positives)
    for start in [1.0, 3.5]:
        d = rng.uniform(0.03, 0.09)
        i = int(start*sr); n = int(d*sr)
        y[i:i+n] = 0.0
        injected.append(("block", start, start+d))

    # inject 2 repeated windows (true positives)
    for start in [2.0, 4.5]:
        win = int(0.15*sr)
        i = int(start*sr)
        if i+2*win < len(y):
            y[i+win:i+2*win] = y[i:i+win]
            injected.append(("repetition", start, start+0.3))

    # inject 1 prolongation (true positive): flat, steady segment
    start = 5.0; d = 0.4
    i = int(start*sr); n = int(d*sr)
    if i+n < len(y):
        y[i:i+n] = 0.15 * np.sin(2*np.pi*180*t[i:i+n])
        injected.append(("prolongation", start, start+d))

    return y, sr, injected
"""

def label_candidates(candidates, injected, event_type, tol=0.05):
    """Assign 1 if candidate overlaps an injected event of the same type within tolerance, else 0."""
    labels = []
    truth = [(s,e) for (typ,s,e) in injected if typ == event_type]
    for c in candidates:
        hit = any(abs(c["start"] - s) <= tol or (c["start"] <= e and c["end"] >= s) for s,e in truth)
        labels.append(1 if hit else 0)
    return labels

sim_thresh_wide = 0.80  # deliberately wide net so calibration has both positive and negative examples

vad = VoiceActivity(sr=16000, frame_ms=10, mode=3)
rates = RateEstimator(sr=16000)
ev = EventDetectors(sr=16000, frame_ms=10)

all_raw, all_labels, all_type = [], [], []
for seed in range(20):  # 20 synthetic clips
    y, sr, injected = make_synthetic_clip(seed=seed)
    masks = vad.masks(y)
    spans = vad.spans_from_mask(masks.raw)
    onsets = rates.onsets(y)

    reps = ev.detect_repetitions_scored(y, sr, onsets, sim_thresh=sim_thresh_wide)
    pros = ev.detect_prolongations_scored(y, spans, flux_thresh=0.006)
    blks = ev.detect_blocks_scored(masks.raw)

    for c, lab in zip(reps, label_candidates(reps, injected, "repetition")):
        all_raw.append(c["raw_score"]); all_labels.append(lab); all_type.append("repetition")
    for c, lab in zip(pros, label_candidates(pros, injected, "prolongation")):
        all_raw.append(c["raw_score"]); all_labels.append(lab); all_type.append("prolongation")
    for c, lab in zip(blks, label_candidates(blks, injected, "block")):
        all_raw.append(c["raw_score"]); all_labels.append(lab); all_type.append("block")

import pandas as pd
df = pd.DataFrame({"raw_score": all_raw, "label": all_labels, "type": all_type})
print(df.groupby("type")["label"].agg(["count","mean"]))

from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import train_test_split
import numpy as np

calibrators = {}
metrics_before_after = {}

def brier(p, y): return float(np.mean((p - y) ** 2))

def ece(p, y, n_bins=10):
    bins = np.linspace(0, 1, n_bins+1)
    idx = np.digitize(p, bins) - 1
    e, n = 0.0, len(p)
    for b in range(n_bins):
        m = idx == b
        if np.any(m):
            e += (np.sum(m)/n) * abs(np.mean(p[m]) - np.mean(y[m]))
    return float(e)

for event_type in ["repetition", "prolongation", "block"]:
    sub = df[df["type"] == event_type]
    if sub["label"].nunique() < 2:
        continue  # need both classes present
    X = sub["raw_score"].values
    y = sub["label"].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(X_tr, y_tr)
    calibrators[event_type] = iso

    p_raw_test = X_te  # "raw" baseline = uncalibrated score treated as probability
    p_cal_test = iso.predict(X_te)

    metrics_before_after[event_type] = {
        "brier_raw": brier(p_raw_test, y_te), "brier_cal": brier(p_cal_test, y_te),
        "ece_raw": ece(p_raw_test, y_te), "ece_cal": ece(p_cal_test, y_te),
        "n_test": len(y_te)
    }

print(pd.DataFrame(metrics_before_after).T)

import matplotlib.pyplot as plt
matplotlib.use("Agg")  # for headless environments
import matplotlib.pyplot as plt

def reliability_points(p, y, n_bins=5):
    bins = np.linspace(0,1,n_bins+1); idx = np.digitize(p,bins)-1
    mp, mo = [], []
    for b in range(n_bins):
        m = idx==b
        if np.any(m):
            mp.append(np.mean(p[m])); mo.append(np.mean(y[m]))
    return np.array(mp), np.array(mo)

for event_type, iso in calibrators.items():
    sub = df[df["type"] == event_type]
    X, y = sub["raw_score"].values, sub["label"].values
    p_cal = iso.predict(X)

    fig, axes = plt.subplots(1, 2, figsize=(8,4))
    for ax, p, title in zip(axes, [X, p_cal], ["Raw score", "Calibrated"]):
        mp, mo = reliability_points(p, y)
        ax.plot([0,1],[0,1],"--",color="gray")
        ax.plot(mp, mo, "o-", color = "purple" if title=="Calibrated" else "crimson")
        ax.set_title(f"{event_type}: {title}")
        ax.set_xlabel("Predicted"); ax.set_ylabel("Observed")
    plt.tight_layout(); plt.show()
    plt.savefig(f"reliability_curve_{event_type}.png", dpi=150)
    plt.close(fig)

payload_to_serialize = {
    "models" : calibrators,
    "metrics" : metrics_before_after
}

models_dir = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(models_dir, exist_ok=True)

model_path = os.path.join(models_dir, "calibrators.pkl")
with open(model_path, "wb") as f:
    pickle.dump(payload_to_serialize, f)


