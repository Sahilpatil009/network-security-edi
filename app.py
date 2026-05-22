import sys
import os
import json
from datetime import datetime, timezone
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


def create_mongo_client(uri: str):
    uri_lower = (uri or "").lower()
    uses_tls = uri_lower.startswith("mongodb+srv://") or "tls=true" in uri_lower or "ssl=true" in uri_lower
    if uses_tls:
        return pymongo.MongoClient(uri, tlsCAFile=ca)
    return pymongo.MongoClient(uri)


client = create_mongo_client(mongo_db_url)

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
MODEL_COMPARISON_JSON_PATH = BASE_DIR / "final_model" / "model_comparison.json"
MODEL_COMPARISON_CSV_PATH = BASE_DIR / "final_model" / "model_comparison.csv"
PREDICTION_OUTPUT_PATH = BASE_DIR / "prediction_output" / "output.csv"
SAMPLE_DATA_PATH = BASE_DIR / "Network_Data" / "phisingData.csv"
DAGSHUB_REPO_OWNER = os.getenv("DAGSHUB_REPO_OWNER", "Sahilpatil009")
DAGSHUB_REPO_NAME = os.getenv("DAGSHUB_REPO_NAME", "network-security-edi")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
URL_PREDICTION_COLLECTION_NAME = os.getenv("URL_PREDICTION_COLLECTION_NAME", "url_prediction_history")
url_prediction_collection = database[URL_PREDICTION_COLLECTION_NAME]
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


def build_url_prediction(url: str) -> dict:
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
    suspicious_count = sum(1 for value in features.values() if value == -1)
    neutral_count = sum(1 for value in features.values() if value == 0)
    normal_count = sum(1 for value in features.values() if value == 1)
    confidence = max(52, min(96, 86 - suspicious_count * 4 + normal_count))

    return {
        "url": metadata["normalized_url"],
        "finalUrl": metadata["final_url"],
        "hostname": metadata["hostname"],
        "dnsStatus": metadata["dns_status"],
        "htmlStatus": metadata["html_status"],
        "prediction": prediction,
        "label": label,
        "statusClass": prediction_class(prediction),
        "confidence": confidence,
        "summary": summary,
        "signals": {
            "suspicious": suspicious_count,
            "neutral": neutral_count,
            "normal": normal_count,
        },
        "features": [
            {
                "name": name,
                "value": value,
                "signal": "Suspicious" if value == -1 else "Neutral" if value == 0 else "Normal",
            }
            for name, value in features.items()
        ],
    }


def save_url_prediction(result: dict) -> dict:
    saved_at = datetime.now(timezone.utc)
    document = {
        "url": result["url"],
        "finalUrl": result["finalUrl"],
        "hostname": result["hostname"],
        "dnsStatus": result["dnsStatus"],
        "htmlStatus": result["htmlStatus"],
        "prediction": result["prediction"],
        "label": result["label"],
        "statusClass": result["statusClass"],
        "confidence": result["confidence"],
        "summary": result["summary"],
        "signals": result["signals"],
        "features": result["features"],
        "suspiciousFeatures": [
            feature["name"]
            for feature in result["features"]
            if feature["signal"] == "Suspicious"
        ],
        "createdAt": saved_at,
    }
    inserted = url_prediction_collection.insert_one(document)
    result["historyId"] = str(inserted.inserted_id)
    result["savedAt"] = saved_at.isoformat()
    return result


def serialize_url_prediction_history(document: dict) -> dict:
    created_at = document.get("createdAt")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()

    return {
        "historyId": str(document.get("_id", "")),
        "url": document.get("url", ""),
        "finalUrl": document.get("finalUrl", ""),
        "hostname": document.get("hostname", ""),
        "dnsStatus": document.get("dnsStatus", ""),
        "htmlStatus": document.get("htmlStatus", ""),
        "prediction": int(document.get("prediction", 0)),
        "label": document.get("label", "Phishing"),
        "statusClass": document.get("statusClass", "danger"),
        "confidence": int(document.get("confidence", 0)),
        "summary": document.get("summary", ""),
        "signals": document.get("signals", {"suspicious": 0, "neutral": 0, "normal": 0}),
        "features": document.get("features", []),
        "suspiciousFeatures": document.get("suspiciousFeatures", []),
        "createdAt": created_at or "",
    }


def get_url_prediction_history(limit: int = 10) -> list:
    safe_limit = max(1, min(limit, 50))
    documents = (
        url_prediction_collection
        .find()
        .sort("createdAt", pymongo.DESCENDING)
        .limit(safe_limit)
    )
    return [serialize_url_prediction_history(document) for document in documents]


def build_model_comparison_payload() -> dict:
    if not MODEL_COMPARISON_JSON_PATH.exists():
        return {
            "ready": False,
            "generatedAt": "",
            "bestModelName": "",
            "bestModelScore": 0,
            "models": [],
            "message": "Run model training to generate a model comparison report.",
        }

    with open(MODEL_COMPARISON_JSON_PATH, "r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)

    best_model = next((model for model in payload.get("models", []) if model.get("isBest")), None)
    payload["ready"] = True
    payload["bestModelName"] = payload.get("bestModelName") or (best_model or {}).get("modelName", "")
    payload["bestModelScore"] = payload.get("bestModelScore") or (best_model or {}).get("testF1", 0)
    payload["reportMeta"] = file_meta(MODEL_COMPARISON_CSV_PATH)
    return payload


def build_status_payload() -> dict:
    model_ready = MODEL_PATH.exists() and PREPROCESSOR_PATH.exists()
    mongo_ready = bool(mongo_db_url)
    sample_ready = SAMPLE_DATA_PATH.exists()
    output_ready = PREDICTION_OUTPUT_PATH.exists()
    model_comparison_ready = MODEL_COMPARISON_JSON_PATH.exists()
    return {
        "model": {
            "status": "Ready" if model_ready else "Missing",
            "ready": model_ready,
            "meta": file_meta(MODEL_PATH),
        },
        "preprocessor": {
            "status": "Ready" if PREPROCESSOR_PATH.exists() else "Missing",
            "ready": PREPROCESSOR_PATH.exists(),
            "meta": file_meta(PREPROCESSOR_PATH),
        },
        "mongo": {
            "status": "Configured" if mongo_ready else "Missing",
            "ready": mongo_ready,
            "meta": mongo_db_url or "Set MONGODB_URL_KEY in .env",
        },
        "sampleData": {
            "status": "Available" if sample_ready else "Missing",
            "ready": sample_ready,
            "meta": file_meta(SAMPLE_DATA_PATH),
        },
        "output": {
            "status": "Available" if output_ready else "No predictions yet",
            "ready": output_ready,
            "meta": file_meta(PREDICTION_OUTPUT_PATH),
        },
        "modelComparison": {
            "status": "Available" if model_comparison_ready else "Not generated",
            "ready": model_comparison_ready,
            "meta": file_meta(MODEL_COMPARISON_JSON_PATH),
        },
        "gemini": {
            "status": "Configured" if GEMINI_API_KEY else "Missing",
            "ready": bool(GEMINI_API_KEY),
            "meta": GEMINI_MODEL if GEMINI_API_KEY else "Set GEMINI_API_KEY in .env",
        },
        "repo": {
            "name": f"{DAGSHUB_REPO_OWNER}/{DAGSHUB_REPO_NAME}",
            "url": f"https://dagshub.com/{DAGSHUB_REPO_OWNER}/{DAGSHUB_REPO_NAME}",
        },
    }


@app.get("/", tags=["ui"])
async def index():
    status_payload = build_status_payload()

    return render_template(
        "index.html",
        MODEL_STATUS=status_payload["model"]["status"],
        MODEL_STATUS_CLASS=status_class(status_payload["model"]["ready"]),
        MODEL_META=escape(status_payload["model"]["meta"]),
        PREPROCESSOR_META=escape(status_payload["preprocessor"]["meta"]),
        MONGO_STATUS=status_payload["mongo"]["status"],
        MONGO_STATUS_CLASS=status_class(status_payload["mongo"]["ready"]),
        MONGO_META=escape(status_payload["mongo"]["meta"]),
        SAMPLE_STATUS=status_payload["sampleData"]["status"],
        SAMPLE_STATUS_CLASS=status_class(status_payload["sampleData"]["ready"]),
        SAMPLE_META=escape(status_payload["sampleData"]["meta"]),
        OUTPUT_STATUS=status_payload["output"]["status"],
        OUTPUT_STATUS_CLASS=status_class(status_payload["output"]["ready"]),
        OUTPUT_META=escape(status_payload["output"]["meta"]),
        DAGSHUB_REPO=escape(status_payload["repo"]["name"]),
        DAGSHUB_URL=escape(status_payload["repo"]["url"]),
        GEMINI_STATUS=status_payload["gemini"]["status"],
        GEMINI_STATUS_CLASS=status_class(status_payload["gemini"]["ready"]),
        GEMINI_META=escape(status_payload["gemini"]["meta"]),
    )


@app.get("/api/status")
async def api_status():
    return build_status_payload()


@app.get("/api/prediction-history")
async def api_prediction_history(limit: int = 10):
    try:
        return {"items": get_url_prediction_history(limit)}
    except Exception as e:
        error = NetworkSecurityException(e, sys)
        return {
            "error": str(error),
            "message": "Could not load URL prediction history from MongoDB.",
            "items": [],
        }


@app.get("/api/model-comparison")
async def api_model_comparison():
    try:
        return build_model_comparison_payload()
    except Exception as e:
        error = NetworkSecurityException(e, sys)
        return {
            "ready": False,
            "error": str(error),
            "message": "Could not load the model comparison report.",
            "models": [],
        }


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
        result = build_url_prediction(url)
        result = save_url_prediction(result)
        features = {feature["name"]: feature["value"] for feature in result["features"]}

        return render_template(
            "url_result.html",
            URL=escape(result["url"]),
            FINAL_URL=escape(result["finalUrl"]),
            HOSTNAME=escape(result["hostname"]),
            DNS_STATUS=escape(result["dnsStatus"]),
            HTML_STATUS=escape(result["htmlStatus"]),
            RESULT_LABEL=escape(result["label"]),
            RESULT_CLASS=result["statusClass"],
            RESULT_VALUE=str(result["prediction"]),
            GEMINI_SUMMARY=escape(result["summary"]),
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


@app.post("/api/predict-url")
async def api_predict_url(url: str = Form(...)):
    try:
        result = build_url_prediction(url)
        return save_url_prediction(result)
    except Exception as e:
        error = NetworkSecurityException(e, sys)
        return {
            "error": str(error),
            "message": "The website URL could not be converted into model features.",
        }


@app.post("/api/predict-csv")
async def api_predict_csv(file: UploadFile = File(...)):
    try:
        df = pd.read_csv(file.file)
        input_df = df.drop(columns=[TARGET_COLUMN], errors="ignore")
        y_pred = predict_dataframe(input_df)
        df["predicted_column"] = y_pred

        PREDICTION_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(PREDICTION_OUTPUT_PATH, index=False)

        predicted_counts = df["predicted_column"].value_counts().to_dict()
        preview = df.head(8).to_dict(orient="records")
        return {
            "fileName": file.filename or "Uploaded CSV",
            "rows": len(df),
            "columns": len(df.columns),
            "phishing": int(predicted_counts.get(0, 0)),
            "legitimate": int(predicted_counts.get(1, 0)),
            "outputMeta": file_meta(PREDICTION_OUTPUT_PATH),
            "preview": preview,
        }
    except Exception as e:
        error = NetworkSecurityException(e, sys)
        return {
            "error": str(error),
            "message": "The CSV could not be processed.",
        }


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
