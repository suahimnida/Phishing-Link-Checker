import "./MLModel.css";

// 서비스 모델 v2 (backend/ml_integration/models/url_model_v2_report.json)
const features = [
  "문자 n-gram (3~5글자)",
  "URL 원문 (스킴·도메인만 소문자로, 홈페이지 끝 '/' 제거)",
  "로지스틱 회귀 분류",
  "검증 세트로 정한 판정 기준점",
];

function MLModel() {
  return (
    <section className="ml-model-page">
      <div className="ml-model-header">
        <p className="ml-model-eyebrow">ML MODEL</p>

        <h2>ML 모델</h2>

        <p className="ml-model-description">
          URL 문자열만 보고 피싱 가능성을 계산하는 머신러닝 모델이에요.
        </p>
      </div>

      <div className="ml-overview">
        <div className="ml-overview-content">
          <span className="ml-section-number">01</span>

          <div>
            <h3>URL 기반 피싱 탐지</h3>

            <p>
              입력된 URL 원문에서 3~5글자 문자 조합(n-gram)을
              뽑아 정상·피싱 URL로 학습한 모델이 위험도를
              계산해요. 학습에 없던 데이터로 평가했을 때
              정상 URL을 피싱으로 잘못 판정하는 비율은 34.2%,
              피싱을 놓치는 비율은 10.3%예요(ROC-AUC 0.879).
              공식 도메인 허용 목록에 있는 사이트는 ML 점수와
              관계없이 정상으로 판정해요.
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
            <strong>문자 조합 추출</strong>
            <p>URL 원문의 3~5글자 n-gram</p>
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
            <strong>기준점 보정</strong>
            <p>의심 30점 · 피싱 60점</p>
          </div>
        </div>
      </div>

      <div className="ml-info-grid">
        <div className="ml-info-card">
          <span>DATASET</span>
          <strong>PhiUSIIL + 공개 URL + KISA</strong>
          <p>형태 편향을 고친 정상·피싱 URL 약 19만 건</p>
        </div>

        <div className="ml-info-card">
          <span>INPUT</span>
          <strong>URL 원문</strong>
          <p>입력한 URL 문자열 (대소문자 표기 차이로 점수가 바뀌지 않게 정규화)</p>
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

