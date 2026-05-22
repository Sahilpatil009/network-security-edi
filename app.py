import sys
import os
import json
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

import certifi
ca = certifi.where()

from dotenv import load_dotenv
load_dotenv()
mongo_db_url = os.getenv("MONGODB_URL_KEY")
print(mongo_db_url)
import pymongo
from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logging

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from uvicorn import run as app_run
import pandas as pd

from networksecurity.utils.main_utils.utils import load_object
from networksecurity.utils.ml_utils.model.estimator import NetworkModel
from networksecurity.utils.url_feature_extractor import extract_url_features


client = pymongo.MongoClient(mongo_db_url, tlsCAFile=ca)

from networksecurity.constants.training_pipeline import DATA_INGESTION_COLLECTION_NAME
from networksecurity.constants.training_pipeline import DATA_INGESTION_DATABASE_NAME
from networksecurity.constants.training_pipeline import TARGET_COLUMN

database = client[DATA_INGESTION_DATABASE_NAME]
collection = database[DATA_INGESTION_COLLECTION_NAME]

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
MODEL_PATH = BASE_DIR / "final_model" / "model.pkl"
PREPROCESSOR_PATH = BASE_DIR / "final_model" / "preprocessor.pkl"
PREDICTION_OUTPUT_PATH = BASE_DIR / "prediction_output" / "output.csv"
SAMPLE_DATA_PATH = BASE_DIR / "Network_Data" / "phisingData.csv"
DAGSHUB_REPO_OWNER = os.getenv("DAGSHUB_REPO_OWNER", "Sahilpatil009")
DAGSHUB_REPO_NAME = os.getenv("DAGSHUB_REPO_NAME", "network-security-edi")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def render_template(template_name: str, **context: str) -> HTMLResponse:
    template = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    for key, value in context.items():
        template = template.replace("{{ " + key + " }}", str(value))
    return HTMLResponse(content=template)


def file_meta(path: Path) -> str:
    if not path.exists():
        return "Not found"
    size_kb = path.stat().st_size / 1024
    modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d %b %Y, %I:%M %p")
    return f"{size_kb:,.0f} KB | {modified}"


def status_class(is_ready: bool) -> str:
    return "good" if is_ready else "warn"


def prediction_label(value: int) -> str:
    return "Legitimate" if int(value) == 1 else "Phishing"


def prediction_class(value: int) -> str:
    return "good" if int(value) == 1 else "danger"


def feature_rows(features: dict) -> str:
    rows = []
    for name, value in features.items():
        if value == -1:
            signal = "Suspicious"
            cls = "danger"
        elif value == 0:
            signal = "Neutral"
            cls = "warn"
        else:
            signal = "Normal"
            cls = "good"
        rows.append(
            "<tr>"
            f"<td>{escape(name)}</td>"
            f"<td>{value}</td>"
            f"<td><span class=\"badge {cls}\">{signal}</span></td>"
            "</tr>"
        )
    return "".join(rows)


def local_prediction_summary(url: str, label: str, features: dict) -> str:
    suspicious_features = [name for name, value in features.items() if value == -1]
    neutral_features = [name for name, value in features.items() if value == 0]
    if suspicious_features:
        reason = f"Suspicious signals include {', '.join(suspicious_features[:5])}."
    elif neutral_features:
        reason = f"Most URL signals look normal, with uncertain values for {', '.join(neutral_features[:4])}."
    else:
        reason = "Most extracted URL signals look normal."
    return (
        f"The model predicted this URL as {label}. {reason} "
        "Treat this as an ML-assisted check and manually verify the domain before sharing passwords or payment details."
    )


def explain_prediction_with_gemini(url: str, label: str, features: dict, metadata: dict) -> str:
    fallback = local_prediction_summary(url, label, features)
    if not GEMINI_API_KEY:
        return fallback

    suspicious_features = [name for name, value in features.items() if value == -1]
    neutral_features = [name for name, value in features.items() if value == 0]
    prompt = (
        "You are explaining a phishing URL detector result for a student project. "
        "Use plain language, keep it under 120 words, and do not claim certainty. "
        f"URL: {url}\n"
        f"Model prediction: {label}\n"
        f"Resolved host: {metadata.get('hostname')}\n"
        f"Page fetch status: {metadata.get('html_status')}\n"
        f"Suspicious feature names: {', '.join(suspicious_features) or 'none'}\n"
        f"Neutral or unknown feature names: {', '.join(neutral_features) or 'none'}\n"
        "Explain why the model may have made this prediction and give one practical safety step."
    )

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 220},
    }
    request = UrlRequest(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        parts = data["candidates"][0]["content"]["parts"]
        summary = " ".join(part.get("text", "") for part in parts).strip()
        if len(summary) < 80 or summary.lower().rstrip(". ").endswith(("because", "include", "with")):
            return fallback
        return summary
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as e:
        return f"{fallback} Gemini summary could not be generated: {str(e)}"


def predict_dataframe(input_df: pd.DataFrame):
    preprocessor = load_object(str(PREPROCESSOR_PATH))
    final_model = load_object(str(MODEL_PATH))
    network_model = NetworkModel(preprocessor=preprocessor, model=final_model)
    return network_model.predict(input_df)


@app.get("/", tags=["ui"])
async def index():
    model_ready = MODEL_PATH.exists() and PREPROCESSOR_PATH.exists()
    mongo_ready = bool(mongo_db_url)
    sample_ready = SAMPLE_DATA_PATH.exists()
    output_ready = PREDICTION_OUTPUT_PATH.exists()

    return render_template(
        "index.html",
        MODEL_STATUS="Ready" if model_ready else "Missing",
        MODEL_STATUS_CLASS=status_class(model_ready),
        MODEL_META=escape(file_meta(MODEL_PATH)),
        PREPROCESSOR_META=escape(file_meta(PREPROCESSOR_PATH)),
        MONGO_STATUS="Configured" if mongo_ready else "Missing",
        MONGO_STATUS_CLASS=status_class(mongo_ready),
        MONGO_META=escape(mongo_db_url or "Set MONGODB_URL_KEY in .env"),
        SAMPLE_STATUS="Available" if sample_ready else "Missing",
        SAMPLE_STATUS_CLASS=status_class(sample_ready),
        SAMPLE_META=escape(file_meta(SAMPLE_DATA_PATH)),
        OUTPUT_STATUS="Available" if output_ready else "No predictions yet",
        OUTPUT_STATUS_CLASS=status_class(output_ready),
        OUTPUT_META=escape(file_meta(PREDICTION_OUTPUT_PATH)),
        DAGSHUB_REPO=escape(f"{DAGSHUB_REPO_OWNER}/{DAGSHUB_REPO_NAME}"),
        DAGSHUB_URL=escape(f"https://dagshub.com/{DAGSHUB_REPO_OWNER}/{DAGSHUB_REPO_NAME}"),
        GEMINI_STATUS="Configured" if GEMINI_API_KEY else "Missing",
        GEMINI_STATUS_CLASS=status_class(bool(GEMINI_API_KEY)),
        GEMINI_META=escape(GEMINI_MODEL if GEMINI_API_KEY else "Set GEMINI_API_KEY in .env"),
    )

@app.get("/train")
async def train_route():
    try:
        from networksecurity.pipeline.training_pipeline import TrainingPipeline

        train_pipeline = TrainingPipeline()
        train_pipeline.run_pipeline()
        return render_template(
            "message.html",
            STATUS_CLASS="good",
            TITLE="Training completed",
            MESSAGE="The training pipeline finished successfully. New model artifacts are available for prediction.",
            DETAIL=escape(f"MLflow tracking repo: {DAGSHUB_REPO_OWNER}/{DAGSHUB_REPO_NAME}"),
            PRIMARY_ACTION="/",
            PRIMARY_LABEL="Back to dashboard",
            SECONDARY_ACTION="/docs",
            SECONDARY_LABEL="Open API docs",
        )
    except Exception as e:
        error = NetworkSecurityException(e, sys)
        return render_template(
            "message.html",
            STATUS_CLASS="danger",
            TITLE="Training failed",
            MESSAGE="The training pipeline could not finish.",
            DETAIL=escape(str(error)),
            PRIMARY_ACTION="/",
            PRIMARY_LABEL="Back to dashboard",
            SECONDARY_ACTION="/docs",
            SECONDARY_LABEL="Open API docs",
        )

@app.post("/predict")
async def predict_route(file: UploadFile = File(...)):
    try:
        df = pd.read_csv(file.file)
        input_df = df.drop(columns=[TARGET_COLUMN], errors="ignore")
        y_pred = predict_dataframe(input_df)
        df['predicted_column'] = y_pred

        PREDICTION_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(PREDICTION_OUTPUT_PATH, index=False)

        preview_df = df.head(200)
        table_html = preview_df.to_html(classes="data-table", index=False)
        predicted_counts = df["predicted_column"].value_counts().to_dict()
        phishing_count = int(predicted_counts.get(0, 0))
        legitimate_count = int(predicted_counts.get(1, 0))

        return render_template(
            "results.html",
            FILE_NAME=escape(file.filename or "Uploaded CSV"),
            ROW_COUNT=f"{len(df):,}",
            COLUMN_COUNT=f"{len(df.columns):,}",
            PHISHING_COUNT=f"{phishing_count:,}",
            LEGITIMATE_COUNT=f"{legitimate_count:,}",
            TABLE_HTML=table_html,
            PREVIEW_NOTE=escape(
                "Showing first 200 rows." if len(df) > 200 else "Showing all rows."
            ),
            OUTPUT_META=escape(file_meta(PREDICTION_OUTPUT_PATH)),
        )

    except Exception as e:
        error = NetworkSecurityException(e, sys)
        return render_template(
            "message.html",
            STATUS_CLASS="danger",
            TITLE="Prediction failed",
            MESSAGE="The CSV could not be processed.",
            DETAIL=escape(str(error)),
            PRIMARY_ACTION="/",
            PRIMARY_LABEL="Back to dashboard",
            SECONDARY_ACTION="/docs",
            SECONDARY_LABEL="Open API docs",
        )


@app.post("/predict-url")
async def predict_url_route(url: str = Form(...)):
    try:
        feature_df, features, metadata = extract_url_features(url)
        y_pred = predict_dataframe(feature_df)
        prediction = int(y_pred[0])
        label = prediction_label(prediction)
        summary = explain_prediction_with_gemini(
            metadata["normalized_url"],
            label,
            features,
            metadata,
        )

        return render_template(
            "url_result.html",
            URL=escape(metadata["normalized_url"]),
            FINAL_URL=escape(metadata["final_url"]),
            HOSTNAME=escape(metadata["hostname"]),
            DNS_STATUS=escape(metadata["dns_status"]),
            HTML_STATUS=escape(metadata["html_status"]),
            RESULT_LABEL=escape(label),
            RESULT_CLASS=prediction_class(prediction),
            RESULT_VALUE=str(prediction),
            GEMINI_SUMMARY=escape(summary),
            FEATURE_ROWS=feature_rows(features),
        )
    except Exception as e:
        error = NetworkSecurityException(e, sys)
        return render_template(
            "message.html",
            STATUS_CLASS="danger",
            TITLE="URL prediction failed",
            MESSAGE="The website URL could not be converted into model features.",
            DETAIL=escape(str(error)),
            PRIMARY_ACTION="/",
            PRIMARY_LABEL="Back to dashboard",
            SECONDARY_ACTION="/docs",
            SECONDARY_LABEL="Open API docs",
        )


@app.get("/download-output")
async def download_output():
    if not PREDICTION_OUTPUT_PATH.exists():
        return render_template(
            "message.html",
            STATUS_CLASS="warn",
            TITLE="No output file yet",
            MESSAGE="Run a prediction first to generate prediction_output/output.csv.",
            DETAIL="",
            PRIMARY_ACTION="/",
            PRIMARY_LABEL="Back to dashboard",
            SECONDARY_ACTION="/docs",
            SECONDARY_LABEL="Open API docs",
        )
    return FileResponse(
        PREDICTION_OUTPUT_PATH,
        media_type="text/csv",
        filename="network_security_predictions.csv",
    )


@app.get("/sample-data")
async def sample_data():
    return FileResponse(
        SAMPLE_DATA_PATH,
        media_type="text/csv",
        filename="phisingData.csv",
    )


if __name__ == "__main__":
    app_run(app, host="0.0.0.0", port=8000)
