// 판정 표시를 한 곳에서 관리한다.
// 예전에는 화면마다 따로 정해서 판정이 없을 때(null) Result는 '의심', History·홈은 '정상'으로 보였다 (QA).

const VERDICTS = {
  phishing: { label: "피싱", className: "danger", level: "위험" },
  suspicious: { label: "의심", className: "warning", level: "주의" },
  normal: { label: "정상", className: "normal", level: "안전" },
};

const UNKNOWN = { label: "판정 불가", className: "unknown", level: "판정 불가" };

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
