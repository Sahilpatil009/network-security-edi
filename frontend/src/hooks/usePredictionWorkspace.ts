import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { getPredictionHistory, getStatus, mockStatus, predictCsv, predictUrl } from "../lib/api";
import { signalColors } from "../lib/ui-data";
import type { AppStatus, CsvPrediction, UrlPrediction } from "../lib/types";

type ActiveResult = "empty" | "url" | "csv";

function usePredictionWorkspace() {
  const [status, setStatus] = useState<AppStatus>(mockStatus);
  const [url, setUrl] = useState("https://example.com/login");
  const [urlResult, setUrlResult] = useState<UrlPrediction | null>(null);
  const [csvResult, setCsvResult] = useState<CsvPrediction | null>(null);
  const [activeResult, setActiveResult] = useState<ActiveResult>("empty");
  const [history, setHistory] = useState<UrlPrediction[]>([]);
  const [isCheckingUrl, setIsCheckingUrl] = useState(false);
  const [isUploadingCsv, setIsUploadingCsv] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getStatus()
      .then(setStatus)
      .catch(() => setStatus(mockStatus));

    getPredictionHistory(20)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, []);

  const latestUrlResult = urlResult ?? history[0] ?? null;

  const signalData = useMemo(
    () =>
      latestUrlResult
        ? [
            { name: "Suspicious", value: latestUrlResult.signals.suspicious, color: signalColors.suspicious },
            { name: "Neutral", value: latestUrlResult.signals.neutral, color: signalColors.neutral },
            { name: "Normal", value: latestUrlResult.signals.normal, color: signalColors.normal },
          ]
        : [
            { name: "Suspicious", value: 8, color: signalColors.suspicious },
            { name: "Neutral", value: 5, color: signalColors.neutral },
            { name: "Normal", value: 17, color: signalColors.normal },
          ],
    [latestUrlResult],
  );

  async function handleUrlSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsCheckingUrl(true);
    try {
      const result = await predictUrl(url);
      setUrlResult(result);
      setActiveResult("url");
      setHistory((current) => [result, ...current].slice(0, 20));
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Unable to analyze this URL.");
    } finally {
      setIsCheckingUrl(false);
    }
  }

  async function handleCsvSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = event.currentTarget;
    const fileInput = form.elements.namedItem("csvFile") as HTMLInputElement;
    const file = fileInput.files?.[0];
    if (!file) {
      setError("Choose a CSV file before running batch prediction.");
      return;
    }

    setIsUploadingCsv(true);
    try {
      const result = await predictCsv(file);
      setCsvResult(result);
      setActiveResult("csv");
      form.reset();
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Unable to process the CSV.");
    } finally {
      setIsUploadingCsv(false);
    }
  }

  return {
    activeResult,
    csvResult,
    error,
    handleCsvSubmit,
    handleUrlSubmit,
    history,
    isCheckingUrl,
    isUploadingCsv,
    latestUrlResult,
    setUrl,
    signalData,
    status,
    url,
    urlResult,
  };
}

export { usePredictionWorkspace };
export type { ActiveResult };
