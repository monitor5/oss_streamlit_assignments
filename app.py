import hashlib
import json
import logging
import sys
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).parent
QUIZ_FILE = BASE_DIR / "quiz_data.json"
USERS_FILE = BASE_DIR / "users.json"

APP_TITLE = "광운대역 도착 통학 생존 퀴즈"
STUDENT_ID = "2023204020"
STUDENT_NAME = "김우현"
STUDENT_DEPARTMENT = "정보융합학부"

ANSWER_TYPE_LABELS = {
    "multiple_choice": "객관식",
    "short_answer": "단답형",
    "time_slider": "시간 추정형",
}

LOGGER = logging.getLogger("commute_quiz")
if not LOGGER.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


def log_event(action: str, **details: object) -> None:
    detail_text = " ".join(
        f"{key}={json.dumps(value, ensure_ascii=False)}"
        for key, value in details.items()
    )
    if detail_text:
        LOGGER.info("%s %s", action, detail_text)
        return
    LOGGER.info(action)


def get_log_username() -> str:
    return st.session_state.get("username") or "anonymous"


def log_page_render(location: str) -> None:
    st.session_state.render_count = st.session_state.get("render_count", 0) + 1
    log_event(
        "page_render",
        username=get_log_username(),
        location=location,
        logged_in=st.session_state.get("logged_in", False),
        quiz_submitted=st.session_state.get("quiz_submitted", False),
        render_count=st.session_state.render_count,
    )


def log_button_click(label: str, location: str, **details: object) -> None:
    log_event(
        "button_clicked",
        username=get_log_username(),
        location=location,
        label=label,
        **details,
    )


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


DEFAULT_USERS = {
    "student": {
        "password_hash": hash_password("1234"),
        "display_name": "기본 사용자",
    },
}


def render_source_links(source_links: list[dict]) -> None:
    if not source_links:
        return

    st.caption("조사 출처")
    for source in source_links:
        st.markdown(f"- [{source['label']}]({source['url']})")


@st.cache_data(show_spinner="퀴즈 데이터를 불러오는 중입니다...")
def load_quiz_data(file_path: str, file_version: int) -> list[dict]:
    """Load quiz questions from JSON and cache them for the Streamlit session."""
    del file_version  # Included only so Streamlit invalidates cache when the JSON file changes.
    with open(file_path, "r", encoding="utf-8") as quiz_file:
        return json.load(quiz_file)


@st.cache_data(show_spinner="사용자 데이터를 불러오는 중입니다...")
def load_user_data(file_path: str, file_version: int) -> dict:
    del file_version
    with open(file_path, "r", encoding="utf-8") as user_file:
        return json.load(user_file)


def ensure_user_file() -> None:
    if USERS_FILE.exists():
        return

    save_user_data(DEFAULT_USERS)


def save_user_data(users: dict) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as user_file:
        json.dump(users, user_file, ensure_ascii=False, indent=2)
        user_file.write("\n")


def initialize_state() -> None:
    ensure_user_file()
    defaults = {
        "users": load_user_data(str(USERS_FILE), USERS_FILE.stat().st_mtime_ns),
        "logged_in": False,
        "username": "",
        "quiz_submitted": False,
        "quiz_reset_version": 0,
        "score": 0,
        "results": [],
        "app_started_logged": False,
        "render_count": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    if not st.session_state.app_started_logged:
        log_event("app_start", page=APP_TITLE)
        st.session_state.app_started_logged = True


def get_answer_key(question: dict) -> str:
    return f"answer_{st.session_state.quiz_reset_version}_{question['id']}"


def is_question_answered(question: dict) -> bool:
    answer = st.session_state.get(get_answer_key(question))

    return bool(str(answer or "").strip())


def get_progress_questions(quiz_data: list[dict]) -> list[dict]:
    return [question for question in quiz_data if question["type"] != "time_slider"]


def get_unanswered_questions(quiz_data: list[dict]) -> list[tuple[int, dict]]:
    return [
        (index, question)
        for index, question in enumerate(quiz_data, start=1)
        if question["type"] != "time_slider" and not is_question_answered(question)
    ]


def render_student_header() -> None:
    st.caption(f"학부: {STUDENT_DEPARTMENT} | 학번: {STUDENT_ID} | 이름: {STUDENT_NAME}")
    st.title(APP_TITLE)
    st.write(
        "부평, 가정, 운정중앙, 구리, 동탄, 안산에서 광운대역까지 가는 통학 경로를 "
        "요금, 환승 수, 배차 리스크까지 함께 판단해 보는 Streamlit 퀴즈입니다."
    )


def login_user(username: str, password: str) -> bool:
    user = st.session_state.users.get(username.strip())
    if not user:
        return False

    if isinstance(user, str):
        return user == password

    return user.get("password_hash") == hash_password(password)


def register_user(username: str, password: str, password_confirm: str) -> tuple[bool, str]:
    username = username.strip()

    if not username or not password:
        return False, "아이디와 비밀번호를 모두 입력해 주세요."
    if username in st.session_state.users:
        return False, "이미 존재하는 아이디입니다."
    if password != password_confirm:
        return False, "비밀번호 확인이 일치하지 않습니다."
    if len(password) < 4:
        return False, "비밀번호는 4자 이상으로 입력해 주세요."

    st.session_state.users[username] = {
        "password_hash": hash_password(password),
        "display_name": username,
    }
    save_user_data(st.session_state.users)
    load_user_data.clear()
    st.session_state.logged_in = True
    st.session_state.username = username
    return True, "회원가입이 완료되었습니다. 바로 퀴즈를 시작합니다."


def render_auth() -> None:
    login_tab, signup_tab = st.tabs(["로그인", "회원가입"])

    with login_tab:
        st.subheader("로그인")
        st.info("기본 계정: student / 1234")

        with st.form("login_form"):
            username = st.text_input("아이디", key="login_username")
            password = st.text_input("비밀번호", type="password", key="login_password")
            submitted = st.form_submit_button("로그인")

        if submitted:
            login_username = username.strip()
            log_button_click(
                "로그인",
                "auth.login",
                widget_type="form_submit_button",
                username_attempt=login_username or "blank",
            )
            log_event(
                "form_submitted",
                username=get_log_username(),
                location="auth.login",
                label="로그인",
                username_attempt=login_username or "blank",
            )
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = login_username
                log_event("login_success", username=login_username)
                st.success("로그인 성공! 퀴즈 화면으로 이동합니다.")
                st.rerun()
            log_event("login_failed", username=login_username or "blank")
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    with signup_tab:
        st.subheader("회원가입")

        with st.form("signup_form"):
            new_username = st.text_input("새 아이디", key="signup_username")
            new_password = st.text_input("새 비밀번호", type="password", key="signup_password")
            password_confirm = st.text_input("비밀번호 확인", type="password", key="signup_password_confirm")
            signup_submitted = st.form_submit_button("회원가입")

        if signup_submitted:
            signup_username = new_username.strip()
            log_button_click(
                "회원가입",
                "auth.signup",
                widget_type="form_submit_button",
                username_attempt=signup_username or "blank",
            )
            log_event(
                "form_submitted",
                username=get_log_username(),
                location="auth.signup",
                label="회원가입",
                username_attempt=signup_username or "blank",
            )
            ok, message = register_user(new_username, new_password, password_confirm)
            if ok:
                log_event("signup_success", username=signup_username)
                st.success(message)
                st.rerun()
            log_event("signup_failed", username=signup_username or "blank", reason=message)
            st.error(message)


def is_correct_answer(question: dict, user_answer: str) -> bool:
    if question["type"] == "time_slider":
        return question["answer_min"] <= int(user_answer) <= question["answer_max"]

    if question["type"] == "short_answer":
        normalized_answer = str(user_answer).strip().lower().replace(" ", "")
        accepted_keywords = question.get("accepted_keywords", [])
        if accepted_keywords:
            return any(keyword.lower().replace(" ", "") in normalized_answer for keyword in accepted_keywords)
        return bool(normalized_answer)

    return user_answer == question["answer"]


def get_correct_answer_text(question: dict) -> str:
    if question["type"] == "time_slider":
        unit = question.get("unit", "분")
        return f"{question['answer_min']}~{question['answer_max']}{unit}"

    if question.get("answer"):
        return question["answer"]

    return "서술형 참여 점수"


def log_answer_change(question: dict, index: int, key: str, widget_type: str) -> None:
    answer = st.session_state.get(key, "")
    log_event(
        "answer_changed",
        username=get_log_username(),
        widget_type=widget_type,
        question=f"Q{index}",
        question_id=question["id"],
        region=question["region"],
        answer_type=question["type"],
        has_answer=bool(str(answer or "").strip()),
        answer_length=len(str(answer)),
    )


def calculate_results(quiz_data: list[dict]) -> tuple[int, list[dict]]:
    score = 0
    results = []

    for question in quiz_data:
        key = get_answer_key(question)
        user_answer = st.session_state.get(key, "")
        correct = is_correct_answer(question, user_answer)

        if correct:
            score += 1

        results.append(
            {
                "id": question["id"],
                "region": question["region"],
                "origin": question["origin"],
                "destination": question["destination"],
                "route_summary": question["route_summary"],
                "estimated_time": question["estimated_time"],
                "traffic_evidence": question.get("traffic_evidence", []),
                "source_links": question.get("source_links", []),
                "question": question["question"],
                "user_answer": user_answer,
                "correct_answer": get_correct_answer_text(question),
                "is_correct": correct,
                "explanation": question["explanation"],
                "type": question["type"],
            }
        )

    return score, results


def get_result_message(score: int) -> tuple[str, str]:
    if score <= 4:
        return "통학 입문자", "노선명과 환승역부터 차근차근 확인하면 점수가 금방 오릅니다."
    if score <= 7:
        return "현실형 통학생", "핵심 환승은 잘 잡았습니다. 지역별 예외만 조금 더 챙기면 좋습니다."
    return "광운대 통학 전략가", "광역 노선의 강점과 약점을 꽤 정확히 읽고 있습니다."


def build_region_summary(results: list[dict]) -> pd.DataFrame:
    rows = []
    regions = sorted({result["region"] for result in results})

    for region in regions:
        region_results = [result for result in results if result["region"] == region]
        total = len(region_results)
        correct = sum(1 for result in region_results if result["is_correct"])
        rows.append(
            {
                "지역": region,
                "정답 수": correct,
                "문항 수": total,
                "정답률": round(correct / total * 100, 1) if total else 0,
            }
        )

    return pd.DataFrame(rows)


def render_question(question: dict, index: int) -> None:
    st.markdown(f"### Q{index}. {question['question']}")

    meta_cols = st.columns(3)
    meta_cols[0].metric("출발", question["origin"])
    meta_cols[1].metric("도착", question["destination"])
    meta_cols[2].metric("예상", question["estimated_time"])
    st.caption(f"경로 힌트: {question['route_summary']}")

    traffic_evidence = question.get("traffic_evidence", [])
    source_links = question.get("source_links", [])
    if traffic_evidence or source_links:
        with st.expander("교통 근거 보기"):
            for evidence in traffic_evidence:
                st.write(f"- {evidence}")
            render_source_links(source_links)

    image_path = BASE_DIR / question["image"]
    if image_path.exists():
        st.image(str(image_path), width="stretch")
    else:
        st.warning(f"이미지를 찾을 수 없습니다: {question['image']}")

    key = get_answer_key(question)
    if question["type"] == "multiple_choice":
        st.radio(
            "답을 선택하세요.",
            question["options"],
            index=None,
            key=key,
            on_change=log_answer_change,
            args=(question, index, key, "radio"),
        )
    elif question["type"] == "time_slider":
        st.slider(
            question.get("slider_label", "예상 소요 시간을 맞혀 보세요."),
            min_value=question.get("min_value", 30),
            max_value=question.get("max_value", 180),
            value=question.get("default_value", question.get("min_value", 30)),
            step=question.get("step", 5),
            format=f"%d{question.get('unit', '분')}",
            key=key,
            on_change=log_answer_change,
            args=(question, index, key, "slider"),
        )
    elif question.get("accepted_keywords"):
        st.text_input(
            "짧게 답을 입력하세요.",
            key=key,
            placeholder="역 이름을 입력하세요.",
            on_change=log_answer_change,
            args=(question, index, key, "text_input"),
        )
    else:
        st.text_area(
            "본인 판단을 1문장 이상 적어 주세요.",
            key=key,
            placeholder="예: 배차 간격과 환승 동선을 고려하면 이 경로를 선택하겠습니다...",
            on_change=log_answer_change,
            args=(question, index, key, "text_area"),
        )


def render_region_chart(results: list[dict]) -> None:
    summary = build_region_summary(results)
    chart_data = summary.set_index("지역")[["정답률"]]

    st.markdown("### 지역별 이해도")
    st.bar_chart(chart_data)
    st.dataframe(summary, width="stretch", hide_index=True)

    max_rate = summary["정답률"].max()
    min_rate = summary["정답률"].min()
    strong_regions = ", ".join(summary.loc[summary["정답률"] == max_rate, "지역"])
    weak_regions = ", ".join(summary.loc[summary["정답률"] == min_rate, "지역"])

    st.info(f"가장 강한 지역: {strong_regions} ({max_rate:.1f}%)")
    st.warning(f"보완하면 좋은 지역: {weak_regions} ({min_rate:.1f}%)")


def render_results(total_questions: int) -> None:
    score = st.session_state.score
    title, message = get_result_message(score)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("총점", f"{score} / {total_questions}")
    with col2:
        st.success(f"{title}: {message}")

    render_region_chart(st.session_state.results)

    st.markdown("### 문항별 확인")
    for index, result in enumerate(st.session_state.results, start=1):
        status = "정답" if result["is_correct"] else "오답"

        with st.expander(f"Q{index}. {result['region']} - {status}"):
            st.write(f"출발/도착: {result['origin']} → {result['destination']}")
            st.write(f"경로: {result['route_summary']}")
            st.write(f"예상 소요: {result['estimated_time']}")
            if result["traffic_evidence"]:
                st.write("교통 근거:")
                for evidence in result["traffic_evidence"]:
                    st.write(f"- {evidence}")
            st.write(f"내 답: {result['user_answer']}")
            st.write(f"기준 답: {result['correct_answer']}")
            st.caption(result["explanation"])
            render_source_links(result["source_links"])


@st.dialog("최종 결과", width="large")
def render_results_dialog(quiz_data: list[dict]) -> None:
    render_results(len(quiz_data))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("결과 창 닫기", key="close_result_dialog", width="stretch"):
            log_button_click("결과 창 닫기", "results.dialog")
            log_event("result_dialog_close", username=st.session_state.username)
            st.rerun()
    with col2:
        if st.button("다시 풀기", key="retry_quiz_from_dialog", width="stretch"):
            log_button_click("다시 풀기", "results.dialog")
            log_event("quiz_retry", username=st.session_state.username, source="dialog")
            reset_quiz()
            st.rerun()


def render_quiz(quiz_data: list[dict]) -> None:
    st.subheader("퀴즈")
    question_types = sorted({ANSWER_TYPE_LABELS.get(question["type"], question["type"]) for question in quiz_data})
    st.caption(
        f"{', '.join(question_types)} 문항이 섞여 있습니다. 모든 문항은 1점이며, 참여형 서술 문항은 공백이 아니면 점수로 인정합니다."
    )

    for index, question in enumerate(quiz_data, start=1):
        render_question(question, index)
        st.divider()

    submitted = st.button("결과 보기", type="primary")

    if submitted:
        unanswered = get_unanswered_questions(quiz_data)
        answered_count = len(get_progress_questions(quiz_data)) - len(unanswered)
        log_button_click("결과 보기", "quiz.main", answered_count=answered_count)

        if unanswered:
            unanswered_numbers = ", ".join(str(index) for index, _ in unanswered)
            log_event(
                "result_submit_blocked",
                username=st.session_state.username,
                unanswered_count=len(unanswered),
                unanswered_questions=unanswered_numbers,
            )
            st.warning(f"아직 답하지 않은 문제가 있습니다: {unanswered_numbers}번")
            return

        score, results = calculate_results(quiz_data)
        st.session_state.score = score
        st.session_state.results = results
        st.session_state.quiz_submitted = True
        log_event("result_submit_success", username=st.session_state.username, score=score, total=len(quiz_data))
        st.balloons()
        render_results_dialog(quiz_data)

    if st.session_state.quiz_submitted:
        st.success("결과가 계산되었습니다. 아래 버튼으로 결과 창을 다시 열거나 퀴즈를 초기화할 수 있습니다.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("결과 창 열기", key="open_result_dialog", width="stretch"):
                log_button_click("결과 창 열기", "quiz.results_controls")
                log_event("result_dialog_open", username=st.session_state.username, score=st.session_state.score)
                render_results_dialog(quiz_data)
        with col2:
            if st.button("다시 풀기", key="retry_quiz", width="stretch"):
                log_button_click("다시 풀기", "quiz.results_controls")
                log_event("quiz_retry", username=st.session_state.username, source="main")
                reset_quiz()
                st.rerun()


def reset_quiz() -> None:
    st.session_state.quiz_reset_version = st.session_state.get("quiz_reset_version", 0) + 1

    for key in list(st.session_state.keys()):
        if str(key).startswith("answer_"):
            st.session_state.pop(key, None)

    st.session_state.quiz_submitted = False
    st.session_state.score = 0
    st.session_state.results = []


def render_sidebar(quiz_data: list[dict]) -> None:
    st.sidebar.header("앱 정보")
    st.sidebar.write(f"로그인 사용자: {st.session_state.username}")
    st.sidebar.write(f"문항 수: {len(quiz_data)}개")

    unanswered = get_unanswered_questions(quiz_data)
    progress_questions = get_progress_questions(quiz_data)
    answered_count = len(progress_questions) - len(unanswered)
    progress_total = len(progress_questions)
    progress = answered_count / progress_total if progress_total else 0

    st.sidebar.subheader("풀이 진행률")
    st.sidebar.progress(progress, text=f"{answered_count} / {progress_total}문항 완료")

    if unanswered:
        unanswered_labels = [f"Q{index}. {question['region']}" for index, question in unanswered]
        st.sidebar.warning("미답변 문항: " + ", ".join(unanswered_labels))
    else:
        st.sidebar.success("모든 문항에 답했습니다.")

    st.sidebar.caption("퀴즈 데이터는 quiz_data.json에서 읽고 @st.cache_data로 캐싱합니다.")
    st.sidebar.caption("회원가입 정보는 users.json에 저장되어 서버 재시작 후에도 유지됩니다.")

    if st.sidebar.button("퀴즈 데이터 캐시 새로고침"):
        log_button_click("퀴즈 데이터 캐시 새로고침", "sidebar")
        load_quiz_data.clear()
        log_event("quiz_cache_refresh", username=st.session_state.username)
        reset_quiz()
        st.rerun()

    if st.sidebar.button("로그아웃"):
        log_button_click("로그아웃", "sidebar")
        log_event("logout", username=st.session_state.username)
        st.session_state.logged_in = False
        st.session_state.username = ""
        reset_quiz()
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🚇",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_state()
    log_page_render("quiz" if st.session_state.logged_in else "auth")
    render_student_header()

    if not st.session_state.logged_in:
        render_auth()
        return

    quiz_data = load_quiz_data(str(QUIZ_FILE), QUIZ_FILE.stat().st_mtime_ns)
    render_quiz(quiz_data)
    render_sidebar(quiz_data)


if __name__ == "__main__":
    main()
