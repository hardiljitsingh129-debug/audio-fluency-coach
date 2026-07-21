Audio Fluency — Clinical Mode Pipeline

- Install: pip install -r requirements.txt
- Run a file: python drivers/driver.py path/to/clip.wav --mode prolonged
- Run tests: pytest -q



Notes:
- Clinical mode uses 10 ms VAD frames with no gap merge for detection.
- Store raw audio only locally; default to features-only for privacy.
