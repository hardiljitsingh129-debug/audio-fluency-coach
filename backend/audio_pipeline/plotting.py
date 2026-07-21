from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict

def plot_timeline(y, sr, masks: Dict, events: Dict, title="Timeline"):
    """
    Plot waveform, 10 ms raw mask (shaded), and event overlays.
    """
    t = np.arange(len(y)) / sr
    plt.figure(figsize=(12, 4))
    plt.plot(t, y, color="#2c7fb8", linewidth=0.6, label="waveform")
    frame_s = masks["frame_ms"] / 1000.0
    for i, v in enumerate(masks["raw"]):
        if v == 1:
            s = i * frame_s; e = (i+1) * frame_s
            plt.axvspan(s, e, color="#78c679", alpha=0.15)
    for s, e in events.get("blocks", []):
        plt.axvspan(s, e, color="#e34a33", alpha=0.4, label="block")
    for s, e in events.get("prolongations", []):
        plt.axvspan(s, e, color="#2b8cbe", alpha=0.3, label="prolongation")
    for s, e in events.get("repetitions", []):
        plt.axvspan(s, e, color="#fecc5c", alpha=0.4, label="repetition")
    plt.xlabel("Time (s)"); plt.title(title); plt.tight_layout(); plt.show()
