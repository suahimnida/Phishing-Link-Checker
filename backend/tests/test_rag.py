from types import SimpleNamespace
import pytest

from app.services import rag

FAKE_CASES = [
    {"url": "http://evil.tk/login", "label": 1, "description": "...", "similarity": 0.91},
    {"url": "https://naver.com", "label": 0, "description": "...", "similarity": 0.52},
]


EVIDENCE = [
    {"id": "E1", "source": "ML 모델", "text": "위험 점수는 99점입니다.", "used_in_verdict": True},
    {"id": "E2", "source": "탐지 결과 · URL 구조", "text": "도메인에 로그인 단어가 있습니다.", "used_in_verdict": False},
]
GUIDES = [{"id": "G1", "title": "링크 대신 공식 경로로 확인하기", "text": "공식 앱으로 확인한다.", "source": "KISA"}]


class FakeClaude:
    def __init__(self, text):
        self.text = text
        self.prompts = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.prompts.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.text)], stop_reason="end_turn")


@pytest.fixture
def with_claude(monkeypatch):
    def use(text):
        fake = FakeClaude(text)
        monkeypatch.setattr(rag, "_state", {"client": fake})
        return fake
    return use


def test_compose_returns_cited_explanation(with_claude):
    fake = with_claude("도메인에 로그인 단어가 있어 위험합니다 [E2]. 위험 점수도 높습니다 [E1]. 공식 앱으로 확인하세요 [G1].")
    text = rag.compose(EVIDENCE, GUIDES)
    assert text.endswith("[G1].")
    prompt = fake.prompts[0]
    assert "판정하지 않습니다" in prompt["system"]
    assert "[E2] (탐지 결과 · URL 구조)" in prompt["messages"][0]["content"] and "[G1]" in prompt["messages"][0]["content"]


@pytest.mark.parametrize(
    "bad",
    [
        "출처 없이 위험하다고만 씁니다.",
        "위험합니다 [E9].", 
        "위험합니다 [E1]. 출처 없는 문장입니다.",
        "118로 전화하세요 [G1].",  
        "https://evil.example 로 가지 마세요 [E1].",
    ],
)
def test_compose_rejects_unsourced_text(with_claude, bad):
    with_claude(bad)
    assert rag.compose(EVIDENCE, GUIDES) is None 


def test_compose_without_claude_returns_none(monkeypatch):
    monkeypatch.setattr(rag, "_state", None)
    assert rag.compose(EVIDENCE, GUIDES) is None


def test_similar_without_rag_returns_empty(monkeypatch):
    monkeypatch.setattr(rag, "_state", None)
    assert rag.similar("https://example.com") == rag.RagResult()


def test_load_rag_without_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "_state", None)  # 다른 테스트가 서버를 띄우며 RAG를 이미 불러왔을 수 있다
    monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path))
    assert rag.load_rag() is False
    assert rag._state is None



@pytest.fixture
def real_rag(monkeypatch):
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(rag, "_state", None)
    assert rag.load_rag() is True
    assert rag._state["client"] is None


def labels_of(url):
    return [c.label for c in rag.similar(url).similar_cases]


def test_phishing_url_finds_phishing_cases(real_rag):
    assert labels_of("http://secure-paypal-login.verify-account.tk") == [1, 1, 1, 1, 1]
    assert labels_of("http://m.login.secure.naver-account-verify-center.xyz/update?id=1029") == [1] * 5


def test_cases_are_balanced_and_not_homepage_biased(real_rag):
    # 사례 목록은 v2 학습 데이터에서 라벨별로 같은 수, 경로 있는/없는 URL 반반 (scripts/build_similar_cases.py)
    meta = rag._state["metadata"]
    assert len(meta) == 5000 and int(meta["label"].sum()) == 2500
    legit = meta[meta["label"] == 0]["url"]
    assert legit.str.startswith("https://www.").mean() < 0.5


def test_normal_urls_with_path_are_not_all_phishing_cases(real_rag):
    # 기존 데이터에서는 경로 있는 정상 URL의 유사 사례가 거의 전부 피싱이었다 (QA)
    urls = ["https://myschool.ac.kr/notice/view?id=12", "https://news.daum.net/article/123",
            "https://www.youtube.com/watch?v=abc", "https://github.com/suahimnida/TEST"]
    labels = [l for u in urls for l in labels_of(u)]
    assert sum(labels) <= len(labels) * 0.6


def test_similarity_is_sorted_and_in_range(real_rag):
    cases = rag.similar("http://secure-paypal-login.verify-account.tk").similar_cases
    sims = [c.similarity for c in cases]
    assert sims == sorted(sims, reverse=True)
    assert all(0 < s <= 1 for s in sims)
    homepage = rag.similar("https://www.naver.com").similar_cases[0].similarity
    assert homepage > sims[0]


def test_search_features_keeps_ml_features_except_brand_keyword():
    feats = rag.search_features("https://www.naver.com")
    assert feats["suspicious_keyword_count"] == 0
    assert rag.search_features("http://naver-login.xyz")["suspicious_keyword_count"] == 2
