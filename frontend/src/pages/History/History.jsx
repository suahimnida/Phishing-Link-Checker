import { useEffect, useState } from "react";
import "./History.css";

import { getAnalysis, listMyAnalyses, listPublicAnalyses } from "../../services/api";
import { verdictInfo } from "../../utils/verdict";

function History({ onViewResult, initialTab = "mine", notice = "" }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  // 불러오기 실패를 '기록 없음'과 구분한다 (QA: 서버가 잠들어 있으면 기록이 사라진 것처럼 보였다)
  const [loadError, setLoadError] = useState("");
  // mine: 이 브라우저의 기록 / public: 다른 사용자가 공개한 결과
  const [tab, setTab] = useState(initialTab);

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      setLoadError("");
      try {
        const items = tab === "mine" ? await listMyAnalyses() : await listPublicAnalyses();

        setHistory(items);
      } catch (error) {
        console.error(
          "분석 기록을 불러오지 못했습니다:",
          error
        );
        setHistory([]);
        setLoadError(
          error?.status === 0
            ? "서버에 연결하지 못했습니다. 서버가 깨어나는 데 30초~1분 걸릴 수 있으니 잠시 후 다시 열어 주세요."
            : "분석 기록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
        );
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, [tab]);

  const tabs = (
    <div className="history-tabs" role="tablist">
      <button className={tab === "mine" ? "on" : ""} onClick={() => setTab("mine")} role="tab">
        내 기록
      </button>
      <button className={tab === "public" ? "on" : ""} onClick={() => setTab("public")} role="tab">
        공개 분석
      </button>
    </div>
  );

  const handleViewResult = async (item) => {
    try {
      const result = await getAnalysis(item.id);

      onViewResult(result);
    } catch (error) {
      console.error(
        "분석 결과를 불러오지 못했습니다:",
        error
      );

      alert(
        error?.status === 404
          ? "삭제됐거나 볼 수 없는 분석 결과입니다."
          : "분석 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
      );
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) {
      return "-";
    }

    return new Date(dateString).toLocaleString(
      "ko-KR",
      {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }
    );
  };

  const getRiskStatus = (verdict) => verdictInfo(verdict);

  if (loading) {
    return (
      <section className="history-page">
        <div className="history-header">
          <div>
            <p className="history-eyebrow">
              ANALYSIS HISTORY
            </p>

            <h2>분석 기록</h2>

            <p className="history-description">
              분석한 URL에 대한 결과를 확인할 수 있어요.
            </p>
          </div>
        </div>

        {tabs}

        <div className="history-empty">
          <h3>분석 기록을 불러오는 중입니다.</h3>
        </div>
      </section>
    );
  }

  return (
    <section className="history-page">
      {/* Header */}
      <div className="history-header">
        <div>
          <p className="history-eyebrow">
            ANALYSIS HISTORY
          </p>

          <h2>분석 기록</h2>

          <p className="history-description">
            분석한 URL에 대한 결과를 확인할 수 있어요.
          </p>
        </div>

        <div className="history-count">
          <span>{history.length}</span>
          <small>건</small>
        </div>
      </div>

      {tabs}

      {notice && <p className="history-notice">{notice}</p>}
      {/* 기록은 브라우저 ID로 찾는다. 브라우저 데이터를 지우거나 다른 기기에서 열면 내 기록이 보이지 않는다 */}
      {tab === "mine" && (
        <p className="history-storage-note">
          비공개로 설정한 분석 요청은 '내 기록'에서 확인할 수 있으며, 분석을 요청한 브라우저 내에서만 확인
          가능해요.
        </p>
      )}

      {/* Empty */}
      {history.length === 0 ? (
        <div className="history-empty">
          <div className="history-empty-icon">
            ◷
          </div>

          <h3>
            {loadError
              ? "분석 기록을 불러오지 못했습니다."
              : tab === "mine"
              ? "분석 기록이 없습니다."
              : "공개된 분석 결과가 없습니다."}
          </h3>
          <p>
            {loadError
              ? loadError
              : tab === "mine"
              ? "웹사이트를 분석하면 이곳에서 분석 기록을 확인할 수 있습니다. 브라우저 데이터를 지웠다면 이전 기록은 이 브라우저에서 다시 볼 수 없습니다."
              : "분석할 때 '공개'를 선택하거나 결과 화면에서 공개로 바꾸면 이곳에 표시됩니다."}
          </p>
        </div>
      ) : (
        <div className="history-list">
          {history.map((item, index) => {
            const riskStatus = getRiskStatus(
              item.verdict
            );

            return (
              <article
                className="history-card"
                key={item.id}
              >
                <div className="history-card-main">
                  {/* Status / Date */}
                  <div className="history-card-top">
                    <span
                      className={`history-status ${riskStatus.className}`}
                    >
                      {riskStatus.label}
                    </span>

                    <span className="history-date">
                      {formatDate(item.created_at)}
                    </span>
                    {tab === "public" && item.owner_name && (
                      <span className="history-owner">{item.owner_name}</span>
                    )}
                  </div>

                  {/* URL */}
                  <h3>{item.url}</h3>

                  {/* 안내 문구는 맨 위 기록에만 보여 준다 */}
                  {index === 0 && <p>분석 결과를 확인하려면 '결과 보기'를 눌러주세요.</p>}
                </div>

                {/* Actions */}
                <div className="history-card-actions">
                  <button
                    className="history-view-button"
                    onClick={() =>
                      handleViewResult(item)
                    }
                  >
                    결과 보기
                    <span>→</span>
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default History;

