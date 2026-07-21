from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from pathlib import Path

from audio_pipeline.analyze import Analyzer, AnalysisConfig

app = FastAPI(title="Audio Fluency Coach", version="1.0")

app.add_middleware(
    CORSMiddleware,
    #allow_origins=["[localhost](http://localhost:5173)", "[localhost](http://localhost:8000)", "localhost"],
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ],  # Allow all origins for testing; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_dir = Path(__file__).resolve().parent.parent
calibrators_path = current_dir / "audio_pipeline" / "models" / "calibrators.pkl"

analyzer = Analyzer(
    sr=16000,
    frame_ms=10,
    config=AnalysisConfig(mode="assessment"),
    calibrators_path=str("audio_pipeline/models/calibrators.pkl"),
)

current_analyzer = Analyzer(
    sr=16000,
    frame_ms=10,
    config=AnalysisConfig(mode="assessment"),
)  # Global variable to hold the current analyzer instance


class AnalyzeResponse(BaseModel):
    api_version: str
    file: str
    index: float
    confidence: str
    quality: dict
    features: dict
    events: dict
    event_rates: dict
    targets: dict
    tips: list
    thresholds: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    mode: str = Query("assessment", enum=["assessment", "prolonged", "conversational"]),
):
    try:
        data = await file.read()

        current_analyzer = Analyzer(
            sr=16000,
            frame_ms=10,
            config=AnalysisConfig(mode=mode),
            calibrators_path=str(calibrators_path),
        )

        res = current_analyzer.analyze(data, filename=file.filename)

        response = AnalyzeResponse(
            api_version="v1",
            file=file.filename,
            index=res["index"],
            confidence=res["confidence"],
            quality=res["quality"],
            features=res["features"],
            events=res["events"],
            event_rates=res["event_rates"],
            targets=res["targets"],
            tips=res["tips"],
            thresholds=res["thresholds"],
        )

        print(f"Processed file: {file.filename}, Mode: {mode}, Index: {res['index']}, Confidence: {res['confidence']}")
        print(response)  # Print the response dictionary for debugging

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
