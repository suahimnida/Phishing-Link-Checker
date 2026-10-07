import "./DetectionMethods.css";

const methods = [
  {
    number: "01",
    title: "URL 구조 분석",
    description:
      "URL의 길이와 문자 구성, 특수문자 등의 특징을 분석하여 의심스러운 URL 패턴을 탐지합니다.",
    features: [
      "URL 길이",
      "문자 및 특수문자 패턴",
      "숫자 비율",
      "도메인 구조",
    ],
  },
  {
    number: "02",
    title: "통계 및 문자열 분석",
    description:
      "URL 문자열의 무작위성과 반복적인 문자 조합을 분석하여 피싱 사이트에서 나타날 수 있는 특징을 확인합니다.",
    features: [
      "문자열 엔트로피",
      "n-gram",
      "문자 빈도",
      "의심 키워드",
    ],
  },
  {
    number: "03",
    title: "웹페이지 분석",
    description:
      "웹페이지의 HTML 구조와 콘텐츠를 분석하여 추가적인 위험 요소를 확인합니다.",
    features: [
      "HTML / DOM 구조",
      "페이지 텍스트",
      "로그인 및 입력 요소",
      "페이지 이미지",
    ],
  },
  {
    number: "04",
    title: "AI Agent 분석",
    description:
      "각 분석 단계에서 수집된 결과를 종합하여 사이트의 위험도를 판단하고 근거를 설명합니다.",
    features: [
      "분석 결과 종합",
      "위험도 판단",
      "탐지 근거 생성",
      "분석 리포트 생성",
    ],
  },
];

function DetectionMethods() {
  return (
    <section className="detection-methods-page">
      <div className="detection-methods-header">
        <p className="detection-eyebrow">
          DETECTION METHODS
        </p>

        <h2>탐지 방법</h2>

        <p className="detection-description">
          피싱 사이트 분석에 사용되는 주요 탐지 방법과
          분석 항목을 확인할 수 있습니다.
        </p>
      </div>

      <div className="methods-list">
        {methods.map((method) => (
          <article
            className="method-card"
            key={method.number}
          >
            <div className="method-number">
              {method.number}
            </div>

            <div className="method-content">
              <h3>{method.title}</h3>

              <p>{method.description}</p>

              <div className="method-features">
                {method.features.map((feature) => (
                  <span key={feature}>
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="detection-flow">
        <div className="flow-header">
          <div>
            <p className="detection-eyebrow">
              ANALYSIS FLOW
            </p>

            <h3>분석 흐름</h3>
          </div>
        </div>

        <div className="flow-list">
          <div className="flow-item">
            <span>01</span>
            <strong>URL 입력</strong>
          </div>

          <span className="flow-arrow">→</span>

          <div className="flow-item">
            <span>02</span>
            <strong>특징 분석</strong>
          </div>

          <span className="flow-arrow">→</span>

          <div className="flow-item">
            <span>03</span>
            <strong>웹페이지 분석</strong>
          </div>

          <span className="flow-arrow">→</span>

          <div className="flow-item">
            <span>04</span>
            <strong>AI 종합 판단</strong>
          </div>
        </div>
      </div>
    </section>
  );
}

export default DetectionMethods;