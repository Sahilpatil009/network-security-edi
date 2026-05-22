import { Database } from "lucide-react";

import { HistoryList } from "../components/dashboard/HistoryList";
import { MiniMetric } from "../components/common/MiniMetric";
import { Badge } from "../components/ui/badge";
import type { UrlPrediction } from "../lib/types";

function HistoryPage({ history }: { history: UrlPrediction[] }) {
  const phishingCount = history.filter((item) => item.label === "Phishing").length;
  const legitimateCount = history.filter((item) => item.label === "Legitimate").length;
  const avgConfidence = history.length
    ? Math.round(history.reduce((total, item) => total + item.confidence, 0) / history.length)
    : 0;

  return (
    <main className="bg-[#f3f7f8] px-4 py-16 text-slate-950 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <Badge className="mb-3 border-slate-300 bg-white text-slate-700">
              <Database className="h-3.5 w-3.5 text-teal-600" />
              MongoDB history
            </Badge>
            <h1 className="text-3xl font-semibold sm:text-4xl">Saved URL predictions</h1>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-600">
            Every URL scan is saved in MongoDB with the verdict, confidence, timestamp, and suspicious feature names.
          </p>
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <MiniMetric label="Total saved" value={history.length.toLocaleString()} tone="neutral" />
          <MiniMetric label="Phishing saved" value={phishingCount.toLocaleString()} tone="danger" />
          <MiniMetric label="Avg confidence" value={history.length ? `${avgConfidence}%` : "No scans"} tone={legitimateCount >= phishingCount ? "good" : "danger"} />
        </div>

        <HistoryList history={history} variant="full" />
      </div>
    </main>
  );
}

export { HistoryPage };
