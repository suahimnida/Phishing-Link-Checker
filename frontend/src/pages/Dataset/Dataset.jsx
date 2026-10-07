import "./Dataset.css";

const datasets = [
  {
    number: "01",
    name: "KISA 피싱사이트 데이터",
    type: "피싱 사례 데이터",
    description:
      "한국인터넷진흥원에서 제공하는 피싱사이트 관련 데이터를 활용하여 알려진 피싱 사이트 사례를 확인합니다.",
    usage: "피싱 사이트 사례 확인 및 분석 결과 보조",
    source: "한국인터넷진흥원(KISA)",
  },
  {
    number: "02",
    name: "PHIUSIIL",
    type: "URL 데이터셋",
    description:
      "정상 및 피싱 URL 데이터를 기반으로 URL의 다양한 특징을 분석하고 피싱 탐지 모델 개발에 활용합니다.",
    usage: "URL 특징 분석 및 ML 기반 탐지",
    source: "UCI Machine Learning Repository",
  },
  {
    number: "03",
    name: "보안 문서 및 RAG 자료",
    type: "보안 지식 데이터",
    description:
      "피싱 및 웹 보안과 관련된 공개 문서와 보안 자료를 활용하여 분석 결과에 대한 근거와 대응 방법을 제공합니다.",
    usage: "분석 근거 및 보안 대응 방법 제공",
    source: "공개 보안 자료",
  },
];

function Dataset() {
  return (
    <section className="dataset-page">
      <div className="dataset-header">
        <p className="dataset-eyebrow">DATASETS</p>

        <h2>데이터셋</h2>

        <p className="dataset-description">
          피싱 사이트 분석과 AI 기반 탐지에 활용되는
          주요 데이터와 자료입니다.
        </p>
      </div>

      <div className="dataset-list">
        {datasets.map((dataset) => (
          <article
            className="dataset-card"
            key={dataset.number}
          >
            <div className="dataset-card-top">
              <span className="dataset-number">
                {dataset.number}
              </span>

              <span className="dataset-type">
                {dataset.type}
              </span>
            </div>

            <h3>{dataset.name}</h3>

            <p className="dataset-card-description">
              {dataset.description}
            </p>

            <div className="dataset-info">
              <div>
                <span>활용 목적</span>
                <p>{dataset.usage}</p>
              </div>

              <div>
                <span>출처</span>
                <p>{dataset.source}</p>
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="dataset-note">
        <div className="dataset-note-icon">i</div>

        <div>
          <h3>데이터 활용 방식</h3>

          <p>
            데이터셋은 URL 특징 분석, 피싱 사례 확인,
            RAG 기반 정보 검색 등 각 기능의 목적에 맞게
            구분하여 활용합니다.
          </p>
        </div>
      </div>
    </section>
  );
}

export default Dataset;