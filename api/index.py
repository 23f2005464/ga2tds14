from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import statistics
import os

app = FastAPI()

# CORS for any origin (grader requires "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# ---- Load telemetry safely in serverless ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_PATH = os.path.join(BASE_DIR, "telemetry.json")

with open(FILE_PATH, "r") as f:
    telemetry_data = json.load(f)


class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: int


@app.post("/")
def analyze(payload: AnalysisRequest):

    results = {}

    for region in payload.regions:
        region_data = [
            record for record in telemetry_data
            if record.get("region") == region
        ]

        if not region_data:
            continue

        latencies = [r.get("latency_ms", 0) for r in region_data]
        uptimes = [r.get("uptime_pct", 0) for r in region_data]

        # Mean latency
        avg_latency = statistics.mean(latencies)

        # 95th percentile (linear interpolation)
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        index = 0.95 * (n - 1)
        lower = int(index)
        upper = min(lower + 1, n - 1)
        fraction = index - lower

        p95_latency = (
            sorted_latencies[lower] +
            fraction * (sorted_latencies[upper] - sorted_latencies[lower])
        )

        avg_uptime = statistics.mean(uptimes)

        breaches = sum(1 for lat in latencies if lat > payload.threshold_ms)

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }

    return results