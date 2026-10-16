// 결과 화면 맨 위 '한눈에 보는 판정'에 쓸 문구를 정한다.
// 일반 사용자가 "눌러도 되는지"와 "지금 무엇을 해야 하는지"만 바로 알 수 있게,
// 점수·신뢰도 같은 수치 대신 상황별로 정해 둔 쉬운 문장을 쓴다.
// 백엔드 응답에 이미 있는 값만 쓰므로, 예전에 저장된 분석 기록에도 그대로 적용된다.

const ACTIONS = {
  delete: "링크를 누르지 말고 받은 메시지를 삭제하세요.",
  official: "링크 대신 해당 기관의 공식 앱이나 직접 입력한 주소로 확인하세요.",
  askSender: "보낸 사람에게 직접 확인한 뒤에만 여세요.",
  noInput: "열더라도 로그인이나 개인정보 입력은 하지 마세요.",
  retry: "잠시 후 다시 분석해 주세요.",
};

function evidenceSources(data) {
  return (data.ai_analysis?.evidence || []).map((e) => e.source || "");
}

function detectionReasons(data) {
  return Object.values(data.detections || {})
    .filter((d) => d && typeof d === "object" && d.status === "suspicious")
    .flatMap((d) => (Array.isArray(d.reasons) ? d.reasons : []));
}

// ML 판정일 때, 탐지 결과에서 사용자가 이해하기 쉬운 이유를 하나 고른다
function mlReason(data, verdict) {
  // 백엔드가 쉬운 말로 정리한 의심 특징(findings)이 있으면 가장 앞의 것을 쓴다
  const first = Array.isArray(data.findings) ? data.findings[0] : null;
  if (first?.title) {
    return first.title;
  }
  const reasons = detectionReasons(data).join(" ");
  if (reasons.includes("브랜드") || reasons.includes("공식 도메인(")) {
    return "유명 회사나 기관 이름을 넣어 진짜처럼 꾸민 주소예요.";
  }
  if (reasons.includes("IP 주소")) {
    return "도메인 이름 대신 숫자 주소(IP)를 쓰고 있어요. 정상 사이트에서는 드문 형태예요.";
  }
  if (reasons.includes("'@'")) {
    return "주소에 '@'가 들어 있어 보이는 것과 다른 곳으로 이동할 수 있어요.";
  }
  return verdict === "phishing"
    ? "주소 생김새가 기존 피싱 사이트들과 많이 닮았어요."
    : "피싱 사이트에서 자주 보이는 특징이 일부 있어요.";
}

export function userSummary(data) {
  const verdict = data?.verdict ?? null;
  const sources = evidenceSources(data);
  const blacklisted = Boolean(data?.blacklist?.matched);
  const allowlisted = Boolean(data?.allowlist?.matched) && !blacklisted;
  const shortener = sources.includes("단축 URL");
  const homograph = sources.includes("동형 문자 도메인");

  if (blacklisted) {
    return {
      level: "danger",
      headline: "누르지 마세요",
      reason: "한국인터넷진흥원(KISA)에 피싱 사이트로 신고된 주소예요.",
      action: ACTIONS.delete,
    };
  }

  if (verdict === "phishing") {
    return {
      level: "danger",
      headline: "누르지 마세요",
      reason: homograph
        ? "공식 사이트 주소를 비슷하게 생긴 글자로 흉내 낸 주소예요."
        : mlReason(data, verdict),
      action: homograph ? ACTIONS.official : ACTIONS.delete,
    };
  }

  if (verdict === "suspicious") {
    if (shortener) {
      return {
        level: "caution",
        headline: "확인 후 여세요",
        reason: "짧게 줄인 주소라 실제로 어디로 연결되는지 알 수 없어요.",
        action: ACTIONS.askSender,
      };
    }
    return {
      level: "caution",
      headline: "확인 후 여세요",
      reason: homograph
        ? "주소 안에 서로 다른 나라 글자가 섞여 있어 다른 사이트로 착각하기 쉬워요."
        : mlReason(data, verdict),
      action: ACTIONS.noInput,
    };
  }

  if (verdict === "normal") {
    return {
      level: "safe",
      headline: "위험 신호가 없어요",
      reason: allowlisted
        ? "공식 사이트 목록에 있는 주소예요."
        : "피싱 사이트에서 보이는 특징이 발견되지 않았어요.",
      action: null,
    };
  }

  return {
    level: "unknown",
    headline: "지금은 판단하지 못했어요",
    reason: "분석 중 문제가 생겨 결과를 내지 못했어요.",
    action: ACTIONS.retry,
  };
}
