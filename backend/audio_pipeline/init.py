"""
audio_pipeline: Clinical-mode audio analysis for fluency decision-support.

Modules:
- io: audio decode and standardization
- quality: input quality assessment and confidence cue
- vad: WebRTC VAD masks and span building (10 ms raw mask; smoothed for viz)
- rates: syllable nuclei (Parselmouth) articulation rate; onset estimation
- features: pause/F0/energy features
- events: blocks (micro-silences), prolongations (low spectral flux), repetitions (local self-similarity)
- calibrate: probability calibration scaffolds and reliability metrics
- evals: agreement/count-error utilities
- analyze: Analyzer orchestrating the pipeline
- plotting: timeline and feature plots for debugging/reports
"""
from .analyze import AnalysisConfig, Analyzer
