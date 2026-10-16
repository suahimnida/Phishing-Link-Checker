"""결과 화면의 '이미 눌렀다면?' 안내.

리포트(report.py)와 같은 조치(followup.ACTIONS)와 연락처(report.CONTACTS)를 그대로 쓴다.
한 곳에서 관리해 결과 화면과 리포트의 안내가 어긋나지 않게 하고, LLM 없이 바로 응답한다.
'아직 접속하지 않은 경우'는 결과 화면 맨 위의 '지금 할 일'이 대신하므로 여기서는 뺀다.
"""

from app.schemas import ReportContact, ResponseAction, ResponseGuide, ResponseSituation
from app.services.followup import ACTIONS, SITUATIONS
from app.services.report import CONTACTS

# 상황마다 보여 줄 연락처 (CONTACTS의 순서 번호). 과하지 않게 상황에 꼭 필요한 곳만 연결한다
_KISA, _POLICE, _FSS, _PAYINFO, _MSAFER = range(5)
CONTACTS_BY_SITUATION = {
    "visited": [_KISA],
    "entered_account": [_KISA],
    "entered_personal": [_FSS, _MSAFER],
    "financial_loss": [_POLICE, _FSS, _PAYINFO],
    "app_installed": [_KISA, _POLICE],
}

# 화면에 보여 줄 짧은 상황 이름 (사용자가 고르는 버튼)
LABELS = {
    "visited": "링크만 열어 봤어요",
    "entered_account": "아이디·비밀번호를 입력했어요",
    "entered_personal": "주민등록번호·계좌번호 같은 개인정보를 입력했어요",
    "financial_loss": "돈을 보냈거나 카드 정보를 입력했어요",
    "app_installed": "앱이나 파일을 설치했어요",
}


def build() -> ResponseGuide:
    situations = []
    for sid, _ in SITUATIONS:
        if sid not in CONTACTS_BY_SITUATION:
            continue
        actions = [
            ResponseAction(id=aid, title=a["title"], steps=a["steps"])
            for aid, a in ACTIONS.items()
            if a["situation"] == sid
        ]
        contacts: list[ReportContact] = [CONTACTS[i] for i in CONTACTS_BY_SITUATION[sid]]
        situations.append(ResponseSituation(id=sid, label=LABELS[sid], actions=actions, contacts=contacts))
    return ResponseGuide(situations=situations)
