import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  Database,
  Download,
  FileSpreadsheet,
  Globe2,
  Grid3X3,
  LineChart,
  LockKeyhole,
  Radar,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Progress } from "./components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { getStatus, mockStatus, predictCsv, predictUrl } from "./lib/api";
import type { AppStatus, CsvPrediction, UrlPrediction } from "./lib/types";
import heroImg from "./assets/hero.png";

const featureCards = [
  {
    title: "URL Feature Extraction",
    description: "Turns a raw website URL into model-ready signals like IP usage, redirects, SSL state, and link behavior.",
    icon: Globe2,
  },
  {
    title: "ML Risk Classification",
    description: "Uses your trained phishing model to classify links as legitimate or suspicious in a portfolio-ready flow.",
    icon: BrainCircuit,
  },
  {
    title: "Gemini Explanation",
    description: "Summarizes the model decision in plain language so users understand what the detector noticed.",
    icon: Sparkles,
  },
];

const chartData = [
  { name: "Mon", phishing: 14, legitimate: 42 },
  { name: "Tue", phishing: 19, legitimate: 38 },
  { name: "Wed", phishing: 11, legitimate: 47 },
  { name: "Thu", phishing: 28, legitimate: 33 },
  { name: "Fri", phishing: 16, legitimate: 51 },
  { name: "Sat", phishing: 24, legitimate: 29 },
];

const signalColors = {
  suspicious: "#ef4444",
  neutral: "#f59e0b",
  normal: "#14b8a6",
};

function App() {
  const [status, setStatus] = useState<AppStatus>(mockStatus);
  const [url, setUrl] = useState("https://example.com/login");
  const [urlResult, setUrlResult] = useState<UrlPrediction | null>(null);
  const [csvResult, setCsvResult] = useState<CsvPrediction | null>(null);
  const [activeResult, setActiveResult] = useState<"empty" | "url" | "csv">("empty");
  const [history, setHistory] = useState<UrlPrediction[]>([]);
  const [isCheckingUrl, setIsCheckingUrl] = useState(false);
  const [isUploadingCsv, setIsUploadingCsv] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getStatus()
      .then(setStatus)
      .catch(() => setStatus(mockStatus));
  }, []);

  const signalData = urlResult
    ? [
        { name: "Suspicious", value: urlResult.signals.suspicious, color: signalColors.suspicious },
        { name: "Neutral", value: urlResult.signals.neutral, color: signalColors.neutral },
        { name: "Normal", value: urlResult.signals.normal, color: signalColors.normal },
      ]
    : [
        { name: "Suspicious", value: 8, color: signalColors.suspicious },
        { name: "Neutral", value: 5, color: signalColors.neutral },
        { name: "Normal", value: 17, color: signalColors.normal },
      ];

  async function handleUrlSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsCheckingUrl(true);
    try {
      const result = await predictUrl(url);
      setUrlResult(result);
      setActiveResult("url");
      setHistory((current) => [result, ...current.filter((item) => item.url !== result.url)].slice(0, 5));
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Unable to analyze this URL.");
    } finally {
      setIsCheckingUrl(false);
    }
  }

  async function handleCsvSubmit(event: React.FormEvent<HTMLFormElement>) {
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

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <LandingSection />
      <WorkflowSection
        csvResult={csvResult}
        activeResult={activeResult}
        error={error}
        isCheckingUrl={isCheckingUrl}
        isUploadingCsv={isUploadingCsv}
        onCsvSubmit={handleCsvSubmit}
        onUrlSubmit={handleUrlSubmit}
        setUrl={setUrl}
        url={url}
        urlResult={urlResult}
      />
      <DashboardSection history={history} signalData={signalData} status={status} urlResult={urlResult} />
      <FeatureSection />
      <Footer />
    </main>
  );
}

function LandingSection() {
  return (
    <section className="relative isolate overflow-hidden border-b border-white/10">
      <div className="absolute inset-0 bg-[linear-gradient(115deg,#0f172a_0%,#0f766e_52%,#1f2937_100%)]" />
      <img
        alt="Layered detection system visual"
        className="absolute right-4 top-16 hidden w-72 opacity-40 lg:block"
        src={heroImg}
      />
      <div className="relative mx-auto grid min-h-[620px] max-w-7xl items-center gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1fr_0.9fr] lg:px-8">
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className="max-w-3xl"
          initial={{ opacity: 0, y: 18 }}
          transition={{ duration: 0.55 }}
        >
          <Badge className="mb-6 border-teal-300/30 bg-teal-300/10 text-teal-100">
            <ShieldCheck className="h-3.5 w-3.5" />
            ML phishing intelligence
          </Badge>
          <h1 className="max-w-4xl text-balance text-5xl font-semibold leading-tight tracking-tight text-white sm:text-6xl lg:text-7xl">
            Network Security Console
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-200">
            A polished product interface for your phishing detection model: analyze a single URL, upload batch CSV data, and explain predictions with Gemini.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg">
              <a href="#analyze">
                Start analysis
                <ArrowRight className="h-4 w-4" />
              </a>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <a href="#dashboard">View dashboard</a>
            </Button>
          </div>
        </motion.div>

        <motion.div
          animate={{ opacity: 1, scale: 1 }}
          className="rounded-lg border border-white/15 bg-slate-900/75 p-4 shadow-2xl shadow-slate-950/60 backdrop-blur"
          initial={{ opacity: 0, scale: 0.96 }}
          transition={{ delay: 0.15, duration: 0.5 }}
        >
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <p className="text-sm text-slate-400">Live model verdict</p>
              <h2 className="mt-1 text-2xl font-semibold text-white">example.com/login</h2>
            </div>
            <Badge className="border-teal-300/30 bg-teal-300/10 text-teal-100">Legitimate</Badge>
          </div>
          <div className="grid gap-4 py-5 sm:grid-cols-3">
            <MiniStat label="Confidence" value="88%" />
            <MiniStat label="Signals" value="30" />
            <MiniStat label="Latency" value="1.4s" />
          </div>
          <div className="rounded-lg border border-white/10 bg-slate-950/70 p-4">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-sm text-slate-400">Risk activity</span>
              <Activity className="h-4 w-4 text-teal-300" />
            </div>
            <ResponsiveContainer height={190} width="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="legit" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.7} />
                    <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="phish" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.7} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis axisLine={false} dataKey="name" stroke="#94a3b8" tickLine={false} />
                <YAxis axisLine={false} stroke="#94a3b8" tickLine={false} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
                <Area dataKey="legitimate" fill="url(#legit)" stroke="#14b8a6" strokeWidth={2} />
                <Area dataKey="phishing" fill="url(#phish)" stroke="#ef4444" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

interface WorkflowSectionProps {
  activeResult: "empty" | "url" | "csv";
  csvResult: CsvPrediction | null;
  error: string;
  isCheckingUrl: boolean;
  isUploadingCsv: boolean;
  onCsvSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onUrlSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  setUrl: (value: string) => void;
  url: string;
  urlResult: UrlPrediction | null;
}

function WorkflowSection({
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
}: WorkflowSectionProps) {
  const resultTone = urlResult?.label === "Legitimate" ? "text-teal-300" : "text-red-300";
  const csvChartData = csvResult
    ? [
        { fill: "#ef4444", name: "Phishing", value: csvResult.phishing },
        { fill: "#14b8a6", name: "Legitimate", value: csvResult.legitimate },
      ]
    : [];
  const previewColumns = csvResult?.preview[0] ? buildCsvPreviewColumns(Object.keys(csvResult.preview[0])) : [];

  return (
    <section className="bg-slate-100 px-4 py-16 text-slate-950 sm:px-6 lg:px-8" id="analyze">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <Badge className="mb-3 border-slate-300 bg-white text-slate-700">
              <Zap className="h-3.5 w-3.5 text-teal-600" />
              Main workflow
            </Badge>
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Analyze URLs and data in one clean workflow</h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-600">
            The frontend connects to FastAPI JSON endpoints and still keeps loading, success, and error states designed.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <Card>
            <CardHeader>
              <CardTitle>Prediction input</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="url">
                <TabsList>
                  <TabsTrigger value="url">URL analysis</TabsTrigger>
                  <TabsTrigger value="csv">Batch CSV</TabsTrigger>
                </TabsList>
                <TabsContent value="url">
                  <form className="mt-5 space-y-4" onSubmit={onUrlSubmit}>
                    <div className="space-y-2">
                      <Label htmlFor="url">Website URL</Label>
                      <Input
                        id="url"
                        onChange={(event) => setUrl(event.target.value)}
                        placeholder="https://example.com/login"
                        required
                        type="url"
                        value={url}
                      />
                    </div>
                    <Button className="w-full sm:w-auto" disabled={isCheckingUrl} type="submit">
                      {isCheckingUrl ? "Analyzing..." : "Analyze URL"}
                      <Radar className="h-4 w-4" />
                    </Button>
                  </form>
                </TabsContent>
                <TabsContent value="csv">
                  <form className="mt-5 space-y-4" onSubmit={onCsvSubmit}>
                    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5">
                      <Label htmlFor="csvFile">Upload feature CSV</Label>
                      <Input className="mt-3" id="csvFile" name="csvFile" type="file" accept=".csv,text/csv" />
                      <p className="mt-3 text-sm text-slate-500">Use the same feature schema as the training dataset.</p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <Button disabled={isUploadingCsv} type="submit">
                        {isUploadingCsv ? "Processing..." : "Predict CSV"}
                        <FileSpreadsheet className="h-4 w-4" />
                      </Button>
                      <Button asChild variant="outline">
                        <a href="/sample-data">Download sample</a>
                      </Button>
                    </div>
                  </form>
                </TabsContent>
              </Tabs>
              {error ? <p className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
            </CardContent>
          </Card>

          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle>Result display</CardTitle>
            </CardHeader>
            <CardContent>
              {activeResult === "url" && urlResult ? (
                <div className="space-y-5">
                  <div className="flex flex-col justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-center">
                    <div>
                      <p className="text-sm text-slate-500">Model prediction</p>
                      <h3 className={`text-3xl font-semibold ${resultTone}`}>{urlResult.label}</h3>
                    </div>
                    <div className="w-full sm:w-56">
                      <div className="mb-2 flex justify-between text-sm text-slate-600">
                        <span>Confidence</span>
                        <span>{urlResult.confidence}%</span>
                      </div>
                      <Progress value={urlResult.confidence} />
                    </div>
                  </div>
                  <p className="rounded-lg border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600">{urlResult.summary}</p>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <MiniStatus icon={Database} label="DNS" value={urlResult.dnsStatus} />
                    <MiniStatus icon={Globe2} label="Page" value={urlResult.htmlStatus} />
                    <MiniStatus icon={LockKeyhole} label="Host" value={urlResult.hostname} />
                  </div>
                </div>
              ) : activeResult === "csv" && csvResult ? (
                <div className="space-y-5">
                  <div className="flex flex-col justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-center">
                    <div>
                      <p className="text-sm text-slate-500">Batch prediction completed</p>
                      <h3 className="text-2xl font-semibold text-slate-950">{csvResult.fileName}</h3>
                      <p className="mt-1 text-sm text-slate-500">{csvResult.outputMeta}</p>
                    </div>
                    <Button asChild variant="outline">
                      <a href="/download-output">
                        Download scored CSV
                        <Download className="h-4 w-4" />
                      </a>
                    </Button>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-4">
                    <MiniStatus icon={FileSpreadsheet} label="Rows" value={csvResult.rows.toLocaleString()} />
                    <MiniStatus icon={Grid3X3} label="Columns" value={csvResult.columns.toLocaleString()} />
                    <MiniStatus icon={ShieldAlert} label="Phishing" value={csvResult.phishing.toLocaleString()} />
                    <MiniStatus icon={ShieldCheck} label="Legitimate" value={csvResult.legitimate.toLocaleString()} />
                  </div>
                  <div className="grid gap-4 lg:grid-cols-[0.7fr_1.3fr]">
                    <div className="rounded-lg border border-slate-200 bg-white p-4">
                      <p className="mb-3 text-sm font-semibold text-slate-700">Prediction split</p>
                      <ResponsiveContainer height={190} width="100%">
                        <BarChart data={csvChartData}>
                          <XAxis dataKey="name" stroke="#64748b" tickLine={false} />
                          <YAxis allowDecimals={false} stroke="#64748b" tickLine={false} />
                          <Tooltip />
                          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                            {csvChartData.map((entry) => (
                              <Cell fill={entry.fill} key={entry.name} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                      <div className="border-b border-slate-200 px-4 py-3">
                        <p className="text-sm font-semibold text-slate-700">Preview with predicted column</p>
                        <p className="text-xs text-slate-500">Showing first {csvResult.preview.length} scored rows.</p>
                      </div>
                      <div className="max-h-64 overflow-auto">
                        <table className="w-full min-w-[620px] text-left text-xs">
                          <thead className="sticky top-0 bg-slate-50 text-slate-500">
                            <tr>
                              {previewColumns.map((column) => (
                                <th className="border-b border-slate-200 px-3 py-2 font-semibold" key={column}>
                                  {column}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {csvResult.preview.map((row, rowIndex) => (
                              <tr className="hover:bg-slate-50" key={`${csvResult.fileName}-${rowIndex}`}>
                                {previewColumns.map((column) => (
                                  <td className="border-b border-slate-100 px-3 py-2 text-slate-700" key={column}>
                                    {column === "predicted_column" ? (
                                      <Badge
                                        className={
                                          Number(row[column]) === 1
                                            ? "border-teal-200 bg-teal-50 text-teal-700"
                                            : "border-red-200 bg-red-50 text-red-700"
                                        }
                                      >
                                        {Number(row[column]) === 1 ? "Legitimate" : "Phishing"}
                                      </Badge>
                                    ) : (
                                      String(row[column])
                                    )}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="grid min-h-72 place-items-center rounded-lg border border-dashed border-slate-300 bg-slate-50 text-center">
                  <div className="max-w-sm p-6">
                    <LineChart className="mx-auto mb-4 h-10 w-10 text-teal-600" />
                    <h3 className="text-xl font-semibold">Results will appear here</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-500">Run a URL or CSV prediction to see status, confidence, and explainability output.</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}

function buildCsvPreviewColumns(columns: string[]) {
  const predictionColumns = columns.filter((column) => column === "predicted_column");
  const labelColumns = columns.filter((column) => column === "Result");
  const specialColumns = new Set<string>(["Result", "predicted_column"]);
  const featureColumns = columns.filter((column) => !specialColumns.has(column)).slice(0, 6);

  return [...featureColumns, ...labelColumns, ...predictionColumns];
}

interface DashboardSectionProps {
  history: UrlPrediction[];
  signalData: Array<{ color: string; name: string; value: number }>;
  status: AppStatus;
  urlResult: UrlPrediction | null;
}

function DashboardSection({ history, signalData, status, urlResult }: DashboardSectionProps) {
  const systemCards = [
    { label: "Model", value: status.model.status, meta: status.model.meta, icon: BrainCircuit },
    { label: "MongoDB", value: status.mongo.status, meta: "Data source", icon: Database },
    { label: "Gemini", value: status.gemini.status, meta: status.gemini.meta, icon: Sparkles },
    { label: "Output", value: status.output.status, meta: status.output.meta, icon: Download },
  ];

  return (
    <section className="bg-white px-4 py-16 text-slate-950 sm:px-6 lg:px-8" id="dashboard">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <Badge className="mb-3 border-teal-200 bg-teal-50 text-teal-800">
              <BarChart3 className="h-3.5 w-3.5" />
              Dashboard
            </Badge>
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Portfolio-ready monitoring view</h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-600">Status cards, signal distribution, and prediction history make the app feel complete without clutter.</p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {systemCards.map((card) => (
            <Card key={card.label}>
              <CardContent className="flex items-start justify-between gap-4 p-5">
                <div>
                  <p className="text-sm text-slate-500">{card.label}</p>
                  <h3 className="mt-1 text-xl font-semibold">{card.value}</h3>
                  <p className="mt-2 text-xs text-slate-500">{card.meta}</p>
                </div>
                <card.icon className="h-5 w-5 text-teal-600" />
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <Card>
            <CardHeader>
              <CardTitle>Signal distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer height={260} width="100%">
                <BarChart data={signalData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" stroke="#64748b" tickLine={false} />
                  <YAxis allowDecimals={false} stroke="#64748b" tickLine={false} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {signalData.map((entry) => (
                      <Cell fill={entry.color} key={entry.name} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent URL checks</CardTitle>
            </CardHeader>
            <CardContent>
              {history.length ? (
                <div className="space-y-3">
                  {history.map((item) => (
                    <div className="flex flex-col justify-between gap-3 rounded-lg border border-slate-200 p-4 sm:flex-row sm:items-center" key={item.url}>
                      <div>
                        <p className="font-medium">{item.hostname}</p>
                        <p className="max-w-md truncate text-sm text-slate-500">{item.url}</p>
                      </div>
                      <Badge className={item.label === "Legitimate" ? "border-teal-200 bg-teal-50 text-teal-700" : "border-red-200 bg-red-50 text-red-700"}>
                        {item.label}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid min-h-64 place-items-center rounded-lg border border-dashed border-slate-300 bg-slate-50 text-center">
                  <div className="max-w-sm p-6">
                    <CheckCircle2 className="mx-auto mb-4 h-10 w-10 text-slate-400" />
                    <h3 className="font-semibold">No predictions yet</h3>
                    <p className="mt-2 text-sm text-slate-500">Analyze a URL to populate this history.</p>
                  </div>
                </div>
              )}
              {urlResult ? <p className="mt-4 text-xs text-slate-500">Latest checked URL: {urlResult.finalUrl}</p> : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}

function FeatureSection() {
  return (
    <section className="bg-slate-100 px-4 py-16 text-slate-950 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 max-w-3xl">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Built for interviews, hackathons, and demos</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">The UI focuses on the ML story: what problem it solves, how the model is used, and how results can be understood.</p>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {featureCards.map((feature) => (
            <Card className="transition hover:-translate-y-1 hover:shadow-xl" key={feature.title}>
              <CardContent className="p-6">
                <feature.icon className="mb-5 h-9 w-9 text-teal-600" />
                <h3 className="text-xl font-semibold">{feature.title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">{feature.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

function MiniStatus({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <Icon className="mb-3 h-5 w-5 text-teal-600" />
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 truncate font-semibold">{value}</p>
    </div>
  );
}

function Footer() {
  return (
    <footer className="border-t border-white/10 bg-slate-950 px-4 py-8 text-slate-400 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col justify-between gap-4 text-sm sm:flex-row">
        <p>Network Security Console</p>
        <p>React, Tailwind, shadcn-style components, Framer Motion, and Recharts.</p>
      </div>
    </footer>
  );
}

export { App };
