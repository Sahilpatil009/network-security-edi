interface StatusItem {
  meta: string;
  ready: boolean;
  status: string;
}

interface AppStatus {
  gemini: StatusItem;
  model: StatusItem;
  mongo: StatusItem;
  output: StatusItem;
  preprocessor: StatusItem;
  repo: {
    name: string;
    url: string;
  };
  sampleData: StatusItem;
}

interface UrlFeature {
  name: string;
  signal: "Suspicious" | "Neutral" | "Normal";
  value: number;
}

interface UrlPrediction {
  confidence: number;
  createdAt?: string;
  dnsStatus: string;
  features: UrlFeature[];
  finalUrl: string;
  historyId?: string;
  hostname: string;
  htmlStatus: string;
  label: "Legitimate" | "Phishing";
  prediction: number;
  signals: {
    neutral: number;
    normal: number;
    suspicious: number;
  };
  statusClass: "good" | "danger";
  summary: string;
  suspiciousFeatures?: string[];
  url: string;
}

interface CsvPrediction {
  columns: number;
  fileName: string;
  legitimate: number;
  outputMeta: string;
  phishing: number;
  preview: Array<Record<string, string | number>>;
  rows: number;
}

interface PredictionHistoryResponse {
  items: UrlPrediction[];
}

export type { AppStatus, CsvPrediction, PredictionHistoryResponse, UrlFeature, UrlPrediction };
