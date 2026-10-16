import "./Findings.css";

// 탐지된 특징을 쉬운 말로: 무엇이 보였는지, 왜 의심스러운지, 어떤 피해로 이어질 수 있는지,
// 학습 데이터에서 피싱·정상 URL에 각각 얼마나 나타났는지
function Findings({ findings }) {
  if (!findings?.length) {
    return null;
  }

  return (
    <div className="findings">
      <p className="findings-hint">이 주소에서 발견된 의심 특징이에요.</p>
      <ul>
        {findings.map((f) => (
          <li className="finding-item" key={f.key}>
            <h4>{f.title}</h4>
            <dl>
              <dt>왜 의심스럽나요</dt>
              <dd>{f.why}</dd>
              <dt>어떤 피해가 생길 수 있나요</dt>
              <dd>{f.harm}</dd>
            </dl>

            {f.stat && (
              <div className="finding-stat">
                <div className="finding-stat-bars" aria-hidden="true">
                  <span className="bar-label">피싱 URL</span>
                  <span className="bar-value">{f.stat.phishing_pct}</span>
                  <span className="bar-label">정상 URL</span>
                  <span className="bar-value">{f.stat.normal_pct}</span>
                </div>
                <p>
                  {f.stat.text} <span className="finding-source">출처: {f.stat.source}</span>
                </p>
              </div>
            )}

            <p className="finding-detail">탐지 내용: {f.detail}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Findings;
