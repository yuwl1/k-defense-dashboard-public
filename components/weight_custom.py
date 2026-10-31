"""가중치 커스텀 공용 부품 — 02_company(기업별 수출 기회)·04_country(국가별 상세) 공통

- 가중치는 기업별로 따로 저장: st.session_state.export_weights_by_company = {기업명: {draft, applied, locked}}
  02(기업 탭)와 04(기업 선택)에서 같은 기업을 고르면 같은 가중치가 보이고, 바꾸면 양쪽에 반영됨
- 기본값·초기화 값 = dashboard_score.py가 계산한 그 기업의 CRITIC 가중치 (기본값이면 스크립트 결과 그대로)
- 슬라이더·숫자 입력칸은 지금 화면의 기업 값으로 채움 (기업을 바꾸거나 다른 화면에서 돌아올 때 다시 채움)

사용:
    from components.weight_custom import init_weight_state, render_weight_popover, custom_weights
    init_weight_state(company)            # 위젯을 그리기 전에 (기업이 정해진 뒤)
    render_weight_popover(company)        # 버튼을 놓을 자리에서
    weights = custom_weights(company)     # None = 기본값(dashboard_score.py 결과), dict = 사용자 가중치
"""
from pathlib import Path

import streamlit as st


def loaded_mtime() -> int:
    """이 파일의 현재 수정 시각 — 페이지에서 LOADED_MTIME과 비교해 바뀌었으면 다시 불러옴"""
    return Path(__file__).stat().st_mtime_ns


LOADED_MTIME = loaded_mtime()

# 가중치 합계: 10000 = 100.00%
# 소수점 오차를 방지하기 위해 0.01% 단위 정수로 관리 (소수점 둘째 자리까지 설정)
TOTAL = 10000
UNIT = TOTAL // 100   # 1% = 100

WEIGHT_NAMES = [
    "HHI",
    "국방비",
    "무기 매칭도",
    "협력 관계",
    "GPI",
    "신용도",      # Fitch 국가 신용등급을 0~100점으로 변환 (2026-10 추가)
]

# CRITIC 가중치를 계산할 수 없을 때만 쓰는 예비 기본값
# (기존 5개 비율 22.5/22.5/22.5/17.5/15를 90%로 줄이고 신용도 10% 추가 → 합계 100%)
DEFAULT_WEIGHTS = [2025, 2025, 2025, 1575, 1350, 1000]


def default_weights(company):
    """기업의 기본 가중치 = dashboard_score.py의 CRITIC 가중치 % (round_to_100 결과, 합계 100.00%)
    → 0.01% 단위 정수 리스트(합계 10000). 계산은 스크립트에서 하고 여기서는 단위만 바꿈"""
    try:
        from components.export_score import critic_weights_pct
        pct = critic_weights_pct(company)         # {지표 이름: %}
        values = [round(pct[name] * UNIT) for name in WEIGHT_NAMES]
        return values if sum(values) == TOTAL else DEFAULT_WEIGHTS.copy()
    except Exception:
        return DEFAULT_WEIGHTS.copy()


def _store():
    """기업별 가중치 저장소 {기업명: {"draft", "applied", "locked"}}"""
    if "export_weights_by_company" not in st.session_state:
        st.session_state.export_weights_by_company = {}
    return st.session_state.export_weights_by_company


def _company_state(company):
    """기업 가중치 상태 (없거나 지표 개수가 바뀌었으면 그 기업의 CRITIC 기본값으로 생성)"""
    store = _store()
    state = store.get(company)
    # 지표 개수나 단위(합계)가 바뀐 예전 저장값은 기본값으로 다시 만듦
    if (not state or len(state.get("draft", [])) != len(WEIGHT_NAMES)
            or sum(state["draft"]) != TOTAL or sum(state["applied"]) != TOTAL):
        default = default_weights(company)
        state = {"draft": default.copy(), "applied": default.copy(), "locked": set(), "base": default.copy()}
        store[company] = state
    else:
        # 기본값(CRITIC) 계산이 바뀌었는데 사용자가 손대지 않은 상태면 새 기본값으로 맞춤
        # (예: 반올림 규칙 변경 → 예전 기본값이 '사용자 조정'으로 잘못 보이는 것 방지)
        default = default_weights(company)
        base = state.get("base", state["applied"])
        if base != default and state["applied"] == base and state["draft"] == base:
            state.update({"draft": default.copy(), "applied": default.copy(), "base": default.copy()})
    return state


def _state():
    """지금 위젯(슬라이더·입력칸)이 보여주고 있는 기업의 상태 — 콜백에서 사용"""
    return _company_state(st.session_state.get("export_weight_company"))


def init_weight_state(company):
    """가중치 상태 준비 + 슬라이더·입력칸을 이 기업의 값으로 채움 (위젯을 그리기 전에 호출)"""
    # 예전(기업 공통) 저장값은 더 이상 쓰지 않음
    for old_key in ("export_draft_weights", "export_applied_weights", "export_locked_weights"):
        st.session_state.pop(old_key, None)

    state = _company_state(company)
    widgets_missing = any(
        f"export_weight_slider_{i}" not in st.session_state for i in range(len(WEIGHT_NAMES))
    )
    # 기업이 바뀌었거나, 다른 화면에서 돌아와 위젯 값이 지워졌으면 이 기업 값으로 다시 채움
    if st.session_state.get("export_weight_company") != company or widgets_missing:
        st.session_state.export_weight_company = company
        for i, value in enumerate(state["draft"]):
            st.session_state[f"export_weight_slider_{i}"] = value / UNIT
            st.session_state[f"export_weight_number_{i}"] = value / UNIT


def applied_weights(company):
    """기업에 적용된 가중치 (0.1% 단위 정수 리스트, 합계 1000)"""
    return _company_state(company)["applied"]


def is_default_weights(company):
    """기본값(CRITIC)이면 True → dashboard_score.py 결과를 그대로 사용"""
    return applied_weights(company) == default_weights(company)


def is_customized(company):
    """사용자가 가중치를 바꿔 적용한 기업인지 (저장된 적이 있을 때만 판단 — 탭 표시용)"""
    state = _store().get(company)
    return bool(state) and state["applied"] != default_weights(company)


def custom_weights(company):
    """점수 계산용: 기본값이면 None, 사용자가 바꿨으면 {지표 이름: 가중치}"""
    if is_default_weights(company):
        return None
    applied = applied_weights(company)
    return {name: applied[i] for i, name in enumerate(WEIGHT_NAMES)}


def weight_summary(company):
    """도움말용 한 줄 요약: 'HHI 15.7%, 국방비 9.4%, …'"""
    applied = applied_weights(company)
    return ", ".join(
        f"{name} {applied[i] / UNIT:.2f}%"
        for i, name in enumerate(WEIGHT_NAMES)
    )


# =========================================================
# 가중치 계산 함수 (02_company에서 옮김)
# =========================================================

def distribute_weights(values, target_sum):
    """
    기존 비율을 유지하며 target_sum만큼 재분배.
    0.01% 단위 정수로 계산하여 합계를 정확히 맞춤.
    """
    if not values:
        return []

    total_value = sum(values)

    # 모든 값이 0이라면 균등 배분
    if total_value == 0:
        values = [1] * len(values)
        total_value = len(values)

    # 정수 몫 배분
    result = [
        target_sum * value // total_value
        for value in values
    ]

    # 버림으로 발생한 나머지 계산
    remainder = target_sum - sum(result)

    # 소수 부분이 큰 항목부터 1씩 배분
    order = sorted(
        range(len(values)),
        key=lambda i: (
            -(target_sum * values[i] % total_value),
            i,
        ),
    )

    for i in order[:remainder]:
        result[i] += 1

    return result


def sync_slider_values():
    """계산된 가중치를 슬라이더와 숫자 입력칸에 동기화"""
    weights = _state()["draft"]

    for i, value in enumerate(weights):
        percent = value / UNIT

        st.session_state[f"export_weight_slider_{i}"] = percent
        st.session_state[f"export_weight_number_{i}"] = percent


def change_weight(index):
    """
    특정 가중치를 변경하면:
    1. 잠금된 가중치는 유지
    2. 변경한 가중치는 유지
    3. 나머지 잠금 해제 가중치를 비례 재분배
    4. 합계 100% 보장
    """
    weights = _state()["draft"].copy()
    locked = _state()["locked"]

    if index in locked:
        sync_slider_values()
        return

    # 변경 항목을 제외한 자동 조절 대상
    adjustable = [
        i for i in range(len(weights))
        if i not in locked and i != index
    ]

    # 자동 조절할 항목이 없으면 변경 불가
    if not adjustable:
        sync_slider_values()
        return

    # 잠금된 항목의 합계
    locked_sum = sum(
        weights[i] for i in locked
    )

    # 현재 항목이 사용할 수 있는 최대 가중치
    available = TOTAL - locked_sum

    slider_key = f"export_weight_slider_{index}"

    # 0.01% 단위 정수 변환
    requested = round(
        st.session_state[slider_key] * UNIT
    )

    # 잠금 가중치를 침범하지 않도록 제한
    new_value = max(
        0,
        min(requested, available)
    )

    weights[index] = new_value

    # 나머지 가중치에 배분할 총량
    remaining = available - new_value

    previous_values = [
        weights[i] for i in adjustable
    ]

    new_values = distribute_weights(
        previous_values,
        remaining
    )

    for i, value in zip(adjustable, new_values):
        weights[i] = value

    _state()["draft"] = weights

    # 모든 슬라이더 값 동기화
    sync_slider_values()
    
def change_weight_number(index):
    """숫자 직접 입력 시 기존 재분배 함수 실행"""
    st.session_state[f"export_weight_slider_{index}"] = (
        st.session_state[f"export_weight_number_{index}"]
    )

    change_weight(index)


def toggle_weight_lock(index):
    """가중치 잠금 및 해제"""
    locked = _state()["locked"].copy()

    if index in locked:
        locked.remove(index)

    else:
        # 최소 1개는 자동 조절 대상으로 남겨둠
        if len(locked) >= len(WEIGHT_NAMES) - 1:
            return

        locked.add(index)

    _state()["locked"] = locked


def reset_weights():
    """이 기업의 가중치와 잠금 상태를 기본값(CRITIC)으로 초기화"""
    _state()["draft"] = default_weights(st.session_state.get("export_weight_company"))

    _state()["locked"] = set()

    sync_slider_values()


def apply_weights():
    """설정된 가중치를 적용하고 팝오버 닫기"""
    _state()["applied"] = _state()["draft"].copy()

    # '모든 기업에 같은 가중치 적용'을 체크했으면 6개 기업 모두 같은 가중치로 맞춤
    if st.session_state.get("export_weight_apply_all"):
        from components.company_weapons import COMPANIES
        draft = _state()["draft"].copy()
        locked = set(_state()["locked"])
        for other in COMPANIES:
            other_state = _company_state(other)
            other_state["draft"] = draft.copy()
            other_state["applied"] = draft.copy()
            other_state["locked"] = set(locked)

    # 적용 버튼을 누르면 가중치 설정 팝오버 닫기
    st.session_state.export_weights_popover = False


# =========================================================
# 가중치 커스텀 팝오버 (02_company에서 옮김)
# =========================================================

def render_weight_popover(company, icon_only=False):
    """'⚙️ 가중치 커스텀' 버튼 + 설정 팝오버 (선택 기업의 가중치)
    icon_only=True: 좁은 자리용 ⚙️ 아이콘 버튼 (마우스를 올리면 '가중치 커스텀' 표시)"""
    with st.popover(
        "⚙️" if icon_only else "⚙️ 가중치 커스텀",
        use_container_width=not icon_only,
        help="가중치 커스텀" if icon_only else None,
        key="export_weights_popover",
        on_change="rerun"
    ):
        st.html("""
        <style>
        div[data-testid="stNumberInput"] input {
            text-align: center !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
        }
        </style>
        """)
        
        st.html("""
        <style>
        /* 가중치 자물쇠 버튼 가운데 정렬 */
        [class*="st-key-export_lock_"] button {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
        }

        /* 자물쇠 아이콘 중앙 배치 */
        [class*="st-key-export_lock_"] button p {
            width: 100%;
            margin: 0 !important;
            padding: 0 !important;
            text-align: center !important;
            line-height: 1 !important;
        }
        
        /* 상단 초기화 / 적용 버튼 크기 조절 */
        .st-key-export_reset_weights button,
        .st-key-export_apply_weights button {
            height: 32px !important;
            min-height: 32px !important;
            padding: 0 4px !important;
            font-size: 12px !important;
            border-radius: 6px !important;
            white-space: nowrap !important;
        }

        /* 1안: 한 줄 배치 [이름 | 슬라이더 | 숫자 | 잠금] — 6개 항목이 스크롤 없이 한 번에 보이게 */
        /* 슬라이더 위 값·아래 0.00%~100.00% 표시는 숫자 칸과 중복이라 숨김 */
        [class*="st-key-export_weight_slider_"] [data-testid="stSliderThumbValue"],
        [class*="st-key-export_weight_slider_"] [data-testid="stSliderTickBar"] {
            display: none !important;
        }
        /* 팝오버 안 항목 사이 세로 간격 줄임 */
        [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {
            gap: 0.45rem !important;
        }
        .weight-pop-title { font-size: 18px; font-weight: 700; line-height: 1.3; margin: 0; }
        .weight-row-name { font-size: 13.5px; line-height: 1.25; white-space: nowrap; }
        .weight-row-name small { display: block; font-size: 11px; opacity: .6; }
        </style>
        """)

        # -----------------------------------------
        # 가중치 설정 제목 + 초기화 / 적용 버튼
        # -----------------------------------------
        title_col, reset_col, apply_col = st.columns(
            [2.0, 1.0, 0.8],
            gap="small",
            vertical_alignment="center"
        )

        with title_col:
            st.html('<p class="weight-pop-title">가중치 설정</p>')

        with reset_col:
            st.button(
                "↺ 초기화",
                key="export_reset_weights",
                use_container_width=True,
                on_click=reset_weights,
                wrap=True,
            )

        with apply_col:
            st.button(
                "적용",
                key="export_apply_weights",
                type="primary",
                use_container_width=True,
                on_click=apply_weights,
                wrap=True,
            )

        st.checkbox(
            "모든 기업에 같은 가중치 적용",
            key="export_weight_apply_all",
            help="체크하고 '적용'을 누르면 6개 기업 모두 지금 가중치로 바뀝니다. "
                 "기업별로 되돌리려면 그 기업에서 '초기화' 후 '적용'을 누르세요.",
        )

        for i, name in enumerate(WEIGHT_NAMES):

            weights = (
                _company_state(company)["draft"]
            )

            locked = (
                _company_state(company)["locked"]
            )

            unlocked_indices = [
                j for j in range(len(WEIGHT_NAMES))
                if j not in locked
            ]

            locked_total = sum(
                weights[j] for j in locked
            )

            available = TOTAL - locked_total

            is_locked = i in locked

            is_disabled = (
                is_locked
                or len(unlocked_indices) <= 1
                or available == 0
            )
            # 이름 아래에 작게 최대 설정 가능 비율 표시
            limit_note = ""

            if not is_locked:
                if len(unlocked_indices) == 1:
                    limit_note = "자동 결정"
                elif available < TOTAL:
                    limit_note = f"최대 {available / UNIT:.2f}%"

            # 1안: [이름 | 슬라이더 | 숫자 | 잠금] 한 줄
            name_column, slider_column, number_column, lock_column = st.columns(
                [1.35, 3.6, 1.4, 0.8],
                gap="small",
                vertical_alignment="center"
            )

            with name_column:
                st.html(
                    f'<div class="weight-row-name">{name}'
                    + (f'<small>{limit_note}</small>' if limit_note else "")
                    + '</div>'
                )

            with slider_column:
                st.slider(
                    label=name,
                    label_visibility="collapsed",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.01,
                    format="%.2f%%",
                    key=f"export_weight_slider_{i}",
                    disabled=is_disabled,
                    on_change=change_weight,
                    args=(i,),
                )
                
            # 숫자 직접 입력
            with number_column:
                st.number_input(
                    label=f"{name} 직접 입력 (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.01,
                    format="%.2f",
                    key=f"export_weight_number_{i}",
                    label_visibility="collapsed",
                    disabled=is_disabled,
                    on_change=change_weight_number,
                    args=(i,),
                )

            with lock_column:
                st.button(
                    "🔒" if is_locked else "🔓",
                    key=f"export_lock_{i}",
                    disabled=(
                        not is_locked
                        and len(locked)
                        >= len(WEIGHT_NAMES) - 1
                    ),
                    on_click=toggle_weight_lock,
                    args=(i,),
                    use_container_width=True,
                    wrap=True,
                )

        # -----------------------------------------
        # 가중치 안내 문구
        # -----------------------------------------
        st.caption(
            "6개 가중치의 합계는 항상 "
            "100%로 유지됩니다."
        )
        # 잠금 안내는 맨 아래로 (자물쇠와 '잠금' 사이 한 칸 띄움)
        st.caption(
            "🔒\u00a0 잠금된 가중치는 다른 항목을 "
            "조절해도 변경되지 않습니다."
        )
