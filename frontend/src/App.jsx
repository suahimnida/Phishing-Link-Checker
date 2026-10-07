import { useState } from "react";
import Header from "./components/Header/Header";
import Home from "./pages/Home/Home";
import Analysis from "./pages/Analysis/Analysis";
import Result from "./pages/Result/Result";
import History from "./pages/History/History";
import DetectionMethods from "./pages/DetectionMethods/DetectionMethods";
import Dataset from "./pages/Dataset/Dataset";
import MLModel from "./pages/MLModel/MLModel";
import "./App.css";

function App() {
  const [currentPage, setCurrentPage] = useState("home");
  const [targetUrl, setTargetUrl] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  const handleAnalyze = (url, publicStatus) => {
    setTargetUrl(url);
    setIsPublic(publicStatus);
    setCurrentPage("analysis");
  };

  const handleAnalysisComplete = (result) => {
    setAnalysisResult(result);
    setCurrentPage("result");
  };

  const handleViewHistory = (result) => {
    setTargetUrl(result.url);
    setAnalysisResult(result);
    setCurrentPage("result");
  };

  return (
    <div className="app">
      <Header />

      <div className="layout">
        <aside className="sidebar">
          <div className="sidebar-section">
            <p className="sidebar-label">메인</p>

            <button
              className={`sidebar-item ${
                currentPage === "home" ? "active" : ""
              }`}
              onClick={() => setCurrentPage("home")}
            >
              <span>⌂</span>
              대시보드
            </button>

            <button
              className={`sidebar-item ${
                currentPage === "analysis" ? "active" : ""
              }`}
              onClick={() => setCurrentPage("analysis")}
            >
              <span>⌕</span>
              URL 분석
            </button>

            <button
              className={`sidebar-item ${
                currentPage === "history" ? "active" : ""
              }`}
              onClick={() => setCurrentPage("history")}
            >
              <span>◷</span>
              분석 기록
            </button>
          </div>

          <div className="sidebar-section">
            <p className="sidebar-label">프로젝트</p>

            <button
              className={`sidebar-item ${
                currentPage === "detection-methods"
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                setCurrentPage("detection-methods")
              }
            >
              <span>◈</span>
              탐지 방법
            </button>

            <button
              className={`sidebar-item ${
                currentPage === "dataset"
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                setCurrentPage("dataset")
              }
            >
              <span>◫</span>
              데이터셋
            </button>

            <button
              className={`sidebar-item ${
                currentPage === "ml-model"
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                setCurrentPage("ml-model")
              }
            >
              <span>◈</span>
              ML 모델
            </button>
          </div>
        </aside>

        <main className="main-content">
          {currentPage === "home" && (
            <Home
              onAnalyze={handleAnalyze}
              onOpenHistory={() =>
                setCurrentPage("history")
              }
            />
          )}

          {currentPage === "analysis" && (
            <Analysis
              url={targetUrl}
              isPublic={isPublic}
              onComplete={handleAnalysisComplete}
            />
          )}

          {currentPage === "result" && (
            <Result
              url={targetUrl}
              result={analysisResult}
            />
          )}

          {currentPage === "history" && (
            <History
              onViewResult={handleViewHistory}
            />
          )}

          {currentPage === "detection-methods" && (
            <DetectionMethods />
          )}

          {currentPage === "dataset" && <Dataset />}

          {currentPage === "ml-model" && <MLModel />}
        </main>
      </div>
    </div>
  );
}

export default App;