import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { usePredictionWorkspace } from "./hooks/usePredictionWorkspace";

const AboutPage = lazy(() => import("./pages/AboutPage").then((module) => ({ default: module.AboutPage })));
const AnalyzePage = lazy(() => import("./pages/AnalyzePage").then((module) => ({ default: module.AnalyzePage })));
const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const HistoryPage = lazy(() => import("./pages/HistoryPage").then((module) => ({ default: module.HistoryPage })));
const HomePage = lazy(() => import("./pages/HomePage").then((module) => ({ default: module.HomePage })));
const ModelsPage = lazy(() => import("./pages/ModelsPage").then((module) => ({ default: module.ModelsPage })));

function App() {
  const workspace = usePredictionWorkspace();

  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<HomePage />} />
            <Route
              path="analyze"
              element={
                <AnalyzePage
                  activeResult={workspace.activeResult}
                  csvResult={workspace.csvResult}
                  error={workspace.error}
                  isCheckingUrl={workspace.isCheckingUrl}
                  isUploadingCsv={workspace.isUploadingCsv}
                  onCsvSubmit={workspace.handleCsvSubmit}
                  onUrlSubmit={workspace.handleUrlSubmit}
                  setUrl={workspace.setUrl}
                  url={workspace.url}
                  urlResult={workspace.urlResult}
                />
              }
            />
            <Route
              path="dashboard"
              element={
                <DashboardPage
                  history={workspace.history}
                  signalData={workspace.signalData}
                  status={workspace.status}
                  urlResult={workspace.latestUrlResult}
                />
              }
            />
            <Route path="history" element={<HistoryPage history={workspace.history} />} />
            <Route path="models" element={<ModelsPage report={workspace.modelComparison} />} />
            <Route path="about" element={<AboutPage />} />
            <Route path="*" element={<Navigate replace to="/" />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

function PageLoader() {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-950 text-sm text-slate-300">
      Loading console...
    </div>
  );
}

export { App };
