"""업무 매뉴얼 대시보드 (v2)

- 매뉴얼은 GitHub 저장소의 manuals/대분류/중분류/문서.md 로 저장됩니다.
- 화면의 '작성·수정' 메뉴에서 바로 쓰고 고칠 수 있습니다.
- Streamlit Secrets 설정:
    GITHUB_TOKEN  = "github_pat_..."        # 저장소 Contents 읽기/쓰기 권한
    GITHUB_REPO   = "parkjh309/work-manual"
    EDIT_PASSWORD = "원하는비밀번호"          # 선택: 작성 화면 잠금
"""
import base64
import calendar
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
import streamlit as st


# ===== 설정 ============================================================
def secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:  # secrets 파일이 아예 없을 때
        return default


TOKEN = secret("GITHUB_TOKEN")
REPO = secret("GITHUB_REPO")
BRANCH = secret("GITHUB_BRANCH", "main")
EDIT_PW = secret("EDIT_PASSWORD")
USE_GH = bool(TOKEN and REPO)

ROOT = Path(__file__).parent / "manuals"
API = "https://api.github.com"
TZ = ZoneInfo("Asia/Seoul")
WEEKDAYS = "월화수목금토일"

FREQS = {
    "매일": {"color": "#d9480f", "icon": "🟠", "hint": "예: 오전"},
    "매주": {"color": "#1864ab", "icon": "🔵", "hint": "요일 예: 월, 목"},
    "매월": {"color": "#2b8a3e", "icon": "🟢", "hint": "날짜 예: 5일, 말일"},
    "매년": {"color": "#6741d9", "icon": "🟣", "hint": "월 예: 12월, 10~11월, 6,12월"},
    "수시": {"color": "#5c677d", "icon": "⚪", "hint": "비워 두어도 됩니다"},
    "참고": {"color": "#868e96", "icon": "📎", "hint": "비워 두어도 됩니다"},
}
TASK_FREQS = ["매일", "매주", "매월", "매년", "수시"]

TEMPLATE = """## 개요
이 업무가 무엇이고 왜 하는지

## 처리 절차
1. 
2. 
3. 

## 주의사항
- 

## 참고 양식/링크
- 
"""


# ===== GitHub 연동 =====================================================
def gh_headers() -> dict:
    return {"Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def gh_error(r: requests.Response) -> str:
    try:
        msg = r.json().get("message", "")
    except Exception:
        msg = r.text[:200]
    return f"{r.status_code} {msg}"


@st.cache_data(ttl=60, show_spinner=False)
def gh_tree() -> list:
    """manuals/ 아래 .md 파일 목록 [(경로, sha)]"""
    r = requests.get(f"{API}/repos/{REPO}/git/trees/{quote(BRANCH)}",
                     headers=gh_headers(), params={"recursive": 1}, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(gh_error(r))
    return sorted((t["path"], t["sha"]) for t in r.json()["tree"]
                  if t["type"] == "blob" and t["path"].startswith("manuals/")
                  and t["path"].endswith(".md"))


@st.cache_data(show_spinner=False)
def gh_blob(sha: str) -> str:
    """파일 내용 (sha가 같으면 내용도 같으므로 영구 캐시)"""
    r = requests.get(f"{API}/repos/{REPO}/git/blobs/{sha}",
                     headers=gh_headers(), timeout=15)
    if r.status_code != 200:
        raise RuntimeError(gh_error(r))
    return base64.b64decode(r.json()["content"]).decode("utf-8", errors="replace")


def gh_current_sha(path: str):
    r = requests.get(f"{API}/repos/{REPO}/contents/{quote(path)}",
                     headers=gh_headers(), params={"ref": BRANCH}, timeout=15)
    return r.json().get("sha") if r.status_code == 200 else None


def gh_put(path: str, text: str, message: str):
    data = {"message": message, "branch": BRANCH,
            "content": base64.b64encode(text.encode("utf-8")).decode()}
    sha = gh_current_sha(path)
    if sha:  # 이미 있는 파일을 덮어쓸 때는 sha가 반드시 필요 (없으면 422)
        data["sha"] = sha
    r = requests.put(f"{API}/repos/{REPO}/contents/{quote(path)}",
                     headers=gh_headers(), json=data, timeout=15)
    if r.status_code not in (200, 201):
        raise RuntimeError(gh_error(r))


def gh_delete(path: str, message: str):
    sha = gh_current_sha(path)
    if not sha:
        return
    r = requests.delete(f"{API}/repos/{REPO}/contents/{quote(path)}",
                        headers=gh_headers(),
                        json={"message": message, "sha": sha, "branch": BRANCH},
                        timeout=15)
    if r.status_code != 200:
        raise RuntimeError(gh_error(r))


# ===== 매뉴얼 읽기 =====================================================
def clean(name: str) -> str:
    """'01_예산' -> '예산'"""
    return re.sub(r"^\d+[_\-\s.]*", "", name)


def prefix_num(name: str) -> int:
    m = re.match(r"^(\d+)", name)
    return int(m.group(1)) if m else 0


def parse(rel: str, text: str) -> dict:
    """rel: manuals/ 기준 상대경로 (예: 01_예산/03_결산/01_월마감.md)"""
    meta, body = {}, text.replace("\r\n", "\n")
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2]
    body = body.strip()

    parts = rel.split("/")
    title = clean(Path(parts[-1]).stem)
    m = re.search(r"^#\s+(.+)$", body, re.M)
    if m:
        title = m.group(1).strip()
        body = (body[: m.start()] + body[m.end():]).strip()

    freq = meta.get("주기", "참고")
    return {
        "key": rel,
        "cat_dir": parts[0] if len(parts) > 1 else "기타",
        "sub_dir": parts[1] if len(parts) > 2 else "",
        "cat": clean(parts[0]) if len(parts) > 1 else "기타",
        "sub": clean(parts[1]) if len(parts) > 2 else "일반",
        "title": title,
        "freq": freq if freq in FREQS else "참고",
        "when": meta.get("시기", ""),
        "owner": meta.get("담당", ""),
        "body": body,
    }


def load_docs() -> tuple:
    """(문서 목록, 출처 설명)"""
    if USE_GH:
        try:
            docs = [parse(p.removeprefix("manuals/"), gh_blob(sha))
                    for p, sha in gh_tree()]
            return docs, "github"
        except Exception as e:
            st.sidebar.warning(f"GitHub에서 읽지 못해 배포된 파일로 표시합니다.\n\n({e})")
    if not ROOT.exists():
        return [], "local"
    docs = [parse(p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8", errors="replace"))
            for p in sorted(ROOT.rglob("*.md"))]
    return docs, "local"


def build_text(title, freq, when, owner, body) -> str:
    head = f"---\n주기: {freq}\n"
    if when.strip():
        head += f"시기: {when.strip()}\n"
    if owner.strip():
        head += f"담당: {owner.strip()}\n"
    return head + f"---\n\n# {title.strip()}\n\n{body.strip()}\n"


def safe_name(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|#%\[\]]', "", s).strip()
    return re.sub(r"\s+", "", s) or "제목없음"


def next_prefix(names) -> str:
    return f"{max([prefix_num(n) for n in names] + [0]) + 1:02d}"


# ===== 일정 판단 =======================================================
def numbers(s: str) -> list:
    """'10~11월' -> [10, 11], '6,12월' -> [6, 12], '5일' -> [5]"""
    m = re.search(r"(\d+)\s*[~\-]\s*(\d+)", s)
    if m:
        return list(range(int(m.group(1)), int(m.group(2)) + 1))
    return [int(x) for x in re.findall(r"\d+", s)]


def is_today(d: dict, now: datetime) -> bool:
    when = d["when"]
    if d["freq"] == "매일":
        return True
    if d["freq"] == "매주":
        return WEEKDAYS[now.weekday()] in when.replace("요일", "")
    if d["freq"] == "매월":
        if "말일" in when:
            return now.day == calendar.monthrange(now.year, now.month)[1]
        return now.day in numbers(when)
    return False


def is_this_month(d: dict, now: datetime) -> bool:
    if d["freq"] == "매월":
        return True
    if d["freq"] == "매년":
        return now.month in numbers(d["when"])
    return False


def sort_key(d: dict):
    return (list(FREQS).index(d["freq"]), d["cat_dir"], d["sub_dir"], d["title"])


# ===== 화면 공통 =======================================================
st.set_page_config(page_title="업무 매뉴얼", page_icon="📘", layout="wide")
st.markdown("""
<style>
.badge {display:inline-block; padding:2px 10px; border-radius:999px;
        font-size:0.8rem; font-weight:600; margin-right:6px;}
.path  {color:#868e96; font-size:0.85rem;}
</style>""", unsafe_allow_html=True)


def badge(freq: str, when: str = "") -> str:
    c = FREQS[freq]["color"]
    label = freq + (f" {when}" if when else "")
    return (f"<span class='badge' style='background:{c}1a;color:{c};"
            f"border:1px solid {c}66'>{label}</span>")


def show_doc(d: dict, show_path: bool = True):
    when = f" ({d['when']})" if d["when"] else ""
    with st.expander(f"{FREQS[d['freq']]['icon']} {d['title']}{when}"):
        info = badge(d["freq"], d["when"])
        if show_path:
            info += f"<span class='path'>{d['cat']} › {d['sub']}</span>"
        if d["owner"]:
            info += f"<span class='path'> · 담당 {d['owner']}</span>"
        st.markdown(info, unsafe_allow_html=True)
        st.markdown(d["body"] or "_내용을 작성해 주세요._")


def task_list(items: list, empty: str, prefix: str):
    if not items:
        st.caption(empty)
        return
    for d in sorted(items, key=sort_key):
        st.checkbox(f"{FREQS[d['freq']]['icon']} {d['title']}  —  {d['cat']} › {d['sub']}",
                    key=f"{prefix}:{d['key']}")


docs, source = load_docs()
now = datetime.now(TZ)
cat_dirs = sorted({d["cat_dir"] for d in docs})

PAGES = ["🏠 홈", "📂 분류별 보기", "🗓️ 주기별 보기", "🔍 검색", "✏️ 작성·수정"]
with st.sidebar:
    st.title("📘 업무 매뉴얼")
    page = st.radio("메뉴", PAGES, label_visibility="collapsed")
    st.divider()
    st.caption("주기 색상")
    st.markdown(" ".join(badge(f) for f in TASK_FREQS), unsafe_allow_html=True)

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

if not docs and page != "✏️ 작성·수정":
    st.info("아직 매뉴얼이 없습니다. 왼쪽 '✏️ 작성·수정' 메뉴에서 첫 매뉴얼을 작성해 보세요.")
    st.stop()

# ----- 홈 -------------------------------------------------------------
if page == "🏠 홈":
    st.header(f"{now:%Y년 %m월 %d일} ({WEEKDAYS[now.weekday()]})")
    cols = st.columns(max(len(cat_dirs), 1))
    for col, cd in zip(cols, cat_dirs):
        col.metric(clean(cd), f"{sum(1 for d in docs if d['cat_dir'] == cd)}건")

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("오늘 할 일")
        task_list([d for d in docs if is_today(d, now)],
                  "오늘 정해진 업무가 없습니다.", "today")
    with right:
        st.subheader(f"{now.month}월에 할 일")
        task_list([d for d in docs if is_this_month(d, now)],
                  "이번 달 정해진 월간·연간 업무가 없습니다.", "month")
    st.caption("체크 표시는 화면을 새로 고치면 초기화됩니다.")

# ----- 분류별 ---------------------------------------------------------
elif page == "📂 분류별 보기":
    cd = st.sidebar.selectbox("대분류", cat_dirs, format_func=clean)
    pick = st.sidebar.multiselect("주기 필터", list(FREQS), default=list(FREQS))
    st.header(clean(cd))
    in_cat = [d for d in docs if d["cat_dir"] == cd]
    subs = sorted({d["sub_dir"] for d in in_cat})
    for tab, sd in zip(st.tabs([clean(s) if s else "일반" for s in subs]), subs):
        with tab:
            items = [d for d in in_cat if d["sub_dir"] == sd and d["freq"] in pick]
            if not items:
                st.caption("선택한 주기에 해당하는 매뉴얼이 없습니다.")
            for d in sorted(items, key=sort_key):
                show_doc(d, show_path=False)

# ----- 주기별 ---------------------------------------------------------
elif page == "🗓️ 주기별 보기":
    st.header("주기별 업무")
    freqs = [f for f in FREQS if any(d["freq"] == f for d in docs)]
    for tab, f in zip(st.tabs([f"{FREQS[f]['icon']} {f}" for f in freqs]), freqs):
        with tab:
            for cd in cat_dirs:
                items = [d for d in docs if d["freq"] == f and d["cat_dir"] == cd]
                if items:
                    st.markdown(f"**{clean(cd)}**")
                    for d in sorted(items, key=sort_key):
                        show_doc(d)

# ----- 검색 -----------------------------------------------------------
elif page == "🔍 검색":
    st.header("매뉴얼 검색")
    q = st.text_input("검색어", placeholder="예: 결산, 견적, 식수, 계약")
    if q:
        hits = [d for d in docs if q in d["title"] or q in d["body"]]
        st.caption(f"{len(hits)}건 찾음")
        for d in sorted(hits, key=sort_key):
            show_doc(d)

# ----- 작성·수정 ------------------------------------------------------
else:
    st.header("매뉴얼 작성·수정")

    if not USE_GH:
        st.warning("작성 기능을 쓰려면 Streamlit 앱 설정의 Secrets에 "
                   "GITHUB_TOKEN과 GITHUB_REPO를 입력해 주세요.")
        st.code('GITHUB_TOKEN = "github_pat_..."\nGITHUB_REPO = "parkjh309/work-manual"\n'
                'EDIT_PASSWORD = "편집용 비밀번호"', language="toml")
        st.stop()

    if EDIT_PW and not st.session_state.get("authed"):
        pw = st.text_input("편집 비밀번호", type="password")
        if st.button("확인"):
            if pw == EDIT_PW:
                st.session_state["authed"] = True
                st.rerun()
            st.error("비밀번호가 맞지 않습니다.")
        st.stop()

    mode = st.radio("작업", ["새 매뉴얼", "기존 매뉴얼 수정"], horizontal=True,
                    label_visibility="collapsed")
    doc = None
    if mode == "기존 매뉴얼 수정":
        if not docs:
            st.info("수정할 매뉴얼이 없습니다.")
            st.stop()
        doc = st.selectbox("수정할 매뉴얼", sorted(docs, key=lambda d: d["key"]),
                           format_func=lambda d: f"{d['cat']} › {d['sub']} › {d['title']}")
        sfx = "e:" + doc["key"]
    else:
        sfx = f"n:{st.session_state.setdefault('form_n', 0)}"

    NEW_CAT, NO_SUB, NEW_SUB = "➕ 새 대분류 만들기", "(중분류 없음)", "➕ 새 중분류 만들기"

    # 대분류
    c1, c2 = st.columns(2)
    cat_opts = cat_dirs + [NEW_CAT]
    cat_sel = c1.selectbox("대분류", cat_opts,
                           index=cat_opts.index(doc["cat_dir"]) if doc else 0,
                           format_func=lambda x: x if x == NEW_CAT else clean(x),
                           key=f"cat|{sfx}")
    new_cat = c1.text_input("새 대분류 이름", key=f"newcat|{sfx}",
                            placeholder="예: 용역관리") if cat_sel == NEW_CAT else ""

    # 중분류
    sub_dirs = sorted({d["sub_dir"] for d in docs if d["cat_dir"] == cat_sel and d["sub_dir"]})
    sub_opts = sub_dirs + [NO_SUB, NEW_SUB]
    sub_idx = 0
    if doc and doc["cat_dir"] == cat_sel:
        sub_idx = sub_opts.index(doc["sub_dir"]) if doc["sub_dir"] else sub_opts.index(NO_SUB)
    elif not sub_dirs:
        sub_idx = sub_opts.index(NO_SUB)
    sub_sel = c2.selectbox("중분류", sub_opts, index=sub_idx,
                           format_func=lambda x: x if x in (NO_SUB, NEW_SUB) else clean(x),
                           key=f"sub|{sfx}|{cat_sel}")
    new_sub = c2.text_input("새 중분류 이름", key=f"newsub|{sfx}",
                            placeholder="예: 계약관리") if sub_sel == NEW_SUB else ""

    # 업무 정보
    title = st.text_input("업무명", value=doc["title"] if doc else "", key=f"title|{sfx}",
                          placeholder="예: 용역업체 계약관리")
    c3, c4, c5 = st.columns([1, 1, 1])
    freq_list = list(FREQS)
    freq = c3.selectbox("주기", freq_list,
                        index=freq_list.index(doc["freq"]) if doc else freq_list.index("매월"),
                        key=f"freq|{sfx}")
    when = c4.text_input("시기", value=doc["when"] if doc else "", key=f"when|{sfx}",
                         placeholder=FREQS[freq]["hint"])
    owner = c5.text_input("담당", value=doc["owner"] if doc else "", key=f"owner|{sfx}")
    body = st.text_area("매뉴얼 내용", value=doc["body"] if doc else TEMPLATE,
                        height=380, key=f"body|{sfx}",
                        help="## 은 소제목, 1. 은 번호 목록, - 는 글머리 기호가 됩니다.")

    with st.expander("미리보기"):
        st.markdown(badge(freq, when), unsafe_allow_html=True)
        st.markdown(f"### {title or '업무명'}")
        st.markdown(body)

    # 저장 경로 계산
    def target_path():
        if cat_sel == NEW_CAT:
            if not new_cat.strip():
                raise ValueError("새 대분류 이름을 입력해 주세요.")
            cdir = f"{next_prefix(cat_dirs)}_{safe_name(new_cat)}"
        else:
            cdir = cat_sel
        if sub_sel == NEW_SUB:
            if not new_sub.strip():
                raise ValueError("새 중분류 이름을 입력해 주세요.")
            sdir = f"{next_prefix(sub_dirs)}_{safe_name(new_sub)}"
        else:
            sdir = "" if sub_sel == NO_SUB else sub_sel
        folder = f"{cdir}/{sdir}" if sdir else cdir

        if doc and doc["key"].rsplit("/", 1)[0] == folder:
            return doc["key"]  # 같은 폴더면 파일 이름 유지
        siblings = [d["key"].rsplit("/", 1)[-1] for d in docs
                    if d["key"].rsplit("/", 1)[0] == folder]
        return f"{folder}/{next_prefix(siblings)}_{safe_name(title)}.md"

    b1, b2, _ = st.columns([1, 1, 4])
    if b1.button("💾 저장", type="primary"):
        try:
            if not title.strip():
                raise ValueError("업무명을 입력해 주세요.")
            rel = target_path()
            text = build_text(title, freq, when, owner, body)
            with st.spinner("GitHub에 저장하는 중..."):
                gh_put(f"manuals/{rel}", text, f"매뉴얼 {'수정' if doc else '추가'}: {title.strip()}")
                if doc and rel != doc["key"]:  # 분류를 옮긴 경우 기존 파일 삭제
                    gh_delete(f"manuals/{doc['key']}", f"매뉴얼 이동: {title.strip()}")
            gh_tree.clear()
            if not doc:
                st.session_state["form_n"] += 1  # 입력칸 비우기
            st.session_state["flash"] = f"'{title.strip()}' 저장했습니다."
            st.rerun()
        except ValueError as e:
            st.warning(str(e))
        except Exception as e:
            st.error(f"저장하지 못했습니다: {e}")

    if doc:
        with b2.popover("🗑️ 삭제"):
            st.write(f"'{doc['title']}' 매뉴얼을 삭제할까요?")
            if st.button("삭제하기", type="primary"):
                try:
                    with st.spinner("삭제하는 중..."):
                        gh_delete(f"manuals/{doc['key']}", f"매뉴얼 삭제: {doc['title']}")
                    gh_tree.clear()
                    st.session_state["flash"] = f"'{doc['title']}' 삭제했습니다."
                    st.rerun()
                except Exception as e:
                    st.error(f"삭제하지 못했습니다: {e}")
