import { useEffect, useState } from "react";
import Header from "./components/Header/Header";
import Home from "./pages/Home/Home";
import Analysis from "./pages/Analysis/Analysis";
import Result from "./pages/Result/Result";
import History from "./pages/History/History";
import DetectionMethods from "./pages/DetectionMethods/DetectionMethods";
import Dataset from "./pages/Dataset/Dataset";
import MLModel from "./pages/MLModel/MLModel";
import { getAnalysis, getSharedAnalysis, wakeServer } from "./services/api";
import "./App.css";

function App() {
  const [currentPage, setCurrentPage] = useState("home");
  const [targetUrl, setTargetUrl] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [owner, setOwner] = useState({ name: null, secret: null });
  const [analysisResult, setAnalysisResult] = useState(null);
  // 공유 링크(?share=토큰)로 들어온 경우의 토큰. 리포트를 볼 때도 함께 보낸다
  const [shareToken, setShareToken] = useState(null);
  const [shareError, setShareError] = useState("");
  // 분석 결과를 삭제한 뒤 분석 기록 화면에 보여 줄 안내
  const [historyNotice, setHistoryNotice] = useState("");
  const [historyTab, setHistoryTab] = useState("mine");
  // 사이드바 'URL 분석'을 누를 때마다 1씩 올려 홈의 URL 입력칸에 포커스를 준다
  const [focusRequest, setFocusRequest] = useState(0);

  // 사이드바 'URL 분석': 분석 화면을 바로 열지 않는다.
  // 예전에는 직전 URL(또는 빈 값)로 분석을 다시 실행해 빈 요청이 나가거나 기록이 중복 저장됐다 (QA)
  const openUrlInput = () => {
    setCurrentPage("home");
    setFocusRequest((n) => n + 1);
  };

  const handleDeleted = () => {
    setAnalysisResult(null);
    setHistoryNotice("분석 결과를 삭제했습니다.");
    setHistoryTab("public");
    setCurrentPage("history");
  };

  const openHistory = () => {
    setHistoryNotice("");
    setHistoryTab("mine");
    setCurrentPage("history");
  };

  // 사이트를 열면 백엔드를 미리 깨운다 (무료 서버 콜드 스타트 대기 줄이기)
  useEffect(() => {
    wakeServer();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("share");
    const resultId = params.get("result");
    if (token) {
      getSharedAnalysis(token)
        .then((result) => {
          setShareToken(token);
          setTargetUrl(result.url);
          setAnalysisResult(result);
          setCurrentPage("result");
        })
        .catch((error) => {
          // 링크 문제(404)와 서버에 닿지 못한 경우를 구분한다
          setShareError(
            error?.status === 404
              ? "공유가 중지됐거나 잘못된 링크입니다."
              : "서버에 연결하지 못했습니다. 서버가 깨어나는 데 30초~1분 걸릴 수 있으니 잠시 후 새로고침해 주세요."
          );
          setCurrentPage("shared-error");
        });
    } else if (resultId) {
      // 결과 화면에서 새로고침해도 같은 결과를 다시 연다 (주소의 ?result=분석ID)
      getAnalysis(resultId)
        .then((result) => {
          setTargetUrl(result.url);
          setAnalysisResult(result);
          setCurrentPage("result");
        })
        .catch(() => {
          window.history.replaceState(null, "", window.location.pathname);
        });
    }
  }, []);

  // 주소창을 현재 화면에 맞춘다
  // - 내 결과를 보는 중이면 ?result=분석ID (새로고침해도 유지)
  // - 공유 링크로 보는 중이면 ?share=토큰 그대로
  // - 다른 화면으로 가면 둘 다 지운다
  useEffect(() => {
    const search = window.location.search;
    if (currentPage === "shared-error") return;
    if (currentPage === "result" && shareToken) return;
    if (currentPage === "result" && analysisResult?.id && analysisResult.saved !== false) {
      const next = `?result=${encodeURIComponent(analysisResult.id)}`;
      if (search !== next) window.history.replaceState(null, "", window.location.pathname + next);
      return;
    }
    if (search.includes("share=") || search.includes("result=")) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, [currentPage, shareToken, analysisResult]);

  const handleAnalyze = (url, publicStatus, ownerName = null, ownerSecret = null) => {
    setTargetUrl(url);
    setIsPublic(publicStatus);
    setOwner({ name: ownerName, secret: ownerSecret });
    setShareToken(null);
    setCurrentPage("analysis");
  };

  const handleAnalysisComplete = (result) => {
    // 식별 암호는 서버에 보낸 뒤 화면 메모리에 남기지 않는다
    setOwner({ name: null, secret: null });
    setAnalysisResult(result);
    setCurrentPage("result");
  };

  const handleViewHistory = (result) => {
    setTargetUrl(result.url);
    setShareToken(null);
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
                ["analysis", "result"].includes(currentPage) ? "active" : ""
              }`}
              onClick={openUrlInput}
            >
              <span>⌕</span>
              URL 분석
            </button>

            <button
              className={`sidebar-item ${
                currentPage === "history" ? "active" : ""
              }`}
              onClick={openHistory}
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
              onOpenHistory={openHistory}
              focusRequest={focusRequest}
            />
          )}

          {currentPage === "analysis" && (
            <Analysis
              url={targetUrl}
              isPublic={isPublic}
              ownerName={owner.name}
              ownerSecret={owner.secret}
              onComplete={handleAnalysisComplete}
            />
          )}

          {currentPage === "result" && (
            <Result
              url={targetUrl}
              result={analysisResult}
              shareToken={shareToken}
              onResultChange={setAnalysisResult}
              onDeleted={handleDeleted}
            />
          )}

          {currentPage === "shared-error" && (
            <section className="shared-error">
              <h2>결과를 열 수 없습니다</h2>
              <p>{shareError}</p>
            </section>
          )}
          {currentPage === "history" && (
            <History
              key={`${historyTab}-${historyNotice}`}
              initialTab={historyTab}
              notice={historyNotice}
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