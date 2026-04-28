"""
나트랑 패밀리 베이스캠프 🌴
안정성 최우선 & 모벤픽 5박 특화 버전 (Stable & Movenpick Edition)
"""

import streamlit as st
import google.generativeai as genai
import requests
import json
import re
import time
from datetime import datetime

# ──────────────────────────────────────────────
# 1. 기본 설정 및 전역 상태 초기화
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="나트랑 패밀리 베이스캠프",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 가족 구성원 및 위치 상수
FAMILY_MEMBERS = ["아빠", "엄마", "할머니", "할아버지", "첫째 (4학년)", "둘째 윤우 (1학년)", "막내 (취학 전)", "삼촌", "이모", "사촌"]
LOCATIONS = ["숙소(모벤픽)", "해변/수영장", "식당", "관광지", "이동 중"]

def init_session_state():
    """모든 세션 상태를 앱 시작 시 한 번에 안전하게 초기화합니다."""
    if "locations" not in st.session_state:
        st.session_state.locations = {m: "숙소(모벤픽)" for m in FAMILY_MEMBERS}
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "missions" not in st.session_state:
        st.session_state.missions = []
    if "notices" not in st.session_state:
        st.session_state.notices = [{"type": "🔔 긴급", "text": "환영합니다! 즐거운 나트랑 가족 여행 되세요.", "time": "00:00"}]
    if "budget" not in st.session_state:
        st.session_state.budget = 5000000
    if "expenses" not in st.session_state:
        st.session_state.expenses = []

init_session_state()

# ──────────────────────────────────────────────
# 2. API 키 관리 (클라우드 금고 연동)
# ──────────────────────────────────────────────
try:
    # 스트림릿 Secrets 금고에서 키를 가져옵니다.
    KEY_GEMINI = st.secrets["api_keys"]["gemini"]
    KEY_WEATHER = st.secrets["api_keys"]["open_weather"]
except Exception:
    KEY_GEMINI = ""
    KEY_WEATHER = ""

if KEY_GEMINI:
    try:
        genai.configure(api_key=KEY_GEMINI)
    except Exception:
        pass

# ──────────────────────────────────────────────
# 3. 디자인 (커스텀 CSS)
# ──────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background: linear-gradient(160deg, #0f2027 0%, #203a43 50%, #2c5364 100%); }
.main-title { font-size: 2.2rem; font-weight: 900; color: #ffd200; margin: 0; padding-bottom: 10px; }
.card { background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12); border-radius: 12px; padding: 15px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 4. 기능별 화면 렌더링 (Tabs)
# ──────────────────────────────────────────────

def render_map_tab():
    st.subheader("🗺️ 깜란 & 나트랑 지도")
    
    spots = {
        "🏨 모벤픽 리조트 깜란": (11.9688, 109.2162),
        "🏖️ 깜란 해변": (11.9695, 109.2190),
        "🎡 나트랑 시내 야시장": (12.2435, 109.1939),
        "✈️ 깜란 국제공항": (11.9981, 109.2193)
    }

    c1, c2 = st.columns([3, 1])
    with c2:
        st.markdown("**📌 장소 확인**")
        selected = st.radio("목적지 선택", list(spots.keys()), key="map_radio")
        lat, lng = spots[selected]
        url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
        st.link_button("📱 구글 지도 앱으로 열기", url, use_container_width=True)

    with c1:
        # 오류가 나지 않는 가장 안전한 OpenStreetMap Iframe 사용
        osm_url = f"https://www.openstreetmap.org/export/embed.html?bbox={lng-0.03},{lat-0.03},{lng+0.03},{lat+0.03}&layer=mapnik&marker={lat},{lng}"
        st.components.v1.iframe(osm_url, height=350)

    st.markdown("---")
    st.subheader("👨‍👩‍👧‍👦 가족 위치 체크인")
    
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            who = st.selectbox("누구인가요?", FAMILY_MEMBERS, key="loc_who")
        with col2:
            where = st.selectbox("어디에 있나요?", LOCATIONS, key="loc_where")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("위치 알리기", use_container_width=True, key="loc_btn"):
                st.session_state.locations[who] = where
                st.rerun()

    # 위치 현황 요약
    summary = {}
    for m, l in st.session_state.locations.items():
        summary.setdefault(l, []).append(m)
        
    sum_cols = st.columns(max(len(summary), 1))
    for i, (loc, members) in enumerate(summary.items()):
        with sum_cols[i % len(sum_cols)]:
            st.markdown(f"<div class='card'><b style='color:#ffd200;'>{loc}</b><br><span style='font-size:0.85em;'>{', '.join(members)}</span></div>", unsafe_allow_html=True)

def render_ai_tab():
    c1, c2 = st.columns([3, 2])
    
    with c1:
        st.subheader("🤖 여행 비서 (AI)")
        chat_box = st.container(height=350)
        with chat_box:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
        prompt = st.chat_input("예: 베트남어로 고수 빼주세요가 뭐야?")
        if prompt:
            if not KEY_GEMINI:
                st.warning("사이드바에 Gemini API 키를 입력해주세요!")
            else:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.spinner("답변 생성 중..."):
                    try:
                        model = genai.GenerativeModel("gemini-1.5-pro")
                        response = model.generate_content(prompt)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        st.error("오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
                st.rerun()

    with c2:
        st.subheader("🕵️ 아이들 미션")
        if st.button("🎲 오늘의 미션 뽑기", use_container_width=True, key="btn_mission"):
            if not KEY_GEMINI:
                st.warning("API 키가 필요합니다.")
            else:
                with st.spinner("미션 만드는 중..."):
                    try:
                        model = genai.GenerativeModel("gemini-1.5-pro")
                        res = model.generate_content('나트랑 가족 여행 중 4학년, 1학년 아이들을 위한 짧은 미션 3개를 JSON 배열로만 줘. 포맷: [{"emoji":"🍉","title":"미션이름","points":10}]').text
                        # 정규식으로 JSON 추출 (안정성 강화)
                        match = re.search(r'\[.*\]', res, re.DOTALL)
                        if match:
                            st.session_state.missions = json.loads(match.group(0))
                    except Exception:
                        st.error("미션 생성에 실패했어요. 다시 눌러주세요.")

        if st.session_state.missions:
            for i, m in enumerate(st.session_state.missions):
                # 체크박스 상태를 강제로 session_state에 묶어 충돌 방지
                st.checkbox(f"{m.get('emoji','')} **{m.get('title','')}** (+{m.get('points',10)}점)", key=f"msn_{i}")

def render_board_tab():
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("📢 가족 공지")
        with st.expander("✏️ 공지 쓰기"):
            n_type = st.selectbox("말머리", ["🔔 긴급", "📅 일정", "💡 정보"], key="noti_type")
            n_text = st.text_input("내용", key="noti_text")
            if st.button("등록", key="noti_btn") and n_text:
                st.session_state.notices.insert(0, {
                    "type": n_type, 
                    "text": n_text, 
                    "time": datetime.now().strftime("%H:%M")
                })
                st.rerun()

        for n in st.session_state.notices:
            color = "#ff4b4b" if "긴급" in n["type"] else "#f7971e"
            st.markdown(f"<div class='card' style='border-left:4px solid {color};'><b>{n['type']}</b> | {n['text']} <span style='font-size:0.8em;color:gray;'>{n['time']}</span></div>", unsafe_allow_html=True)

    with c2:
        st.subheader("✅ 모벤픽 5박 짐 챙기기")
        items = [
            "여권 (전원 10명 확인)", "E-티켓 및 호텔 바우처", 
            "달러 비상금 (빳빳한 신권)", "아이들 해열제/모기기피제",
            "첫째 스노클링 장비/방수팩", "1학년 윤우 수영복/애착인형", 
            "샤워기 필터 (5박 여분 필수)", "수영복 건조용 옷걸이", 
            "트래블월렛 카드 (그랩용)"
        ]
        
        done = 0
        for i, item in enumerate(items):
            # 체크박스를 누르면 session_state[f"chk_{i}"] 에 자동으로 True/False 저장됨
            if st.checkbox(item, key=f"chk_{i}"):
                done += 1
        st.progress(done / len(items))

def render_budget_tab():
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("💰 공동 경비 장부")
        with st.expander("➕ 지출 쓰기"):
            cat = st.selectbox("분류", ["식비", "교통", "쇼핑", "숙박/체험", "기타"], key="exp_cat")
            amt = st.number_input("금액 (원)", min_value=0, step=10000, key="exp_amt")
            desc = st.text_input("어디서 썼나요?", key="exp_desc")
            if st.button("등록", key="exp_btn") and amt > 0:
                st.session_state.expenses.append({"cat": cat, "amt": amt, "desc": desc})
                st.rerun()

        spent = sum(e["amt"] for e in st.session_state.expenses)
        remain = st.session_state.budget - spent
        st.metric("총 지출액", f"{spent:,} 원", delta=f"남은 예산: {remain:,} 원", delta_color="inverse")

        for e in reversed(st.session_state.expenses[-5:]):
            st.markdown(f"<div class='card'>{e['cat']} - {e['desc']} : <b style='color:#ffd200;'>{e['amt']:,}원</b></div>", unsafe_allow_html=True)

    with c2:
        st.subheader("💱 3초 환율 계산기")
        st.caption("※ 대략적인 계산용입니다. (1달러=1370원, 1원=18.5동 기준)")
        
        t1, t2 = st.tabs(["원화 ➔ 동/달러", "베트남동 ➔ 원/달러"])
        
        with t1:
            krw = st.number_input("원화 입력 (원)", min_value=0, value=50000, step=10000, key="krw_in")
            if krw > 0:
                st.info(f"🇻🇳 약 **{krw * 18.5:,.0f} 동 (VND)**\n\n🇺🇸 약 **${krw / 1370:,.2f} (USD)**")
                
        with t2:
            vnd = st.number_input("베트남동 입력 (동)", min_value=0, value=100000, step=100000, key="vnd_in")
            if vnd > 0:
                st.success(f"🇰🇷 약 **{vnd / 18.5:,.0f} 원 (KRW)**\n\n🇺🇸 약 **${vnd / 25400:,.2f} (USD)**")
                st.caption("💡 꿀팁: 베트남동에서 '0'을 하나 빼고 반으로 나누면 대충 원화 금액과 비슷해요! (예: 10만동 ➔ 5천원)")

        st.markdown("---")
        st.subheader("🌤️ 깜란 날씨")
        if KEY_WEATHER:
            try:
                # 모벤픽 리조트 깜란 좌표
                res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat=11.9688&lon=109.2162&appid={KEY_WEATHER}&units=metric&lang=kr", timeout=3).json()
                st.markdown(f"<div class='card' style='text-align:center;'><h2>{res['main']['temp']:.1f}°C</h2><p>{res['weather'][0]['description']} (습도 {res['main']['humidity']}%)</p></div>", unsafe_allow_html=True)
            except:
                st.warning("날씨 정보를 가져올 수 없습니다.")
        else:
            st.info("사이드바에 OpenWeather API 키를 넣으면 날씨가 보입니다.")

# ──────────────────────────────────────────────
# 5. 메인 앱 실행
# ──────────────────────────────────────────────
def main():
    st.markdown('<p class="main-title">🌴 나트랑 패밀리 베이스캠프</p>', unsafe_allow_html=True)
    st.markdown(f"<div class='card' style='text-align:center;'><b>오늘 날짜: {datetime.now().strftime('%Y년 %m월 %d일')}</b> | 모벤픽 리조트 5박 6일 대가족 여행</div>", unsafe_allow_html=True)
    
    tab_map, tab_ai, tab_board, tab_budget = st.tabs(["🗺️ 지도&위치", "🤖 비서&미션", "✅ 공지&짐싸기", "💰 장부&환율"])
    
    with tab_map: render_map_tab()
    with tab_ai: render_ai_tab()
    with tab_board: render_board_tab()
    with tab_budget: render_budget_tab()

if __name__ == "__main__":
    main()
