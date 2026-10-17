function Header() {
  return (
    <header className="header">
      <div className="header-logo">
        <div className="logo-mark">P</div>

        <div>
          <h1>URL 피싱 확률 분석</h1>
          <span>AI 보안 분석</span>
        </div>
      </div>

      <div className="header-status">
        <span className="status-dot"></span>
        시스템 정상
      </div>
    </header>
  );
}

export default Header;