import "./MLModel.css";

const features = [
  "URL 길이",
  "문자 및 특수문자 패턴",
  "문자열 엔트로피",
  "n-gram",
  "의심 키워드",
  "도메인 특징",
];

function MLModel() {
  return (
    <section className="ml-model-page">
      <div className="ml-model-header">
        <p className="ml-model-eyebrow">ML MODEL</p>

        <h2>ML 모델</h2>

        <p className="ml-model-description">
          URL에서 추출한 다양한 특징을 기반으로
          피싱 사이트의 가능성을 분류하는 머신러닝 모델입니다.
        </p>
      </div>

      <div className="ml-overview">
        <div className="ml-overview-content">
          <span className="ml-section-number">01</span>

          <div>
            <h3>URL 기반 피싱 탐지</h3>

            <p>
              입력된 URL에서 길이, 문자 패턴, 엔트로피,
              n-gram 등의 특징을 추출하고 머신러닝 모델을
              통해 정상 사이트와 피싱 사이트를 분류합니다.
            </p>
          </div>
        </div>
      </div>

      <div className="ml-section">
        <div className="ml-section-header">
          <div>
            <p className="ml-model-eyebrow">FEATURES</p>
            <h3>사용 특징</h3>
          </div>

          <span>URL Analysis</span>
        </div>

        <div className="ml-feature-grid">
          {features.map((feature, index) => (
            <div className="ml-feature-card" key={feature}>
              <span>
                {String(index + 1).padStart(2, "0")}
              </span>
              <strong>{feature}</strong>
            </div>
          ))}
        </div>
      </div>

      <div className="ml-section">
        <div className="ml-section-header">
          <div>
            <p className="ml-model-eyebrow">ANALYSIS FLOW</p>
            <h3>분석 과정</h3>
          </div>
        </div>

        <div className="ml-flow">
          <div className="ml-flow-item">
            <span>01</span>
            <strong>URL 입력</strong>
            <p>분석할 웹사이트 URL</p>
          </div>

          <div className="ml-flow-arrow">→</div>

          <div className="ml-flow-item">
            <span>02</span>
            <strong>특징 추출</strong>
            <p>URL의 주요 특징 분석</p>
          </div>

          <div className="ml-flow-arrow">→</div>

          <div className="ml-flow-item">
            <span>03</span>
            <strong>ML 분류</strong>
            <p>정상 / 피싱 분류</p>
          </div>

          <div className="ml-flow-arrow">→</div>

          <div className="ml-flow-item">
            <span>04</span>
            <strong>AI Agent</strong>
            <p>분석 결과 종합</p>
          </div>
        </div>
      </div>

      <div className="ml-info-grid">
        <div className="ml-info-card">
          <span>DATASET</span>
          <strong>PHIUSIIL</strong>
          <p>정상 및 피싱 URL 데이터</p>
        </div>

        <div className="ml-info-card">
          <span>INPUT</span>
          <strong>URL Features</strong>
          <p>URL에서 추출한 특징 데이터</p>
        </div>

        <div className="ml-info-card">
          <span>OUTPUT</span>
          <strong>Normal / Phishing</strong>
          <p>피싱 가능성 분류 결과</p>
        </div>
      </div>
    </section>
  );
}

export default MLModel;

