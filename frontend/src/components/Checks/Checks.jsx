import "./Checks.css";

const STATE_LABELS = {
  ok: "확인함",
  warn: "주의",
  none: "기록 없음",
  skipped: "건너뜀",
  failed: "확인 못 함",
};

// 의심 사이트에 직접 접속하지 않고, 공개 기록 서비스에 물어봐서 확인한 정보 목록
function Checks({ data }) {
  const blacklisted = Boolean(data.blacklist?.matched);
  const modelReady = data.model?.status === "ready";

  const items = [
    {
      key: "blacklist",
      label: "신고된 피싱 사이트 목록",
      source:
        data.blacklist?.source === "검토된 사용자 신고"
          ? "사용자 신고를 검토해 추가한 목록"
          : "KISA 피싱 사이트 URL 공개 데이터 (2024-12-31 기준, 이후 생긴 사이트는 없을 수 있어요)",
      state: blacklisted ? "warn" : "ok",
      value: blacklisted ? "목록에 있는 주소예요" : "목록에 없어요",
    },
    {
      key: "pattern",
      label: "주소 생김새 분석",
      source: "주소 문자열만 보는 ML 모델",
      state: blacklisted ? "skipped" : modelReady ? "ok" : "failed",
      value: blacklisted
        ? "신고 목록에서 확인돼 생략했어요"
        : modelReady
        ? "피싱 주소와 얼마나 닮았는지 계산했어요"
        : "계산하지 못했어요",
    },
    ...(data.detections?.reputation?.checks || []),
  ];
  const hasReputation = Boolean(data.detections?.reputation?.checks);

  return (
    <div className="checks">
      <p className="checks-hint">
        의심 사이트에는 접속하지 않았어요. 주소 문자열과, 누구나 조회할 수 있는 공개 기록만 확인했어요.
      </p>
      <ul>
        {items.map((item) => (
          <li key={item.key} className={`check-item ${item.state}`}>
            <span className="check-state">{STATE_LABELS[item.state] || item.state}</span>
            <div>
              <strong>{item.label}</strong>
              <p>{item.value}</p>
              <span className="check-source">{item.source}</span>
            </div>
          </li>
        ))}
      </ul>
      {!hasReputation && (
        <p className="checks-hint">
          주소를 만든 날짜, 인증서 기록, 서버 위치는 이 분석에서 확인하지 못했어요.
        </p>
      )}
    </div>
  );
}

export default Checks;
