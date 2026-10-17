"""블랙리스트·허용 목록 정기 점검 (월 1회 권장).

실행 (저장소 루트에서):
    python scripts/audit_lists.py               # 목록끼리 겹치는 문제 점검 (오프라인)
    python scripts/audit_lists.py --online      # 허용 목록 도메인의 만료·DNS 존재 여부도 확인

결과는 evaluation/results/list_audit.md 에 저장한다.

점검 항목
1. 블랙리스트 중 공용 주소(공식 도메인, 플랫폼 주소)와 겹치는 항목
   → 서비스는 이 항목을 호스트 단위로 확정하지 않는다 (blacklist.is_shared_host). 목록 품질 확인용.
2. 블랙리스트 중 형식이 깨진 값 (전화번호, '.com' 등) → 서비스가 읽을 때 버리는 값
3. 공용 주소인데 실제로 영향받던 항목: 이 점검 전에는 정상 주소가 피싱으로 확정되던 경우
4. (--online) 허용 목록 도메인 중 등록 정보가 없거나 DNS에 없는 도메인
   → 만료된 공식 도메인은 다른 사람이 다시 등록해 피싱에 쓸 수 있으므로 허용 목록에서 빼야 한다
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "ml_integration"))

from app.services import allowlist, blacklist  # noqa: E402
from app.services.shorteners import is_shortener_host  # noqa: E402

OUT = ROOT / "evaluation" / "results" / "list_audit.md"


def _shown(value: str) -> str:
    """보고서에 이메일 주소가 그대로 남지 않게 앞부분을 가린다 (KISA 원본에 섞여 있음)."""
    if "@" in value:
        return "***@" + value.split("@", 1)[1]
    return value


def offline() -> list[str]:
    raw_hosts = json.loads((BACKEND / "resources" / "blacklist" / "hosts.json").read_text(encoding="utf-8"))
    urls, hosts = blacklist.load_blacklist()
    broken = sorted({h for h in raw_hosts if not blacklist._valid_host(blacklist._clean_host(h))})
    shared_hosts = sorted(h for h in hosts if blacklist.is_shared_host(h))
    shortener_hosts = sorted(h for h in hosts if is_shortener_host(h))
    shared_bare = sorted(u for u in urls if "/" not in u and blacklist.is_shared_host(blacklist._extract_host(u)))
    shared_paths = [u for u in urls if "/" in u and blacklist.is_shared_host(blacklist._extract_host(u))]
    exclusions, added_urls, added_hosts = blacklist.load_reviewed()

    lines = [
        f"# 블랙리스트·허용 목록 점검 ({date.today().isoformat()})",
        "",
        f"- 블랙리스트: 주소 {len(urls):,}건, 호스트 {len(hosts):,}건 (KISA {blacklist.SOURCE_DATE} 기준)",
        f"- 허용 목록: {len(allowlist.domains()):,}개 도메인",
        f"- 검토된 예외 {len(exclusions)}건, 검토된 추가 {len(added_urls) + len(added_hosts)}건",
        "",
        "## 1. 공용 주소와 겹치는 블랙리스트 호스트",
        "호스트 단위로 확정하면 그 플랫폼·공식 사이트 전체가 피싱이 되는 항목이다. 서비스는 호스트 단위로 확정하지 않는다.",
        "",
        *[f"- `{h}`" for h in shared_hosts],
        "",
        "## 2. 경로 없이 들어 있는 공용 주소",
        "사칭 대상(공식 사이트)이나 이메일 주소가 그대로 들어간 경우로 보인다. 서비스는 확정하지 않는다.",
        "",
        *[f"- `{_shown(u)}`" for u in shared_bare],
        "",
        f"공용 주소 안의 '경로까지 일치하는' 신고 페이지 {len(shared_paths):,}건은 계속 피싱으로 확정한다.",
        "",
        "## 3. 단축 URL 호스트",
        "단축 URL은 호스트 단위로 확정하지 않고 '주의'로 표시한다 (shorteners.py).",
        "",
        *[f"- `{h}`" for h in shortener_hosts],
        "",
        f"## 4. 형식이 깨진 값 ({len(broken)}건, 서비스가 읽을 때 버림)",
        "",
        *[f"- `{_shown(h)}`" for h in broken[:40]],
        *(["- …"] if len(broken) > 40 else []),
    ]
    return lines


def online() -> list[str]:
    from app.services import reputation

    lines = ["", "## 5. 허용 목록 도메인 상태 (온라인 확인)", ""]
    problems = []
    with reputation._client() as client:
        for domain in sorted(allowlist.domains()):
            rdap = reputation._safe(reputation.rdap_lookup, domain, client)
            hosting = reputation._safe(reputation.hosting_lookup, domain, client)
            if rdap.get("status") == "not_found" or hosting.get("status") == "nxdomain":
                problems.append(f"- `{domain}`: 등록 정보 {rdap.get('status')}, DNS {hosting.get('status')}")
    lines += problems or ["- 문제 없음"]
    lines += ["", "문제가 있는 도메인은 만료·재등록 여부를 확인한 뒤 허용 목록에서 빼세요 (scripts/build_allowlist.py)."]
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="블랙리스트·허용 목록 점검")
    parser.add_argument("--online", action="store_true", help="허용 목록 도메인의 등록·DNS 상태도 확인")
    args = parser.parse_args()
    lines = offline() + (online() if args.online else [])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))
    print(f"\n저장: {OUT}")


if __name__ == "__main__":
    main()
