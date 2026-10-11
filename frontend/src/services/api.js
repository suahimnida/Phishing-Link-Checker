export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const CLIENT_ID_KEY = "phishingClientId";

async function request(path, options, errorMessage) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

  if (!response.ok) {
    throw new Error(`${errorMessage}: ${response.status}`);
  }

  return response.json();
}

export function getSavedClientId() {
  return localStorage.getItem(CLIENT_ID_KEY);
}

export async function getClientId() {
  const savedClientId = getSavedClientId();

  if (savedClientId) {
    return savedClientId;
  }

  const data = await request(
    "/api/v1/clients",
    { method: "POST" },
    "클라이언트 ID 발급 실패"
  );

  localStorage.setItem(CLIENT_ID_KEY, data.client_id);

  return data.client_id;
}

export async function analyzeUrl(url, isPublic = false, ownerName = null, ownerSecret = null) {
  const clientId = await getClientId();

  return request(
    "/api/v1/analyses",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Client-Id": clientId,
      },
      body: JSON.stringify({
        url,
        is_public: isPublic,
        owner_name: ownerName || undefined,
        owner_secret: ownerSecret || undefined,
      }),
    },
    "URL 분석 요청 실패"
  );
}

export async function listMyAnalyses() {
  const clientId = await getClientId();

  const data = await request(
    "/api/v1/analyses?scope=mine",
    {
      headers: {
        "X-Client-Id": clientId,
      },
    },
    "분석 기록 조회 실패"
  );

  return Array.isArray(data.items) ? data.items : [];
}

export async function getAnalysis(analysisId) {
  const clientId = await getClientId();

  return request(
    `/api/v1/analyses/${analysisId}`,
    {
      headers: {
        "X-Client-Id": clientId,
      },
    },
    "분석 결과 조회 실패"
  );
}

function shareQuery(shareToken) {
  return shareToken ? `?share=${encodeURIComponent(shareToken)}` : "";
}

export async function createReport(analysisId, shareToken = null) {
  const clientId = await getClientId();

  return request(
    `/api/v1/analyses/${analysisId}/report${shareQuery(shareToken)}`,
    {
      method: "POST",
      headers: {
        "X-Client-Id": clientId,
      },
    },
    "리포트 생성 실패"
  );
}

export async function fetchReportPdf(analysisId, shareToken = null) {
  const clientId = await getClientId();

  const response = await fetch(
    `${API_BASE_URL}/api/v1/analyses/${analysisId}/report.pdf${shareQuery(shareToken)}`,
    {
      headers: {
        "X-Client-Id": clientId,
      },
    }
  );

  if (!response.ok) {
    throw new Error(`PDF 생성 실패: ${response.status}`);
  }

  return response.blob();
}

export function reportFileName(analysisId) {
  return `phishing-report-${String(analysisId).slice(0, 8)}.pdf`;
}

export async function listPublicAnalyses() {
  const data = await request("/api/v1/analyses?scope=public", {}, "공개 분석 조회 실패");
  return Array.isArray(data.items) ? data.items : [];
}

export async function setVisibility(analysisId, isPublic) {
  const clientId = await getClientId();

  return request(
    `/api/v1/analyses/${analysisId}/visibility`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-Client-Id": clientId },
      body: JSON.stringify({ is_public: isPublic }),
    },
    "공개 범위 변경 실패"
  );
}

export async function createShareLink(analysisId) {
  const clientId = await getClientId();

  const data = await request(
    `/api/v1/analyses/${analysisId}/share`,
    { method: "POST", headers: { "X-Client-Id": clientId } },
    "공유 링크 생성 실패"
  );
  return data.token;
}

export async function revokeShareLink(analysisId) {
  const clientId = await getClientId();

  await request(
    `/api/v1/analyses/${analysisId}/share`,
    { method: "DELETE", headers: { "X-Client-Id": clientId } },
    "공유 중지 실패"
  );
}

export async function getSharedAnalysis(token) {
  return request(`/api/v1/shared/${encodeURIComponent(token)}`, {}, "공유된 결과 조회 실패");
}

export function shareUrl(token) {
  return `${window.location.origin}/?share=${encodeURIComponent(token)}`;
}

export async function verifyOwner(analysisId, name, secret) {
  const response = await fetch(`${API_BASE_URL}/api/v1/analyses/${analysisId}/verify-owner`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, secret }),
  });
  if (!response.ok) {
    const error = new Error(`본인 확인 실패: ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export async function deleteAnalysis(analysisId, name, secret, confirmText) {
  const response = await fetch(`${API_BASE_URL}/api/v1/analyses/${analysisId}/delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, secret, confirm_text: confirmText }),
  });
  if (!response.ok) {
    const error = new Error(`분석 결과 삭제 실패: ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}
