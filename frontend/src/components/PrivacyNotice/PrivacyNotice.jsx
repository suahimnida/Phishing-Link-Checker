import "./PrivacyNotice.css";

// 결과 화면 맨 아래 개인정보 처리 안내 (자세한 운영 기준은 백엔드 docs/OPERATIONS.md의 개인정보 항목)
function PrivacyNotice() {
  return (
    <details className="privacy-notice">
      <summary>개인정보 처리 안내</summary>
      <dl>
        <dt>저장하는 정보</dt>
        <dd>성명과 사용자 식별 암호, 입력하신 주소, 분석 결과 등을 포함한 정보가 저장돼요.</dd>
        <dt>보관 기간</dt>
        <dd>
          분석한 날부터 90일 동안 보관하고, 지나면 리포트·공유 링크·보낸 의견과 함께 자동으로 지워요.
          공개한 결과는 그 전에 직접 지울 수도 있어요.
        </dd>
        <dt>보낸 의견의 활용</dt>
        <dd>
          '이 판정이 틀렸나요?'로 보내주신 의견은 담당자에게 전달되며 내부적으로 검토한 뒤, 피싱 목록과 판정 모델
          개선에 사용돼요.
        </dd>
      </dl>
    </details>
  );
}

export default PrivacyNotice;
