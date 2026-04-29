"""
나트랑 패밀리 베이스캠프 🌴
2026.05.10 (일) - 2026.05.15 (금) | 모벤픽 리조트 깜란 5박 6일
대가족 10명 여행 종합 대시보드
"""

import streamlit as st
import google.generativeai as genai
import requests
import json
import re
from datetime import datetime, date, timedelta
from PIL import Image
import io
import base64

# ═══════════════════════════════════════════════════════════════
# 1. 페이지 설정
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="나트랑 베이스캠프",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════
# 2. 여행 기본 정보 (상수)
# ═══════════════════════════════════════════════════════════════
TRIP_START = date(2026, 5, 10)
TRIP_END = date(2026, 5, 15)
TOTAL_DAYS = (TRIP_END - TRIP_START).days + 1
HOTEL_NAME = "모벤픽 리조트 & 스파 깜란"
HOTEL_LAT = 11.9688
HOTEL_LON = 109.2162

FAMILY_MEMBERS = [
    "아빠", "엄마", "할머니", "할아버지",
    "첫째 (4학년)", "윤우 (1학년)", "막내 (취학전)",
    "삼촌", "이모", "사촌",
]

LOCATIONS = ["🏨 모벤픽", "🏖️ 해변/수영장", "🍜 식당", "🎡 관광지", "🚐 이동중"]

# ─────────────────────────────────────────────
# 일자별 일정
# ─────────────────────────────────────────────
ITINERARY = {
    date(2026, 5, 10): {
        "title": "출발 · 인천 → 깜란",
        "tip": "긴 비행, 편한 옷차림 / 아이들 멀미약 챙기기",
        "items": [
            ("출발 3h전", "🛫", "인천공항 집결"),
            ("비행", "✈️", "인천 → 깜란 (약 5시간 30분)"),
            ("도착 후", "🏨", "모벤픽 리조트 체크인"),
            ("저녁", "🍽️", "리조트 내 식사 & 휴식"),
        ],
    },
    date(2026, 5, 11): {
        "title": "리조트 적응 · 모벤픽 만끽",
        "tip": "선크림 필수, 모자/래쉬가드 챙기기",
        "items": [
            ("07:00", "🌅", "조식 - 모벤픽 뷔페"),
            ("10:00", "🏊", "프라이빗 비치 & 수영장"),
            ("13:00", "🍜", "리조트 점심 또는 룸서비스"),
            ("15:00", "😴", "낮잠 / 키즈클럽 / 자유시간"),
            ("18:30", "🌆", "선셋 디너"),
        ],
    },
    date(2026, 5, 12): {
        "title": "나트랑 시내 투어",
        "tip": "오후 햇볕 강함, 양산·물 챙기기",
        "items": [
            ("09:00", "🚐", "그랩카로 나트랑 시내 (약 40분)"),
            ("10:00", "⛪", "포나가르 참탑"),
            ("12:00", "🍲", "현지 쌀국수 점심"),
            ("14:00", "🛍️", "롯데마트 (간식·기념품)"),
            ("17:00", "🎡", "나트랑 야시장 & 저녁식사"),
        ],
    },
    date(2026, 5, 13): {
        "title": "빈원더스 또는 자유 휴식",
        "tip": "물놀이용 옷·수건 별도 / 어르신은 리조트 추천",
        "items": [
            ("종일 A안", "🎢", "빈원더스 나트랑 (케이블카+워터파크)"),
            ("종일 B안", "🏖️", "리조트 풀빌라 휴식"),
            ("18:00", "🍤", "해산물 레스토랑 디너"),
        ],
    },
    date(2026, 5, 14): {
        "title": "마지막 날 알차게",
        "tip": "짐 정리도 슬슬 시작",
        "items": [
            ("08:00", "🌅", "여유로운 조식"),
            ("10:00", "💆", "스파/마사지 (어른) · 키즈클럽 (아이)"),
            ("14:00", "🏊", "마지막 수영"),
            ("16:30", "📸", "가족 단체사진"),
            ("18:30", "🍽️", "특별 디너"),
        ],
    },
    date(2026, 5, 15): {
        "title": "귀국 · 깜란 → 인천",
        "tip": "공항까지 약 20분 / 여권·기내가방 다시 확인",
        "items": [
            ("09:00", "🧳", "짐 정리 & 여권 점검"),
            ("11:00", "🚪", "체크아웃 (지연체크아웃 협의)"),
            ("공항", "🛍️", "깜란공항 면세점"),
            ("비행", "✈️", "깜란 → 인천"),
            ("도착", "🏠", "집으로!"),
        ],
    },
}

# ─────────────────────────────────────────────
# 베트남어 핵심 표현
# ─────────────────────────────────────────────
PHRASES = {
    "인사·기본": [
        ("안녕하세요", "Xin chào", "씬 짜오"),
        ("감사합니다", "Cảm ơn", "깜언"),
        ("죄송합니다", "Xin lỗi", "씬 로이"),
        ("네 / 아니요", "Vâng / Không", "벙 / 콩"),
    ],
    "식당": [
        ("얼마예요?", "Bao nhiêu tiền?", "바오 니에우 띠엔?"),
        ("계산해주세요", "Tính tiền", "띤 띠엔"),
        ("고수 빼주세요", "Không rau mùi", "콩 자우 무이"),
        ("맵지 않게요", "Không cay", "콩 까이"),
        ("얼음 빼주세요", "Không đá", "콩 다"),
        ("물 한 잔 주세요", "Cho tôi nước", "쪼 또이 느억"),
        ("맛있어요!", "Ngon quá!", "응온 꽈!"),
    ],
    "쇼핑·이동": [
        ("비싸요 / 깎아주세요", "Đắt quá / Giảm giá", "닷꽈 / 잠 자"),
        ("여기로 가주세요", "Đi đến đây", "디 덴 더이"),
        ("화장실 어디예요?", "Nhà vệ sinh ở đâu?", "냐 베신 어 더우?"),
    ],
    "긴급": [
        ("도와주세요", "Giúp tôi với", "줍 또이 버이"),
        ("아파요", "Tôi bị đau", "또이 비 다우"),
        ("병원 어디예요?", "Bệnh viện ở đâu?", "벤 비엔 어 더우?"),
    ],
}

# ─────────────────────────────────────────────
# 비상 연락처
# ─────────────────────────────────────────────
EMERGENCY = [
    ("🇰🇷 영사콜센터 (24h)", "+82-2-3210-0404", "한국어 상담"),
    ("🇰🇷 주베트남 한국대사관", "+84-24-3831-5111", "사고/사건 발생시"),
    ("🚨 베트남 경찰", "113", "긴급"),
    ("🚑 베트남 응급의료", "115", "응급"),
    ("🔥 베트남 소방", "114", "화재"),
    ("🏨 모벤픽 깜란", "+84-258-3989-666", "프론트"),
    ("✈️ 깜란 국제공항", "+84-258-3989-919", "항공편 문의"),
]

# ─────────────────────────────────────────────
# 짐 체크리스트
# ─────────────────────────────────────────────
PACKING_LIST = {
    "📄 서류·금융": [
        "여권 (전원 10명, 6개월 이상 유효)",
        "여권 사본 + 사진 (분실 대비)",
        "E-티켓 / 호텔 바우처",
        "여행자보험 증명서",
        "달러 비상금 (빳빳한 신권)",
        "트래블월렛 / 트래블로그 카드",
    ],
    "💊 건강·아이": [
        "아이들 해열제·감기약",
        "지사제·소화제·밴드",
        "모기기피제 (강력 제품)",
        "선크림 (아이용·어른용)",
        "1학년 윤우 애착인형",
        "막내 기저귀/물티슈",
    ],
    "🏖️ 리조트·물놀이": [
        "수영복 (인당 2벌 권장)",
        "래쉬가드 / 수영모",
        "스노클링 장비 / 방수팩",
        "비치타올 (호텔 제공이지만 여분)",
        "수영복 건조용 옷걸이",
        "샤워기 필터 (5박 여분)",
    ],
    "📱 전자·편의": [
        "보조배터리 (기내 반입)",
        "멀티어댑터 (베트남 A/C 타입)",
        "현지 SIM 또는 e심",
        "셀카봉 / 삼각대",
    ],
}

# ═══════════════════════════════════════════════════════════════
# 3. 세션 상태 초기화
# ═══════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "locations": {m: "🏨 모벤픽" for m in FAMILY_MEMBERS},
        "messages": [],
        "missions": [],
        "notices": [{
            "level": "공지", "icon": "🌴",
            "text": "환영합니다! 즐거운 나트랑 가족여행 되세요.",
            "time": datetime.now().strftime("%m/%d %H:%M"),
        }],
        "budget": 5_000_000,
        "expenses": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ═══════════════════════════════════════════════════════════════
# 4. API 키 로드
# ═══════════════════════════════════════════════════════════════
try:
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

# ═══════════════════════════════════════════════════════════════
# 5. 유틸리티 함수
# ═══════════════════════════════════════════════════════════════
def get_trip_status():
    """오늘의 여행 상태: (status, days_left, day_num)"""
    today = date.today()
    if today < TRIP_START:
        return "before", (TRIP_START - today).days, 0
    elif today > TRIP_END:
        return "after", 0, TOTAL_DAYS
    else:
        return "during", 0, (today - TRIP_START).days + 1

def get_weather(lat, lon):
    """OpenWeather API"""
    if not KEY_WEATHER:
        return None
    try:
        res = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": KEY_WEATHER, "units": "metric", "lang": "kr"},
            timeout=4,
        ).json()
        return {
            "temp": res["main"]["temp"],
            "feels": res["main"]["feels_like"],
            "humidity": res["main"]["humidity"],
            "desc": res["weather"][0]["description"],
            "icon": res["weather"][0]["icon"],
        }
    except Exception:
        return None

def gemini_call(prompt, model_name="gemini-2.5-flash"):
    """Gemini API 호출 (text 응답, 에러시 None)"""
    if not KEY_GEMINI:
        return None, "API 키가 설정되지 않았습니다. Secrets에 키를 등록해주세요."
    try:
        model = genai.GenerativeModel(model_name)
        return model.generate_content(prompt).text, None
    except Exception as e:
        return None, str(e)

def gemini_vision(prompt, image, model_name="gemini-2.5-flash"):
    """Gemini Vision API 호출 (이미지 + 프롬프트)"""
    if not KEY_GEMINI:
        return None, "API 키가 설정되지 않았습니다."
    try:
        model = genai.GenerativeModel(model_name)
        return model.generate_content([prompt, image]).text, None
    except Exception as e:
        return None, str(e)

def weekday_kr(d):
    return ["월", "화", "수", "목", "금", "토", "일"][d.weekday()]

# ═══════════════════════════════════════════════════════════════
# 6. CSS 디자인
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
.stApp {
    background: linear-gradient(160deg, #0a2540 0%, #1a4d7a 50%, #2c7da0 100%);
}
.main-title {
    font-size: 2rem; font-weight: 900; color: #ffd60a;
    margin: 0; text-align: center; letter-spacing: -0.5px;
}
.subtitle {
    text-align: center; color: #cfe8ff;
    font-size: 0.9rem; margin-bottom: 12px;
}
.card {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 14px; padding: 16px;
    margin-bottom: 10px;
}
.card-title {
    color: #ffd60a; font-weight: 700;
    font-size: 1.05rem; margin-bottom: 8px;
}
.dday-card {
    background: linear-gradient(135deg, #ff6b6b 0%, #ffd60a 100%);
    color: #1a1a1a; text-align: center;
    border-radius: 18px; padding: 22px;
    margin-bottom: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.dday-num { font-size: 3rem; font-weight: 900; line-height: 1; }
.timeline-item {
    background: rgba(255,255,255,0.06);
    border-left: 3px solid #ffd60a;
    padding: 10px 14px; margin-bottom: 6px;
    border-radius: 0 8px 8px 0; color: #fff;
}
.timeline-time {
    color: #9fd0ff; font-weight: 600;
    min-width: 90px; display: inline-block;
}
.phrase-card {
    background: rgba(255,255,255,0.07);
    padding: 12px 14px; border-radius: 10px;
    margin-bottom: 6px;
    border-left: 3px solid #2c7da0;
}
.phrase-ko { color: #ffd60a; font-weight: 700; font-size: 0.95rem; }
.phrase-vi { color: #fff; font-size: 1.1rem; font-weight: 600; margin-top: 2px; }
.phrase-pron { color: #9fd0ff; font-style: italic; font-size: 0.85rem; }
.emergency-card {
    background: rgba(255,75,75,0.12);
    border-left: 3px solid #ff4b4b;
    padding: 10px 14px; border-radius: 0 8px 8px 0;
    margin-bottom: 6px; color: #fff;
}
.location-pill {
    background: rgba(255,214,10,0.15);
    border: 1px solid rgba(255,214,10,0.3);
    padding: 6px 12px; border-radius: 20px;
    display: inline-block; margin: 2px;
    font-size: 0.85rem; color: #fff;
}
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,0.05);
    border-radius: 8px 8px 0 0; padding: 8px 14px;
}
.stTabs [aria-selected="true"] {
    background: rgba(255,214,10,0.2) !important;
    color: #ffd60a !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 7. 화면: 홈 대시보드
# ═══════════════════════════════════════════════════════════════
def render_home():
    status, days_left, day_num = get_trip_status()
    today = date.today()

    # D-day 카드
    if status == "before":
        st.markdown(f"""
        <div class='dday-card'>
            <div style='font-size:0.95rem;'>출발까지</div>
            <div class='dday-num'>D-{days_left}</div>
            <div style='font-size:0.9rem;'>2026년 5월 10일 (일) 출발</div>
        </div>""", unsafe_allow_html=True)
    elif status == "during":
        st.markdown(f"""
        <div class='dday-card'>
            <div style='font-size:0.95rem;'>여행 중</div>
            <div class='dday-num'>{day_num}일차</div>
            <div style='font-size:0.9rem;'>총 {TOTAL_DAYS}일 · {today.strftime('%m월 %d일')} ({weekday_kr(today)})</div>
        </div>""", unsafe_allow_html=True)
        st.progress(day_num / TOTAL_DAYS)
    else:
        st.markdown("""
        <div class='dday-card'>
            <div class='dday-num'>🏠</div>
            <div style='font-weight:700;'>무사 귀국 · 추억 가득한 여행이었기를!</div>
        </div>""", unsafe_allow_html=True)

    # 메인 그리드
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("#### 📅 오늘의 일정")
        target_date = today if today in ITINERARY else (TRIP_START if status == "before" else None)
        if target_date:
            data = ITINERARY[target_date]
            label = "오늘" if target_date == today else f"여행 첫날 ({target_date.month}/{target_date.day})"
            st.caption(f"{label} · {data['title']}")
            st.info(f"💡 {data['tip']}")
            for time_, icon, task in data["items"][:5]:
                st.markdown(f"""
                <div class='timeline-item'>
                    <span class='timeline-time'>{time_}</span> {icon} {task}
                </div>""", unsafe_allow_html=True)
        else:
            st.info("여행이 종료되었습니다.")

    with col_right:
        st.markdown("#### 🌤️ 깜란 날씨")
        w = get_weather(HOTEL_LAT, HOTEL_LON)
        if w:
            st.markdown(f"""
            <div class='card' style='text-align:center;'>
                <img src='https://openweathermap.org/img/wn/{w["icon"]}@2x.png' style='width:80px;'>
                <div style='font-size:2rem; font-weight:900; color:#ffd60a;'>{w['temp']:.1f}°C</div>
                <div>{w['desc']}</div>
                <div style='font-size:0.85rem; color:#9fd0ff;'>체감 {w['feels']:.1f}°C · 습도 {w['humidity']}%</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='card' style='text-align:center;'>
                <div style='font-size:2rem;'>🌴</div>
                <div style='color:#ffd60a; font-weight:700; font-size:1.2rem;'>28~32°C</div>
                <div>5월 깜란 평균 (맑음·습함)</div>
                <div style='font-size:0.8rem; color:#9fd0ff;'>OpenWeather 키 등록시 실시간</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("#### 📊 한눈에")
        spent = sum(e["amt"] for e in st.session_state.expenses)
        remain = st.session_state.budget - spent
        c1, c2 = st.columns(2)
        c1.metric("남은 예산", f"{remain:,}원")
        c2.metric("공지", f"{len(st.session_state.notices)}건")

# ═══════════════════════════════════════════════════════════════
# 8. 화면: 일정
# ═══════════════════════════════════════════════════════════════
def render_itinerary():
    st.markdown("### 📅 5박 6일 전체 일정")
    
    today = date.today()
    labels = []
    for d in ITINERARY.keys():
        n = (d - TRIP_START).days + 1
        labels.append(f"D{n}·{d.month}/{d.day}({weekday_kr(d)})")

    tabs = st.tabs(labels)
    for tab, (d, data) in zip(tabs, ITINERARY.items()):
        with tab:
            badge = ""
            if d == today:
                badge = " <span style='background:#ff4b4b; color:#fff; padding:2px 10px; border-radius:12px; font-size:0.75rem;'>오늘</span>"
            st.markdown(f"<h4 style='color:#ffd60a; margin-bottom:4px;'>{data['title']}{badge}</h4>", unsafe_allow_html=True)
            st.caption(f"💡 {data['tip']}")
            st.markdown("<br>", unsafe_allow_html=True)
            for time_, icon, task in data["items"]:
                st.markdown(f"""
                <div class='timeline-item'>
                    <span class='timeline-time'>{time_}</span> {icon} <b>{task}</b>
                </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 9. 화면: AI 비서 + 베트남어
# ═══════════════════════════════════════════════════════════════
def render_ai():
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🤖 AI 채팅", "🇻🇳 베트남어 회화", "📷 사진 번역"])

    with sub_tab1:
        st.markdown("##### 무엇이든 물어보세요 (Gemini 2.5 Flash)")
        st.caption("예: '나트랑 5월 날씨 특징', '쌀국수 종류 알려줘', '아이들과 갈만한 곳'")
        
        chat_box = st.container(height=350)
        with chat_box:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        prompt = st.chat_input("질문을 입력하세요...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("답변 생성 중..."):
                # 가족여행 컨텍스트 추가
                context = f"""당신은 베트남 나트랑/깜란 가족여행 전문 도우미입니다.
여행 정보: 2026.5.10~5.15, 모벤픽 리조트 깜란 5박, 가족 10명 (4학년·1학년·미취학 아이 포함, 어르신 포함).
한국어로 친절하고 실용적으로, 핵심만 간결하게 답하세요.

질문: {prompt}"""
                text, err = gemini_call(context, "gemini-2.5-flash")
                if text:
                    st.session_state.messages.append({"role": "assistant", "content": text})
                    st.rerun()
                else:
                    st.error(f"🚨 {err}")

        if st.session_state.messages and st.button("🗑️ 대화 초기화"):
            st.session_state.messages = []
            st.rerun()

    with sub_tab2:
        st.markdown("##### 가족여행 필수 표현")
        st.caption("👉 발음은 원어와 다를 수 있어요. 천천히 또박또박!")
        
        for category, phrases in PHRASES.items():
            with st.expander(f"**{category}** ({len(phrases)}개)", expanded=(category == "식당")):
                for ko, vi, pron in phrases:
                    st.markdown(f"""
                    <div class='phrase-card'>
                        <div class='phrase-ko'>🇰🇷 {ko}</div>
                        <div class='phrase-vi'>🇻🇳 {vi}</div>
                        <div class='phrase-pron'>🔊 {pron}</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### ✨ 즉석 번역 (한 → 베)")
        ko_text = st.text_input("번역할 한국어", placeholder="예: 이거 포장해주세요")
        if st.button("번역하기", use_container_width=True) and ko_text:
            with st.spinner("번역 중..."):
                p = f"""다음 한국어를 베트남어로 번역하고, 한글 발음도 함께 알려주세요.
형식: 
🇻🇳 베트남어: ...
🔊 발음: ...
💡 팁: (있다면 짧게)

한국어: {ko_text}"""
                text, err = gemini_call(p)
                if text:
                    st.success(text)
                else:
                    st.error(err)

    with sub_tab3:
        st.markdown("##### 📷 메뉴판·간판 사진 번역")
        st.caption("사진을 찍거나 업로드하면 베트남어를 한국어로 자동 번역해드려요")

        if not KEY_GEMINI:
            st.warning("⚠️ Gemini API 키가 필요합니다. Secrets에 등록해주세요.")
            return

        mode = st.radio(
            "입력 방식 선택",
            ["📷 카메라로 촬영", "📁 갤러리에서 선택"],
            horizontal=True,
            key="cam_mode",
        )

        img_file = None
        if mode == "📷 카메라로 촬영":
            img_file = st.camera_input("📸 메뉴판이나 간판을 찍어주세요", key="cam_input")
        else:
            img_file = st.file_uploader(
                "이미지 파일 선택 (jpg/png)",
                type=["jpg", "jpeg", "png", "webp"],
                key="cam_upload",
            )

        if img_file is not None:
            try:
                img = Image.open(img_file)
                # 너무 큰 이미지는 리사이즈 (속도·비용 절약)
                max_size = 1600
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.LANCZOS)

                col_img, col_opt = st.columns([2, 1])
                with col_img:
                    # 🔍 줌 슬라이더 (줌아웃 ↔ 줌인)
                    zoom = st.slider(
                        "🔍 보기 크기 (← 줌아웃 / 줌인 →)",
                        min_value=0.3, max_value=2.5, value=1.0, step=0.1,
                        format="%.1fx",
                        key="img_zoom",
                        help="작게 보려면 왼쪽, 자세히 보려면 오른쪽으로",
                    )
                    
                    # PIL 이미지를 base64로 변환해 HTML로 표시 (줌 + 스크롤 지원)
                    buf = io.BytesIO()
                    img_rgb = img.convert("RGB") if img.mode != "RGB" else img
                    img_rgb.save(buf, format="JPEG", quality=85)
                    img_b64 = base64.b64encode(buf.getvalue()).decode()
                    width_pct = int(zoom * 100)
                    
                    st.markdown(f"""
                    <div style="text-align:center; overflow:auto; max-height:500px;
                                background:rgba(0,0,0,0.25); border-radius:10px; 
                                padding:8px; border:1px solid rgba(255,255,255,0.1);">
                        <img src="data:image/jpeg;base64,{img_b64}" 
                             style="width:{width_pct}%; max-width:none; 
                                    border-radius:6px;
                                    box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                    </div>
                    <div style="text-align:center; color:#9fd0ff; 
                                font-size:0.8rem; margin-top:6px;">
                        📐 현재 {zoom:.1f}배 · 원본 {img.size[0]}×{img.size[1]}px
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col_opt:
                    st.markdown("**번역 모드**")
                    translate_mode = st.radio(
                        "선택",
                        ["🍜 메뉴판", "🪧 간판/표지", "📄 일반 문서"],
                        key="trans_mode",
                        label_visibility="collapsed",
                    )
                    do_translate = st.button(
                        "🔍 번역 시작",
                        use_container_width=True,
                        type="primary",
                    )

                if do_translate:
                    # 모드별 프롬프트
                    if "메뉴판" in translate_mode:
                        prompt = """이 이미지는 베트남 음식점 메뉴판입니다. 다음 형식으로 정리해주세요:

📋 **메뉴 번역**

각 메뉴 항목별로:
- 🇻🇳 원문 (베트남어)
- 🇰🇷 한국어 번역
- 💵 가격 (있는 경우)
- 💡 음식 설명 (한 줄, 한국 가족이 먹기 좋은지 / 매운지 / 고수 들어가는지 등)

⚠️ **주의사항**: (아이가 먹기 어려운 메뉴, 알레르기 주의 메뉴 등)

✨ **추천**: 한국 가족(아이 3명 포함)에게 추천할 만한 메뉴 2-3개

이미지에 메뉴가 없으면 "메뉴를 찾을 수 없습니다"라고 답하세요."""
                    elif "간판" in translate_mode:
                        prompt = """이 이미지의 베트남어 간판/표지/안내판을 번역해주세요:

📝 **원문**: (베트남어 그대로)
🇰🇷 **번역**: (자연스러운 한국어)
📍 **장소·용도**: (어떤 곳인지, 무슨 안내인지)
💡 **참고 정보**: (관광객이 알면 좋을 점, 주의사항 등)

이미지에 베트남어가 없으면 그렇게 답해주세요."""
                    else:
                        prompt = """이 이미지의 베트남어 텍스트를 한국어로 번역해주세요:

📝 **원문 (베트남어)**:

🇰🇷 **번역 (한국어)**:

💡 **추가 설명**: (필요시 맥락 설명)

이미지에 베트남어 텍스트가 없으면 그렇게 답해주세요."""

                    with st.spinner("🔎 이미지 분석 중... (5~15초)"):
                        text, err = gemini_vision(prompt, img)
                        if text:
                            st.success(text)
                            # 결과 다시보기용 저장
                            st.session_state["last_translation"] = text
                        else:
                            st.error(f"🚨 분석 실패: {err}")
                            st.info("💡 사진이 너무 어둡거나 흐릿하면 인식이 어려워요. 밝은 곳에서 다시 찍어보세요.")

            except Exception as e:
                st.error(f"이미지 처리 오류: {e}")

        # 사용 팁
        with st.expander("💡 더 정확하게 번역받는 팁"):
            st.markdown("""
            - **밝은 곳에서 촬영** — 그림자 없이 정면에서
            - **글자가 화면에 꽉 차도록** — 너무 멀리서 찍으면 인식 안 됨
            - **흔들림 주의** — 두 손으로 잡고 천천히
            - **메뉴판은 한 면씩** — 양면을 한 번에 찍으면 정확도 ↓
            - **반사 주의** — 코팅된 메뉴판은 각도 살짝 틀어서
            """)

# ═══════════════════════════════════════════════════════════════
# 10. 화면: 가족 (위치 + 공지 + 미션)
# ═══════════════════════════════════════════════════════════════
def render_family():
    sub1, sub2, sub3 = st.tabs(["📍 위치 체크인", "📢 가족 공지", "🕵️ 아이 미션"])

    with sub1:
        st.markdown("##### 누가 어디에 있나요?")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            who = st.selectbox("가족", FAMILY_MEMBERS, key="loc_who")
        with c2:
            where = st.selectbox("위치", LOCATIONS, key="loc_where")
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✓ 체크인", use_container_width=True):
                st.session_state.locations[who] = where
                st.rerun()

        st.markdown("---")
        st.markdown("##### 현재 가족 위치")
        summary = {}
        for m, loc in st.session_state.locations.items():
            summary.setdefault(loc, []).append(m)
        for loc, members in summary.items():
            pills = " ".join([f"<span class='location-pill'>{m}</span>" for m in members])
            st.markdown(f"""
            <div class='card'>
                <div class='card-title'>{loc} ({len(members)}명)</div>
                {pills}
            </div>""", unsafe_allow_html=True)

    with sub2:
        st.markdown("##### 새 공지 등록")
        c1, c2 = st.columns([1, 3])
        with c1:
            n_level = st.selectbox("종류", ["🚨 긴급", "📅 일정", "💡 정보"], key="noti_lv")
        with c2:
            n_text = st.text_input("내용", key="noti_txt", placeholder="예: 7시 로비 집결!")
        if st.button("📢 공지 올리기", use_container_width=True) and n_text:
            st.session_state.notices.insert(0, {
                "level": n_level.split()[1],
                "icon": n_level.split()[0],
                "text": n_text,
                "time": datetime.now().strftime("%m/%d %H:%M"),
            })
            st.rerun()

        st.markdown("---")
        st.markdown("##### 공지 목록")
        for n in st.session_state.notices:
            color = "#ff4b4b" if "긴급" in n["level"] else ("#ffd60a" if "일정" in n["level"] else "#9fd0ff")
            st.markdown(f"""
            <div class='card' style='border-left:4px solid {color};'>
                <b>{n['icon']} {n['level']}</b> · {n['text']}
                <div style='font-size:0.8rem; color:#9fd0ff; margin-top:4px;'>{n['time']}</div>
            </div>""", unsafe_allow_html=True)

    with sub3:
        st.markdown("##### 아이들을 위한 오늘의 미션 🎯")
        st.caption("4학년·1학년 아이가 즐길 수 있는 작은 챌린지")
        
        if st.button("🎲 새 미션 뽑기", use_container_width=True):
            with st.spinner("미션 생성 중..."):
                p = """나트랑 가족 여행 중인 4학년, 1학년 아이들이 함께 즐길 수 있는 짧은 미션 4개를 만들어주세요.
관광지, 식당, 리조트에서 안전하게 할 수 있는 활동이어야 합니다.
JSON 배열로만 응답하세요. 다른 설명은 절대 넣지 마세요.
형식: [{"emoji":"🍉","title":"미션이름","points":10}, ...]"""
                text, err = gemini_call(p)
                if text:
                    match = re.search(r"\[.*\]", text, re.DOTALL)
                    if match:
                        try:
                            st.session_state.missions = json.loads(match.group(0))
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("미션 형식 파싱 실패. 다시 시도해주세요.")
                else:
                    st.error(err)

        if st.session_state.missions:
            total_done = 0
            total_points = 0
            for i, m in enumerate(st.session_state.missions):
                done = st.checkbox(
                    f"{m.get('emoji','🎯')} **{m.get('title','미션')}** · +{m.get('points',10)}점",
                    key=f"msn_{i}",
                )
                if done:
                    total_done += 1
                    total_points += m.get("points", 10)
            st.success(f"✅ 완료 {total_done}/{len(st.session_state.missions)} · 누적 {total_points}점")

# ═══════════════════════════════════════════════════════════════
# 11. 화면: 가계부 (지출 + 환율)
# ═══════════════════════════════════════════════════════════════
def render_budget():
    sub1, sub2 = st.tabs(["💰 공동 가계부", "💱 환율 계산기"])

    with sub1:
        st.markdown("##### 새 지출 등록")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            cat = st.selectbox("분류", ["🍽️ 식비", "🚐 교통", "🛍️ 쇼핑", "🎡 체험", "🏨 숙박", "기타"], key="exp_cat")
        with c2:
            amt = st.number_input("금액(원)", min_value=0, step=10000, key="exp_amt")
        with c3:
            desc = st.text_input("내용", key="exp_desc", placeholder="예: 야시장 쌀국수")
        if st.button("✓ 등록", use_container_width=True) and amt > 0:
            st.session_state.expenses.append({
                "cat": cat, "amt": amt, "desc": desc,
                "time": datetime.now().strftime("%m/%d %H:%M"),
            })
            st.rerun()

        st.markdown("---")
        spent = sum(e["amt"] for e in st.session_state.expenses)
        remain = st.session_state.budget - spent
        c1, c2, c3 = st.columns(3)
        c1.metric("총 예산", f"{st.session_state.budget:,}원")
        c2.metric("지출", f"{spent:,}원")
        c3.metric("남은 금액", f"{remain:,}원", delta=None)
        st.progress(min(spent / st.session_state.budget, 1.0) if st.session_state.budget else 0)

        st.markdown("##### 최근 지출")
        if not st.session_state.expenses:
            st.info("아직 등록된 지출이 없습니다.")
        for e in reversed(st.session_state.expenses[-10:]):
            st.markdown(f"""
            <div class='card'>
                <b>{e['cat']}</b> · {e['desc'] or '(내용 없음)'}
                <span style='float:right; color:#ffd60a; font-weight:700;'>{e['amt']:,}원</span>
                <div style='font-size:0.8rem; color:#9fd0ff;'>{e.get('time','')}</div>
            </div>""", unsafe_allow_html=True)

    with sub2:
        st.markdown("##### 빠른 환율 계산")
        st.caption("기준: 1원 ≈ 18.5동, 1달러 ≈ 1,370원 (대략적 계산용)")
        
        t1, t2, t3 = st.tabs(["원 → 동", "동 → 원", "달러 → 원"])
        with t1:
            krw = st.number_input("원화 (KRW)", min_value=0, value=50000, step=10000, key="krw1")
            if krw > 0:
                vnd = krw * 18.5
                usd = krw / 1370
                st.markdown(f"""
                <div class='card'>
                    🇻🇳 약 <b style='color:#ffd60a; font-size:1.3rem;'>{vnd:,.0f} VND</b><br>
                    🇺🇸 약 <b style='color:#ffd60a; font-size:1.1rem;'>${usd:,.2f} USD</b>
                </div>""", unsafe_allow_html=True)

        with t2:
            vnd = st.number_input("베트남동 (VND)", min_value=0, value=100000, step=50000, key="vnd1")
            if vnd > 0:
                krw = vnd / 18.5
                st.markdown(f"""
                <div class='card'>
                    🇰🇷 약 <b style='color:#ffd60a; font-size:1.3rem;'>{krw:,.0f}원</b>
                </div>""", unsafe_allow_html=True)
                st.info("💡 꿀팁: VND에서 0 하나 빼고 ÷2 하면 대충 원화! (10만동 ≈ 5천원)")

        with t3:
            usd = st.number_input("미국달러 (USD)", min_value=0.0, value=10.0, step=10.0, key="usd1")
            if usd > 0:
                krw = usd * 1370
                vnd = usd * 25400
                st.markdown(f"""
                <div class='card'>
                    🇰🇷 약 <b style='color:#ffd60a; font-size:1.3rem;'>{krw:,.0f}원</b><br>
                    🇻🇳 약 <b style='color:#ffd60a; font-size:1.1rem;'>{vnd:,.0f} VND</b>
                </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 12. 화면: 준비 (짐 + 비상)
# ═══════════════════════════════════════════════════════════════
def render_prep():
    sub1, sub2 = st.tabs(["🎒 짐 체크리스트", "🚨 비상 연락처"])

    with sub1:
        st.markdown("##### 5박 6일 짐 챙기기")
        all_items = []
        for cat, items in PACKING_LIST.items():
            with st.expander(f"**{cat}** ({len(items)}개)", expanded=True):
                for i, item in enumerate(items):
                    key = f"pack_{cat}_{i}"
                    checked = st.checkbox(item, key=key)
                    all_items.append(checked)
        
        done = sum(all_items)
        total = len(all_items)
        st.markdown("---")
        st.progress(done / total if total else 0)
        st.markdown(f"<center><b>준비 완료: {done} / {total}</b></center>", unsafe_allow_html=True)

    with sub2:
        st.markdown("##### 위급 상황 대비")
        st.caption("📞 번호를 길게 눌러 복사 → 전화 앱에서 붙여넣기")
        for name, phone, note in EMERGENCY:
            note_html = f"<div style='font-size:0.8rem; color:#9fd0ff; margin-top:4px;'>{note}</div>" if note else ""
            st.markdown(f"""
            <div class='emergency-card'>
                <b>{name}</b>
                <div style='font-size:1.1rem; color:#ffd60a; font-weight:700; letter-spacing:0.5px;'>{phone}</div>
                {note_html}
            </div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("""
        <div class='card'>
            <div class='card-title'>📋 사고 발생 시 행동 요령</div>
            <ol style='color:#fff; padding-left:20px; line-height:1.8;'>
                <li>가족 안전 먼저 확보 (인원수 체크)</li>
                <li>호텔 프론트 또는 한국대사관 영사콜센터 연락</li>
                <li>여행자보험 회사에도 연락 (영수증·진단서 보관)</li>
                <li>여권 분실시 → 대사관 → 임시여권 발급</li>
            </ol>
        </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 13. 메인
# ═══════════════════════════════════════════════════════════════
def main():
    st.markdown('<p class="main-title">🌴 나트랑 패밀리 베이스캠프</p>', unsafe_allow_html=True)
    st.markdown(
        f"<p class='subtitle'>2026.05.10 (일) ~ 05.15 (금) · 모벤픽 리조트 깜란 5박 6일 · 대가족 10명</p>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["🏠 홈", "📅 일정", "🤖 AI비서", "👨‍👩‍👧‍👦 가족", "💰 가계부", "🎒 준비"])

    with tabs[0]:
        render_home()
    with tabs[1]:
        render_itinerary()
    with tabs[2]:
        render_ai()
    with tabs[3]:
        render_family()
    with tabs[4]:
        render_budget()
    with tabs[5]:
        render_prep()


if __name__ == "__main__":
    main()
