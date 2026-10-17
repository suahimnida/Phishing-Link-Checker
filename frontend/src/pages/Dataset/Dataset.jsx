import "./Dataset.css";

const datasets = [
  {
    number: "01",
    name: "KISA 피싱사이트 데이터",
    type: "피싱 사례 데이터",
    description:
      "한국인터넷진흥원이 공개한 피싱 사이트 목록(2024)이에요. 입력한 URL이 목록과 일치하면 피싱으로 확정하고, ML 학습 데이터에도 피싱 사례로 넣었어요.",
    usage: "블랙리스트 확정 판정, ML 학습(피싱)",
    source: "한국인터넷진흥원(KISA)",
  },
  {
    number: "02",
    name: "PHIUSIIL",
    type: "URL 데이터셋",
    description:
      "정상·피싱 URL 데이터셋이에요. 정상 URL이 모두 https://www. 형태라 그대로 쓰면 형태만 보고 판단하는 편향이 생겨, 스킴과 www 형태를 무작위로 바꿔 학습에 썼어요.",
    usage: "ML 학습(정상·피싱)",
    source: "UCI Machine Learning Repository",
  },
  {
    number: "03",
    name: "공개 URL 데이터셋",
    type: "URL 데이터셋",
    description:
      "경로가 있는 정상 URL과 다양한 형태의 악성 URL을 보충하기 위해 함께 학습했어요. 세 데이터를 합쳐 약 19만 건(학습 15.3만 · 검증 3.8만)을 도메인이 겹치지 않게 나눴어요.",
    usage: "ML 학습(정상·피싱), 유사 사례 검색 5,000건",
    source: "faizann24 / Using-machine-learning-to-detect-malicious-URLs (GitHub)",
  },
  {
    number: "04",
    name: "공식 기관 대응 가이드",
    type: "RAG 검색 자료",
    description:
      "피싱 신고, 계정·금융 피해 대응, 예방 방법을 담은 공식 기관 안내 10건이에요. 분석 근거에 맞는 가이드를 찾아 AI 설명과 리포트에 출처와 함께 넣어요.",
    usage: "대응 가이드 검색, AI 설명·리포트의 출처",
    source: "KISA 보호나라·118, 금융감독원, 금융결제원, KAIT 엠세이퍼, 경찰청 ECRM",
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
          주요 데이터와 자료예요.
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
            구분하여 활용해요.
          </p>
        </div>
      </div>
    </section>
  );
}

export default Dataset;