import AfterClick from "../AfterClick/AfterClick";
import { userSummary } from "../../utils/userSummary";
import "./QuickVerdict.css";

const LEVEL_LABELS = {
  danger: "위험",
  caution: "주의",
  safe: "안전",
  unknown: "판정 불가",
};

// 결과 화면 맨 위: 3단계 판정, 한 줄 이유, 지금 할 일 하나만 보여 준다.
// 점수·신뢰도·탐지 항목 같은 근거는 아래 '자세히 보기'에 있다.
function QuickVerdict({ data, url }) {
  const summary = userSummary(data);
  const target = data.url || url || "-";

  return (
    <section className={`quick-verdict ${summary.level}`} aria-live="polite">
      <div className="quick-verdict-top">
        <span className="quick-verdict-badge">{LEVEL_LABELS[summary.level]}</span>
        <p className="quick-verdict-url" title={target}>{target}</p>
      </div>

      <h2 className="quick-verdict-headline">{summary.headline}</h2>
      <p className="quick-verdict-reason">{summary.reason}</p>

      {summary.action && (
        <div className="quick-verdict-action">
          <strong>지금 할 일</strong>
          <p>{summary.action}</p>
        </div>
      )}

      {(summary.level === "danger" || summary.level === "caution") && <AfterClick />}

      {summary.level === "safe" && (
        <p className="quick-verdict-note">
          위험 신호가 없다는 뜻이고, 안전을 보장하지는 않아요. 열기 전에 주소창의 주소가 맞는지
          한 번 더 확인하세요.
        </p>
      )}

      <p className="quick-verdict-scope">
        이 사이트에 직접 접속하지 않고, 주소와 공개된 기록만으로 확인했어요. 무엇을 확인했는지는
        아래 '접속하지 않고 확인한 정보'에서 볼 수 있어요.
      </p>
    </section>
  );
}

export default QuickVerdict;
