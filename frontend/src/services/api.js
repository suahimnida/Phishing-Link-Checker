export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const CLIENT_ID_KEY = "phishingClientId";

async function getClientId() {
  const savedClientId =
    localStorage.getItem(CLIENT_ID_KEY);

  if (savedClientId) {
    return savedClientId;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/v1/clients`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error(
      `클라이언트 ID 발급 실패: ${response.status}`
    );
  }

  const data = await response.json();

  localStorage.setItem(
    CLIENT_ID_KEY,
    data.client_id
  );

  return data.client_id;
}

export async function analyzeUrl(
  url,
  isPublic = false
) {
  const clientId = await getClientId();

  const response = await fetch(
    `${API_BASE_URL}/api/v1/analyses`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Client-Id": clientId,
      },
      body: JSON.stringify({
        url,
        is_public: isPublic,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      `URL 분석 요청 실패: ${response.status}`
    );
  }

  return response.json();
}
