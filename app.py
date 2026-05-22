import sys
import os
from datetime import datetime
from html import escape
from pathlib import Path

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
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from uvicorn import run as app_run
import pandas as pd

from networksecurity.utils.main_utils.utils import load_object
from networksecurity.utils.ml_utils.model.estimator import NetworkModel


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
        preprocessor = load_object(str(PREPROCESSOR_PATH))
        final_model = load_object(str(MODEL_PATH))
        network_model = NetworkModel(preprocessor=preprocessor, model=final_model)
        input_df = df.drop(columns=[TARGET_COLUMN], errors="ignore")
        y_pred = network_model.predict(input_df)
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
