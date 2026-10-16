import "./DetailCard.css";

// '자세히 보기' 안의 접히는 카드. 처음에는 제목과 한 줄 요약만 보인다.
function DetailCard({ title, summary, children, defaultOpen = false }) {
  return (
    <details className="detail-card" open={defaultOpen}>
      <summary>
        <span className="detail-card-title">{title}</span>
        {summary && <span className="detail-card-summary">{summary}</span>}
      </summary>
      <div className="detail-card-body">{children}</div>
    </details>
  );
}

export default DetailCard;
