import { useState } from "react";

import { sendFeedback } from "../../services/api";
import "./FeedbackBox.css";

const MAX_COMMENT = 200;

// 판정마다 '틀렸다'고 할 만한 방향을 먼저 보여 준다
function claimOptions(verdict) {
  const safe = { id: "actually_safe", label: "실제로는 안전한 사이트예요" };
  const phishing = { id: "actually_phishing", label: "실제로는 피싱 사이트예요" };
  const other = { id: "other", label: "기타 의견" };
  return verdict === "normal" ? [phishing, safe, other] : [safe, phishing, other];
}

// 결과 화면의 '이 판정이 틀렸나요?' 신고.
// 보낸 의견은 바로 반영되지 않고, 검토를 거쳐 목록과 모델 개선에 쓰인다 (조작 신고 방지)
function FeedbackBox({ analysisId, verdict, shareToken }) {
  const [open, setOpen] = useState(false);
  const [claim, setClaim] = useState(null);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState("");
  const [error, setError] = useState("");

  async function submit() {
    if (!claim || busy) return;
    setBusy(true);
    setError("");
    try {
      const res = await sendFeedback(analysisId, claim, comment, shareToken);
      setDone(res.message);
    } catch (e) {
      setError(e.status === 429 ? e.detail : e.detail || "의견을 보내지 못했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="feedback-box">
        <p className="feedback-done" role="status">{done}</p>
      </div>
    );
  }

  return (
    <div className="feedback-box">
      <button type="button" className="feedback-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        이 판정이 틀렸나요?
      </button>

      {open && (
        <div className="feedback-panel">
          <div className="feedback-options" role="radiogroup" aria-label="의견 종류">
            {claimOptions(verdict).map((o) => (
              <button
                type="button"
                key={o.id}
                role="radio"
                aria-checked={claim === o.id}
                className={claim === o.id ? "selected" : ""}
                onClick={() => setClaim(o.id)}
              >
                {o.label}
              </button>
            ))}
          </div>

          <label className="feedback-comment">
            <span>더 알려 주실 내용 (선택)</span>
            <textarea
              value={comment}
              maxLength={MAX_COMMENT}
              rows={3}
              placeholder="예: 회사에서 쓰는 공식 사이트예요"
              onChange={(e) => setComment(e.target.value)}
            />
            <span className="feedback-meta">
              이름·전화번호 같은 개인정보는 적지 마세요. {comment.length}/{MAX_COMMENT}
            </span>
          </label>

          {error && <p className="feedback-error" role="alert">{error}</p>}

          <div className="feedback-actions">
            <button type="button" className="feedback-submit" disabled={!claim || busy} onClick={submit}>
              {busy ? "보내는 중" : "의견 보내기"}
            </button>
            <p>보낸 의견은 검토를 거쳐 피싱 목록과 판정 모델 개선에 쓰여요.</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default FeedbackBox;
