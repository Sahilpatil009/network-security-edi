import { Zap } from "lucide-react";
import type { FormEvent } from "react";

import { PredictionInput } from "../components/prediction/PredictionInput";
import { ResultPanel } from "../components/prediction/ResultPanel";
import { Badge } from "../components/ui/badge";
import type { ActiveResult } from "../hooks/usePredictionWorkspace";
import type { CsvPrediction, UrlPrediction } from "../lib/types";

interface AnalyzePageProps {
  activeResult: ActiveResult;
  csvResult: CsvPrediction | null;
  error: string;
  isCheckingUrl: boolean;
  isUploadingCsv: boolean;
  onCsvSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onUrlSubmit: (event: FormEvent<HTMLFormElement>) => void;
  setUrl: (value: string) => void;
  url: string;
  urlResult: UrlPrediction | null;
}

function AnalyzePage({
  activeResult,
  csvResult,
  error,
  isCheckingUrl,
  isUploadingCsv,
  onCsvSubmit,
  onUrlSubmit,
  setUrl,
  url,
  urlResult,
}: AnalyzePageProps) {
  return (
    <main className="bg-[#f3f7f8] px-4 py-16 text-slate-950 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <Badge className="mb-3 border-slate-300 bg-white text-slate-700">
              <Zap className="h-3.5 w-3.5 text-teal-600" />
              Main workflow
            </Badge>
            <h1 className="text-3xl font-semibold sm:text-4xl">Analyze URLs and data in one clean workflow</h1>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-600">
            Single-link checks and batch scoring share the same model experience: clear inputs, fast feedback, and downloadable results.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <PredictionInput
            error={error}
            isCheckingUrl={isCheckingUrl}
            isUploadingCsv={isUploadingCsv}
            onCsvSubmit={onCsvSubmit}
            onUrlSubmit={onUrlSubmit}
            setUrl={setUrl}
            url={url}
          />
          <ResultPanel activeResult={activeResult} csvResult={csvResult} urlResult={urlResult} />
        </div>
      </div>
    </main>
  );
}

export { AnalyzePage };
