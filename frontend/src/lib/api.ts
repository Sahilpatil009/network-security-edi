import type { AppStatus, CsvPrediction, ModelComparisonReport, PredictionHistoryResponse, UrlPrediction } from "./types";

const mockStatus: AppStatus = {
  gemini: { meta: "gemini-3.5-flash", ready: true, status: "Configured" },
  model: { meta: "1,655 KB | local artifact", ready: true, status: "Ready" },
  modelComparison: { meta: "Run training to generate report", ready: false, status: "Not generated" },
  mongo: { meta: "Local development connection", ready: true, status: "Configured" },
  output: { meta: "No predictions yet", ready: false, status: "Waiting" },
  preprocessor: { meta: "2,333 KB | local artifact", ready: true, status: "Ready" },
  repo: { name: "Sahilpatil009/network-security-edi", url: "https://dagshub.com/Sahilpatil009/network-security-edi" },
  sampleData: { meta: "Sample phishing feature CSV", ready: true, status: "Available" },
};

const mockModelComparison: ModelComparisonReport = {
  bestModelName: "",
  bestModelScore: 0,
  generatedAt: "",
  message: "Run model training to generate a model comparison report.",
  models: [],
  ready: false,
};

const mockPrediction: UrlPrediction = {
  confidence: 84,
  createdAt: new Date().toISOString(),
  dnsStatus: "Resolved",
  features: [
    { name: "having_IP_Address", signal: "Normal", value: 1 },
    { name: "URL_Length", signal: "Normal", value: 1 },
    { name: "Shortining_Service", signal: "Normal", value: 1 },
    { name: "SSLfinal_State", signal: "Normal", value: 1 },
    { name: "Page_Rank", signal: "Suspicious", value: -1 },
  ],
  finalUrl: "https://example.com/login",
  historyId: "mock-history-item",
  hostname: "example.com",
  htmlStatus: "Fetched",
  label: "Legitimate",
  prediction: 1,
  signals: { neutral: 4, normal: 22, suspicious: 4 },
  statusClass: "good",
  summary:
    "The model predicted this URL as Legitimate. Most structural signals look normal, but a few metadata checks remain uncertain, so verify the domain before sharing passwords.",
  url: "https://example.com/login",
};

async function parseJson<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T & { error?: string; message?: string };
  if (!response.ok || payload.error) {
    throw new Error(payload.message || payload.error || "Request failed.");
  }
  return payload;
}

async function getStatus(): Promise<AppStatus> {
  const response = await fetch("/api/status");
  return parseJson<AppStatus>(response);
}

async function getPredictionHistory(limit = 10): Promise<UrlPrediction[]> {
  const response = await fetch(`/api/prediction-history?limit=${limit}`);
  const payload = await parseJson<PredictionHistoryResponse>(response);
  return payload.items;
}

async function getModelComparison(): Promise<ModelComparisonReport> {
  const response = await fetch("/api/model-comparison");
  return parseJson<ModelComparisonReport>(response);
}

async function predictUrl(url: string): Promise<UrlPrediction> {
  const body = new FormData();
  body.append("url", url);
  const response = await fetch("/api/predict-url", {
    body,
    method: "POST",
  });
  return parseJson<UrlPrediction>(response);
}

async function predictCsv(file: File): Promise<CsvPrediction> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/predict-csv", {
    body,
    method: "POST",
  });
  return parseJson<CsvPrediction>(response);
}

export { getModelComparison, getPredictionHistory, getStatus, mockModelComparison, mockPrediction, mockStatus, predictCsv, predictUrl };
