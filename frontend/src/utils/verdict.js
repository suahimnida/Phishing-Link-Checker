// 판정 표시를 한 곳에서 관리한다.
// 예전에는 화면마다 따로 정해서 판정이 없을 때(null) Result는 '의심', History·홈은 '정상'으로 보였다 (QA).

// 화면에는 일반 사용자 기준의 3단계(위험/주의/안전)로 표시한다.
// term은 백엔드 설명 문장·리포트에 쓰이는 판정 이름(피싱/피싱 의심/정상)이다.
const VERDICTS = {
  phishing: { label: "위험", className: "danger", level: "위험", term: "피싱" },
  suspicious: { label: "주의", className: "warning", level: "주의", term: "피싱 의심" },
  normal: { label: "안전", className: "normal", level: "안전", term: "정상" },
};

const UNKNOWN = { label: "판정 불가", className: "unknown", level: "판정 불가", term: "판정 불가" };

export function verdictInfo(verdict) {
  return VERDICTS[verdict] ?? UNKNOWN;
}

// risk_level(safe/caution/warning/danger) 표시. 값이 없으면 '판정 불가'
const LEVELS = {
  safe: { label: "안전", className: "normal" },
  caution: { label: "주의", className: "warning" },
  warning: { label: "경고", className: "danger" },
  danger: { label: "위험", className: "danger" },
};

export function levelInfo(level) {
  return LEVELS[level] ?? { label: "판정 불가", className: "unknown" };
}
