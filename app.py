"""
나트랑 패밀리 베이스캠프 🌴
2026.05.10 (일) - 2026.05.15 (금) | 모벤픽 리조트 깜란 5박 6일

주요 기능:
- 일정 / 준비물 / 인원 자유 편집
- 실시간 HTML5 사진 줌 (재로딩 없음)
- Gemini 멀티 모델 fallback (404 자동 회피)
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
from math import radians, sin, cos, sqrt, atan2

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
# 2. 여행 상수
# ═══════════════════════════════════════════════════════════════
TRIP_START = date(2026, 5, 10)
TRIP_END = date(2026, 5, 15)
TOTAL_DAYS = (TRIP_END - TRIP_START).days + 1
HOTEL_NAME = "모벤픽 리조트 & 스파 깜란"
HOTEL_LAT = 11.9688
HOTEL_LON = 109.2162

LOCATIONS = ["🏨 모벤픽", "🏖️ 해변/수영장", "🍜 식당", "🎡 관광지", "🚐 이동중"]

# Gemini 모델 우선순위 (무료 한도 큰 순서대로 시도)
# 무료 티어 분당 요청 한도 (RPM):
#   - gemini-2.5-flash-lite: 15 RPM ← 가장 여유로움
#   - gemini-2.0-flash:      15 RPM
#   - gemini-2.5-flash:       5 RPM ← 가장 빨리 소진
#   - gemini-flash-latest:    가변
GEMINI_MODELS = [
    "gemini-2.5-flash-lite", # 1순위: 분당 15회 (가장 여유)
    "gemini-2.0-flash",      # 2순위: 분당 15회
    "gemini-2.5-flash",      # 3순위: 분당 5회 (품질 ↑ but 빨리 소진)
    "gemini-flash-latest",   # 4순위: fallback
]

# ─────────────────────────────────────────────
# 기본값 (사용자가 자유 편집 가능)
# ─────────────────────────────────────────────
DEFAULT_MEMBERS = [
    "아빠", "엄마", "할머니", "할아버지",
    "첫째 (4학년)", "윤우 (1학년)", "막내 (취학전)",
    "삼촌", "이모", "사촌",
]

DEFAULT_ITINERARY = {
    "2026-05-10": {
        "title": "출발 · 인천 → 깜란",
        "tip": "긴 비행, 편한 옷차림 / 아이들 멀미약 챙기기",
        "items": [
            ["출발 3h전", "🛫", "인천공항 집결"],
            ["비행", "✈️", "인천 → 깜란 (약 5시간 30분)"],
            ["도착 후", "🏨", "모벤픽 리조트 체크인"],
            ["저녁", "🍽️", "리조트 내 식사 & 휴식"],
        ],
    },
    "2026-05-11": {
        "title": "리조트 적응 · 모벤픽 만끽",
        "tip": "선크림 필수, 모자/래쉬가드 챙기기",
        "items": [
            ["07:00", "🌅", "조식 - 모벤픽 뷔페"],
            ["10:00", "🏊", "프라이빗 비치 & 수영장"],
            ["13:00", "🍜", "리조트 점심 또는 룸서비스"],
            ["15:00", "😴", "낮잠 / 키즈클럽 / 자유시간"],
            ["18:30", "🌆", "선셋 디너"],
        ],
    },
    "2026-05-12": {
        "title": "나트랑 시내 투어",
        "tip": "오후 햇볕 강함, 양산·물 챙기기",
        "items": [
            ["09:00", "🚐", "그랩카로 나트랑 시내 (약 40분)"],
            ["10:00", "⛪", "포나가르 참탑"],
            ["12:00", "🍲", "현지 쌀국수 점심"],
            ["14:00", "🛍️", "롯데마트 (간식·기념품)"],
            ["17:00", "🎡", "나트랑 야시장 & 저녁식사"],
        ],
    },
    "2026-05-13": {
        "title": "빈원더스 또는 자유 휴식",
        "tip": "물놀이용 옷·수건 별도 / 어르신은 리조트 추천",
        "items": [
            ["종일 A안", "🎢", "빈원더스 나트랑 (케이블카+워터파크)"],
            ["종일 B안", "🏖️", "리조트 풀빌라 휴식"],
            ["18:00", "🍤", "해산물 레스토랑 디너"],
        ],
    },
    "2026-05-14": {
        "title": "마지막 날 알차게",
        "tip": "짐 정리도 슬슬 시작",
        "items": [
            ["08:00", "🌅", "여유로운 조식"],
            ["10:00", "💆", "스파/마사지 (어른) · 키즈클럽 (아이)"],
            ["14:00", "🏊", "마지막 수영"],
            ["16:30", "📸", "가족 단체사진"],
            ["18:30", "🍽️", "특별 디너"],
        ],
    },
    "2026-05-15": {
        "title": "귀국 · 깜란 → 인천",
        "tip": "공항까지 약 20분 / 여권·기내가방 다시 확인",
        "items": [
            ["09:00", "🧳", "짐 정리 & 여권 점검"],
            ["11:00", "🚪", "체크아웃 (지연체크아웃 협의)"],
            ["공항", "🛍️", "깜란공항 면세점"],
            ["비행", "✈️", "깜란 → 인천"],
            ["도착", "🏠", "집으로!"],
        ],
    },
}

DEFAULT_PACKING = {
    "📄 서류·금융": [
        "여권 (전원 확인, 6개월 이상 유효)",
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
# 주요 명소 좌표 (구글지도용)
# ─────────────────────────────────────────────
PLACES = [
    {"name": "🏨 모벤픽 리조트 깜란", "lat": 11.9688, "lon": 109.2162, "info": "우리 숙소 (5박)"},
    {"name": "✈️ 깜란 국제공항", "lat": 11.9981, "lon": 109.2193, "info": "도착·출발지"},
    {"name": "🏖️ 깜란 베이 (롱비치)", "lat": 11.9695, "lon": 109.2190, "info": "리조트 인근 해변"},
    {"name": "⛪ 포나가르 참탑", "lat": 12.2654, "lon": 109.1956, "info": "9세기 힌두 사원"},
    {"name": "🛕 롱선사 (백불상)", "lat": 12.2515, "lon": 109.1794, "info": "거대 좌불상"},
    {"name": "⛪ 나트랑 대성당", "lat": 12.2476, "lon": 109.1853, "info": "고딕 양식 성당"},
    {"name": "🛍️ 롯데마트 나트랑", "lat": 12.2354, "lon": 109.1936, "info": "기념품·간식"},
    {"name": "🎡 나트랑 야시장", "lat": 12.2394, "lon": 109.1944, "info": "쇼핑·먹거리"},
    {"name": "🎢 빈원더스 나트랑", "lat": 12.2192, "lon": 109.2569, "info": "테마파크 (케이블카)"},
    {"name": "🍤 코스타 시푸드", "lat": 12.2334, "lon": 109.1956, "info": "유명 해산물 식당"},
    {"name": "🌊 혼쫑 곶", "lat": 12.2742, "lon": 109.2090, "info": "기암절벽 풍경"},
    {"name": "🏝️ 혼문섬 (스노클링)", "lat": 12.1819, "lon": 109.2950, "info": "보트 투어"},
]

# ═══════════════════════════════════════════════════════════════
# 3. 세션 상태 초기화
# ═══════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "members": list(DEFAULT_MEMBERS),
        "itinerary": json.loads(json.dumps(DEFAULT_ITINERARY)),
        "packing": json.loads(json.dumps(DEFAULT_PACKING)),
        "locations": {},
        "messages": [],
        "missions": [],
        "notices": [{
            "level": "공지", "icon": "🌴",
            "text": "환영합니다! 즐거운 나트랑 가족여행 되세요.",
            "time": datetime.now().strftime("%m/%d %H:%M"),
        }],
        "budget": 5_000_000,
        "expenses": [],
        "active_model": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # 멤버↔위치 동기화
    for m in st.session_state.members:
        if m not in st.session_state.locations:
            st.session_state.locations[m] = "🏨 모벤픽"
    for m in list(st.session_state.locations.keys()):
        if m not in st.session_state.members:
            del st.session_state.locations[m]

init_state()

# ═══════════════════════════════════════════════════════════════
# 4. API 키
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
# 5. Gemini API (다중 모델 fallback)
# ═══════════════════════════════════════════════════════════════
def gemini_request(content_parts):
    """여러 모델을 순차 시도. 처음 성공한 모델은 캐시.
    404(모델 없음) + 429(할당량 초과) 모두 자동으로 다음 모델로 넘김."""
    if not KEY_GEMINI:
        return None, "❌ Gemini API 키가 없습니다.\n\n.streamlit/secrets.toml 에 등록:\n```\n[api_keys]\ngemini = \"your-key\"\n```"

    models_order = list(GEMINI_MODELS)
    if st.session_state.active_model and st.session_state.active_model in models_order:
        models_order.remove(st.session_state.active_model)
        models_order.insert(0, st.session_state.active_model)

    errors = []
    quota_exceeded_count = 0
    
    for model_name in models_order:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(content_parts)
            st.session_state.active_model = model_name
            return response.text, None
        except Exception as e:
            err_msg = str(e)
            err_lower = err_msg.lower()
            
            is_quota = "429" in err_msg or "quota" in err_lower or "rate limit" in err_lower or "exceeded" in err_lower
            is_not_found = "404" in err_msg or "not found" in err_lower
            
            if is_quota:
                quota_exceeded_count += 1
                errors.append(f"• `{model_name}`: 분당 한도 초과")
            else:
                errors.append(f"• `{model_name}`: {err_msg[:100]}")
            
            # 404, 429 외의 에러(인증 등)는 즉시 중단
            if not is_not_found and not is_quota:
                st.session_state.active_model = None
                return None, f"🚨 API 오류 ({model_name}):\n\n{err_msg}"
            
            # 캐시된 모델이 실패한 경우 캐시 무효화
            if model_name == st.session_state.active_model:
                st.session_state.active_model = None
            continue

    st.session_state.active_model = None
    
    if quota_exceeded_count == len(models_order):
        return None, ("⏱️ **모든 모델의 분당 한도가 초과됐습니다.**\n\n"
                      "💡 **해결 방법**:\n"
                      "1. **30~60초 기다린 후 다시 시도** (분당 카운터 자동 리셋)\n"
                      "2. https://aistudio.google.com/apikey 에서 결제 등록 시 한도 대폭 증가\n"
                      "3. 사용량 확인: https://ai.dev/rate-limit\n\n"
                      "📊 **무료 티어 분당 한도(RPM)**:\n"
                      "• gemini-2.5-flash-lite: 15회\n"
                      "• gemini-2.0-flash: 15회\n"
                      "• gemini-2.5-flash: 5회\n\n"
                      "💰 **결제 등록 후 한도(Tier 1)**:\n"
                      "• 거의 모든 모델 1,000~2,000 RPM\n"
                      "• 가족여행 정도면 절대 초과 안 함")
    
    return None, ("🚨 모든 Gemini 모델 호출 실패.\n\n시도 결과:\n" + "\n".join(errors) + 
                  "\n\n💡 해결 방법:\n"
                  "1. `pip install -U google-generativeai` 라이브러리 업데이트\n"
                  "2. https://aistudio.google.com 에서 API 키 유효성 확인\n"
                  "3. 30~60초 후 재시도")


def gemini_call(prompt):
    return gemini_request(prompt)


def gemini_vision(prompt, image):
    return gemini_request([prompt, image])

# ═══════════════════════════════════════════════════════════════
# 6. 유틸
# ═══════════════════════════════════════════════════════════════
def get_trip_status():
    today = date.today()
    if today < TRIP_START:
        return "before", (TRIP_START - today).days, 0
    elif today > TRIP_END:
        return "after", 0, TOTAL_DAYS
    return "during", 0, (today - TRIP_START).days + 1


def get_weather(lat, lon):
    if not KEY_WEATHER:
        return None
    try:
        res = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": KEY_WEATHER, "units": "metric", "lang": "kr"},
            timeout=4,
        ).json()
        return {
            "temp": res["main"]["temp"], "feels": res["main"]["feels_like"],
            "humidity": res["main"]["humidity"], "desc": res["weather"][0]["description"],
            "icon": res["weather"][0]["icon"],
        }
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_exchange_rates():
    """무료 환율 API. KRW 1원 기준 환율 반환. 10분 캐시."""
    try:
        res = requests.get("https://open.er-api.com/v6/latest/KRW", timeout=4).json()
        if res.get("result") == "success":
            updated = res.get("time_last_update_utc", "")
            return res["rates"], updated, None
    except Exception as e:
        return None, None, str(e)
    return None, None, "API 응답 오류"


def get_rates():
    """실시간 환율 + 실패시 기본값 fallback"""
    rates, updated, err = fetch_exchange_rates()
    if rates and "VND" in rates and "USD" in rates:
        # 1 KRW 기준 → 1원당 VND, 1원당 USD
        vnd_per_krw = rates["VND"]
        usd_per_krw = rates["USD"]
        krw_per_usd = 1 / usd_per_krw if usd_per_krw else 1370
        vnd_per_usd = krw_per_usd * vnd_per_krw
        return {
            "vnd_per_krw": vnd_per_krw,
            "usd_per_krw": usd_per_krw,
            "krw_per_usd": krw_per_usd,
            "vnd_per_usd": vnd_per_usd,
            "updated": updated,
            "live": True,
        }
    # 기본값 (API 실패시)
    return {
        "vnd_per_krw": 18.5, "usd_per_krw": 1/1370,
        "krw_per_usd": 1370, "vnd_per_usd": 25400,
        "updated": "", "live": False,
    }


@st.cache_data(ttl=600, show_spinner=False)
def cached_translate_to_vi(text):
    """한→베 번역 (10분 캐시, 동일 입력은 즉시 반환)"""
    p = f"""다음 한국어를 베트남어로 번역하고 한글 발음을 알려주세요.
형식만 정확히 지키고 다른 설명은 하지 마세요:

🇻🇳 베트남어: ...
🔊 발음: ...
💡 팁: (있다면 한 줄)

한국어: {text}"""
    return gemini_call(p)


def haversine_km(lat1, lon1, lat2, lon2):
    """두 좌표 간 직선거리 (km)"""
    R = 6371
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))


def weekday_kr(d):
    return ["월", "화", "수", "목", "금", "토", "일"][d.weekday()]


def date_str_to_obj(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

# ═══════════════════════════════════════════════════════════════
# 7. CSS
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
.stApp { background: linear-gradient(160deg, #0a2540 0%, #1a4d7a 50%, #2c7da0 100%); }
.main-title { font-size: 2rem; font-weight: 900; color: #ffd60a; margin: 0; text-align: center; letter-spacing: -0.5px; }
.subtitle { text-align: center; color: #cfe8ff; font-size: 0.9rem; margin-bottom: 12px; }
.card { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
        border-radius: 14px; padding: 16px; margin-bottom: 10px; }
.card-title { color: #ffd60a; font-weight: 700; font-size: 1.05rem; margin-bottom: 8px; }
.dday-card { background: linear-gradient(135deg, #ff6b6b 0%, #ffd60a 100%);
             color: #1a1a1a; text-align: center; border-radius: 18px; padding: 22px;
             margin-bottom: 16px; box-shadow: 0 8px 24px rgba(0,0,0,0.2); }
.dday-num { font-size: 3rem; font-weight: 900; line-height: 1; }
.timeline-item { background: rgba(255,255,255,0.06); border-left: 3px solid #ffd60a;
                 padding: 10px 14px; margin-bottom: 6px; border-radius: 0 8px 8px 0; color: #fff; }
.timeline-time { color: #9fd0ff; font-weight: 600; min-width: 90px; display: inline-block; }
.phrase-card { background: rgba(255,255,255,0.07); padding: 12px 14px; border-radius: 10px;
               margin-bottom: 6px; border-left: 3px solid #2c7da0; }
.phrase-ko { color: #ffd60a; font-weight: 700; font-size: 0.95rem; }
.phrase-vi { color: #fff; font-size: 1.1rem; font-weight: 600; margin-top: 2px; }
.phrase-pron { color: #9fd0ff; font-style: italic; font-size: 0.85rem; }
.emergency-card { background: rgba(255,75,75,0.12); border-left: 3px solid #ff4b4b;
                  padding: 10px 14px; border-radius: 0 8px 8px 0; margin-bottom: 6px; color: #fff; }
.location-pill { background: rgba(255,214,10,0.15); border: 1px solid rgba(255,214,10,0.3);
                 padding: 6px 12px; border-radius: 20px; display: inline-block;
                 margin: 2px; font-size: 0.85rem; color: #fff; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] { background: rgba(255,255,255,0.05); border-radius: 8px 8px 0 0; padding: 8px 14px; }
.stTabs [aria-selected="true"] { background: rgba(255,214,10,0.2) !important; color: #ffd60a !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 8. HTML5 실시간 줌 컴포넌트
# ═══════════════════════════════════════════════════════════════
def html_zoom_viewer(image_pil, height=560):
    """Streamlit 재실행 없이 실시간 작동하는 HTML5 줌 뷰어.
    슬라이더/버튼/마우스휠/드래그 모두 지원."""
    buf = io.BytesIO()
    img_rgb = image_pil.convert("RGB") if image_pil.mode != "RGB" else image_pil
    img_rgb.save(buf, format="JPEG", quality=88)
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    
    html_code = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; color: #fff;">
        <div id="zoom-wrap" style="
            background: rgba(0,0,0,0.3); 
            border-radius: 10px; 
            padding: 8px; 
            border: 1px solid rgba(255,255,255,0.15);
            max-height: {height-90}px;
            overflow: auto;
            text-align: center;
            cursor: grab;
            user-select: none;
        ">
            <img id="zoom-img" 
                 src="data:image/jpeg;base64,{img_b64}" 
                 style="width: 100%; max-width: none; 
                        transition: width 0.05s ease-out;
                        border-radius: 6px; pointer-events: none;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.3);"
                 draggable="false">
        </div>
        <div style="display:flex; gap:10px; align-items:center; margin-top:10px;
                    background: rgba(255,255,255,0.08); padding: 8px 12px; border-radius: 10px;">
            <button id="zoom-out" style="
                background: #ffd60a; color: #1a1a1a; border: none;
                width: 36px; height: 36px; border-radius: 8px;
                font-size: 1.2rem; font-weight: 900; cursor: pointer;
            ">−</button>
            <input type="range" id="zoom-slider" 
                   min="0.3" max="3" step="0.05" value="1"
                   style="flex: 1; cursor: pointer; accent-color: #ffd60a;">
            <button id="zoom-in" style="
                background: #ffd60a; color: #1a1a1a; border: none;
                width: 36px; height: 36px; border-radius: 8px;
                font-size: 1.2rem; font-weight: 900; cursor: pointer;
            ">+</button>
            <button id="zoom-reset" style="
                background: rgba(255,255,255,0.15); color: #fff; 
                border: 1px solid rgba(255,255,255,0.3);
                padding: 0 12px; height: 36px; border-radius: 8px;
                font-size: 0.85rem; cursor: pointer;
            ">초기화</button>
            <span id="zoom-label" style="
                color: #ffd60a; font-weight: 700; min-width: 50px; 
                text-align: right; font-size: 0.95rem;
            ">1.0x</span>
        </div>
        <div style="text-align:center; color:#9fd0ff; font-size:0.78rem; margin-top:6px;">
            💡 슬라이더 / 버튼 / Ctrl+휠로 실시간 줌 · 드래그로 스크롤
        </div>
    </div>
    
    <script>
    (function() {{
        const img = document.getElementById('zoom-img');
        const slider = document.getElementById('zoom-slider');
        const label = document.getElementById('zoom-label');
        const wrap = document.getElementById('zoom-wrap');
        const btnIn = document.getElementById('zoom-in');
        const btnOut = document.getElementById('zoom-out');
        const btnReset = document.getElementById('zoom-reset');
        
        function update() {{
            const v = parseFloat(slider.value);
            img.style.width = (v * 100) + '%';
            label.textContent = v.toFixed(1) + 'x';
        }}
        
        function changeZoom(delta) {{
            const v = Math.max(0.3, Math.min(3, parseFloat(slider.value) + delta));
            slider.value = v;
            update();
        }}
        
        slider.addEventListener('input', update);
        btnIn.addEventListener('click', () => changeZoom(0.2));
        btnOut.addEventListener('click', () => changeZoom(-0.2));
        btnReset.addEventListener('click', () => {{ slider.value = 1; update(); }});
        
        wrap.addEventListener('wheel', (e) => {{
            if (e.ctrlKey || e.metaKey) {{
                e.preventDefault();
                changeZoom(e.deltaY > 0 ? -0.1 : 0.1);
            }}
        }}, {{ passive: false }});
        
        let isDown = false, startX = 0, startY = 0, scrollLeft = 0, scrollTop = 0;
        wrap.addEventListener('mousedown', (e) => {{
            isDown = true; wrap.style.cursor = 'grabbing';
            startX = e.pageX - wrap.offsetLeft; startY = e.pageY - wrap.offsetTop;
            scrollLeft = wrap.scrollLeft; scrollTop = wrap.scrollTop;
        }});
        wrap.addEventListener('mouseup', () => {{ isDown = false; wrap.style.cursor = 'grab'; }});
        wrap.addEventListener('mouseleave', () => {{ isDown = false; wrap.style.cursor = 'grab'; }});
        wrap.addEventListener('mousemove', (e) => {{
            if (!isDown) return;
            e.preventDefault();
            wrap.scrollLeft = scrollLeft - (e.pageX - wrap.offsetLeft - startX);
            wrap.scrollTop = scrollTop - (e.pageY - wrap.offsetTop - startY);
        }});
        
        // 터치 핀치 줌 (모바일)
        let pinchStart = 0, pinchStartZoom = 1;
        wrap.addEventListener('touchstart', (e) => {{
            if (e.touches.length === 2) {{
                pinchStart = Math.hypot(
                    e.touches[0].pageX - e.touches[1].pageX,
                    e.touches[0].pageY - e.touches[1].pageY
                );
                pinchStartZoom = parseFloat(slider.value);
            }}
        }});
        wrap.addEventListener('touchmove', (e) => {{
            if (e.touches.length === 2) {{
                e.preventDefault();
                const d = Math.hypot(
                    e.touches[0].pageX - e.touches[1].pageX,
                    e.touches[0].pageY - e.touches[1].pageY
                );
                const newZoom = Math.max(0.3, Math.min(3, pinchStartZoom * (d / pinchStart)));
                slider.value = newZoom;
                update();
            }}
        }}, {{ passive: false }});
    }})();
    </script>
    """
    st.components.v1.html(html_code, height=height)

# ═══════════════════════════════════════════════════════════════
# 9. 화면: 홈
# ═══════════════════════════════════════════════════════════════
def render_home():
    status, days_left, day_num = get_trip_status()
    today = date.today()

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

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("#### 📅 오늘의 일정")
        today_key = today.strftime("%Y-%m-%d")
        target_key = today_key if today_key in st.session_state.itinerary else (
            TRIP_START.strftime("%Y-%m-%d") if status == "before" else None
        )
        if target_key:
            data = st.session_state.itinerary[target_key]
            d = date_str_to_obj(target_key)
            label = "오늘" if target_key == today_key else f"여행 첫날 ({d.month}/{d.day})"
            st.caption(f"{label} · {data['title']}")
            if data.get("tip"):
                st.info(f"💡 {data['tip']}")
            for item in data["items"][:5]:
                if len(item) >= 3:
                    time_, icon, task = item[0], item[1], item[2]
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
                <div>5월 깜란 평균</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("#### 📊 한눈에")
        spent = sum(e["amt"] for e in st.session_state.expenses)
        remain = st.session_state.budget - spent
        c1, c2 = st.columns(2)
        c1.metric("남은 예산", f"{remain:,}원")
        c2.metric("인원", f"{len(st.session_state.members)}명")

# ═══════════════════════════════════════════════════════════════
# 9-2. 화면: 실시간 인터랙티브 지도 (Leaflet + Google Maps 토글)
# ═══════════════════════════════════════════════════════════════
def render_map_leaflet():
    """무료 Leaflet 모드 - API 키 불필요, 12개 마커 한번에 표시"""
    places_json = json.dumps(PLACES, ensure_ascii=False)
    avg_lat = sum(p["lat"] for p in PLACES) / len(PLACES)
    avg_lon = sum(p["lon"] for p in PLACES) / len(PLACES)
    
    leaflet_html = f"""
    <link rel="stylesheet" 
          href="https://unpkg.com/[email protected]/dist/leaflet.css"
          crossorigin=""/>
    <script src="https://unpkg.com/[email protected]/dist/leaflet.js"
            crossorigin=""></script>
    
    <style>
        .leaflet-popup-content-wrapper {{
            border-radius: 10px !important;
            background: #1a4d7a !important;
            color: #fff !important;
        }}
        .leaflet-popup-content {{ margin: 12px 14px !important; min-width: 200px; }}
        .leaflet-popup-tip {{ background: #1a4d7a !important; }}
        .leaflet-container {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            border-radius: 12px;
        }}
        .leaflet-control-zoom a {{
            background-color: #ffd60a !important;
            color: #1a1a1a !important;
            border: none !important;
            font-weight: 900;
        }}
        .marker-pin {{
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            border: 2px solid #fff;
        }}
    </style>
    
    <div id="map-leaflet" style="height: 520px; width: 100%; border-radius: 12px;
                                  box-shadow: 0 6px 20px rgba(0,0,0,0.25);"></div>
    
    <div style="display:flex; gap:10px; margin-top:10px; flex-wrap:wrap;">
        <button onclick="window._fitAllL()" style="
            background: #ffd60a; color: #1a1a1a; border: none;
            padding: 8px 14px; border-radius: 8px; font-weight: 700;
            cursor: pointer; flex: 1; min-width: 100px;
        ">🗺️ 전체 보기</button>
        <button onclick="window._goHotelL()" style="
            background: #ff4b4b; color: #fff; border: none;
            padding: 8px 14px; border-radius: 8px; font-weight: 700;
            cursor: pointer; flex: 1; min-width: 100px;
        ">🏨 호텔로</button>
        <button onclick="window._goNTL()" style="
            background: #2c7da0; color: #fff; border: none;
            padding: 8px 14px; border-radius: 8px; font-weight: 700;
            cursor: pointer; flex: 1; min-width: 100px;
        ">🎡 나트랑</button>
    </div>
    
    <script>
    (function() {{
        const places = {places_json};
        const hotel = places[0];
        
        const map = L.map('map-leaflet').setView([{avg_lat}, {avg_lon}], 11);
        
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '© OpenStreetMap · © CARTO',
            maxZoom: 19, subdomains: 'abcd',
        }}).addTo(map);
        
        function distKm(lat1, lon1, lat2, lon2) {{
            const R = 6371;
            const p1 = lat1 * Math.PI / 180, p2 = lat2 * Math.PI / 180;
            const dp = (lat2-lat1) * Math.PI / 180, dl = (lon2-lon1) * Math.PI / 180;
            const a = Math.sin(dp/2)**2 + Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)**2;
            return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        }}
        
        function makeIcon(emoji, isHotel) {{
            const bg = isHotel ? '#ff4b4b' : '#ffd60a';
            const color = isHotel ? '#fff' : '#1a1a1a';
            const size = isHotel ? 44 : 36;
            return L.divIcon({{
                html: `<div class="marker-pin" style="
                    background: ${{bg}}; color: ${{color}};
                    width: ${{size}}px; height: ${{size}}px;
                    border-radius: 50%; font-size: ${{isHotel ? '1.4rem' : '1.1rem'}};
                ">${{emoji}}</div>`,
                iconSize: [size, size], iconAnchor: [size/2, size/2],
                popupAnchor: [0, -size/2], className: '',
            }});
        }}
        
        const markers = [];
        places.forEach((p, i) => {{
            const isHotel = i === 0;
            const emoji = p.name.split(' ')[0];
            const dist = isHotel ? '🏠 우리 숙소' : `🏨 호텔에서 ${{distKm(hotel.lat, hotel.lon, p.lat, p.lon).toFixed(1)}}km`;
            const placeUrl = `https://www.google.com/maps/search/?api=1&query=${{p.lat}},${{p.lon}}`;
            const dirUrl = `https://www.google.com/maps/dir/?api=1&origin=${{hotel.lat}},${{hotel.lon}}&destination=${{p.lat}},${{p.lon}}`;
            
            const popup = `
                <div>
                    <div style="font-weight:800; font-size:1rem; color:#ffd60a; margin-bottom:4px;">${{p.name}}</div>
                    <div style="font-size:0.85rem; color:#cfe8ff; margin-bottom:6px;">${{p.info}}</div>
                    <div style="font-size:0.8rem; color:#9fd0ff; margin-bottom:10px;">${{dist}}</div>
                    <div style="display:flex; gap:6px; flex-wrap:wrap;">
                        <a href="${{placeUrl}}" target="_blank" style="
                            background: #4285f4; color: white; padding: 6px 10px;
                            border-radius: 6px; text-decoration: none; font-size: 0.78rem; font-weight: 600;
                        ">📱 구글지도</a>
                        ${{!isHotel ? `<a href="${{dirUrl}}" target="_blank" style="
                            background: #34a853; color: white; padding: 6px 10px;
                            border-radius: 6px; text-decoration: none; font-size: 0.78rem; font-weight: 600;
                        ">🚗 길찾기</a>` : ''}}
                    </div>
                </div>`;
            
            const marker = L.marker([p.lat, p.lon], {{ icon: makeIcon(emoji, isHotel) }})
                .addTo(map).bindPopup(popup, {{ maxWidth: 280 }});
            markers.push(marker);
        }});
        
        const ntCenter = places.find(p => p.name.includes('야시장'));
        if (ntCenter) {{
            L.polyline([[hotel.lat, hotel.lon], [ntCenter.lat, ntCenter.lon]], {{
                color: '#ffd60a', weight: 2, opacity: 0.5, dashArray: '8, 8',
            }}).addTo(map);
        }}
        
        const group = L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.15));
        
        window._fitAllL = () => map.fitBounds(group.getBounds().pad(0.15));
        window._goHotelL = () => {{ map.setView([hotel.lat, hotel.lon], 15); markers[0].openPopup(); }};
        window._goNTL = () => map.setView([12.245, 109.190], 14);
    }})();
    </script>
    """
    st.components.v1.html(leaflet_html, height=620)


def render_map_google(api_key):
    """진짜 Google Maps JavaScript API - API 키 필요"""
    places_json = json.dumps(PLACES, ensure_ascii=False)
    avg_lat = sum(p["lat"] for p in PLACES) / len(PLACES)
    avg_lon = sum(p["lon"] for p in PLACES) / len(PLACES)
    
    google_html = f"""
    <div id="map-google" style="height: 520px; width: 100%; border-radius: 12px;
                                 box-shadow: 0 6px 20px rgba(0,0,0,0.25);"></div>
    
    <div style="display:flex; gap:10px; margin-top:10px; flex-wrap:wrap;">
        <button onclick="window._fitAllG()" style="
            background: #ffd60a; color: #1a1a1a; border: none;
            padding: 8px 14px; border-radius: 8px; font-weight: 700;
            cursor: pointer; flex: 1; min-width: 100px;
        ">🗺️ 전체 보기</button>
        <button onclick="window._goHotelG()" style="
            background: #ff4b4b; color: #fff; border: none;
            padding: 8px 14px; border-radius: 8px; font-weight: 700;
            cursor: pointer; flex: 1; min-width: 100px;
        ">🏨 호텔로</button>
        <button onclick="window._goNTG()" style="
            background: #2c7da0; color: #fff; border: none;
            padding: 8px 14px; border-radius: 8px; font-weight: 700;
            cursor: pointer; flex: 1; min-width: 100px;
        ">🎡 나트랑</button>
    </div>
    
    <script>
    function initGoogleMap() {{
        const places = {places_json};
        const hotel = places[0];
        
        const map = new google.maps.Map(document.getElementById('map-google'), {{
            center: {{ lat: {avg_lat}, lng: {avg_lon} }},
            zoom: 11,
            mapTypeControl: true,
            streetViewControl: true,
            fullscreenControl: true,
        }});
        
        function distKm(lat1, lon1, lat2, lon2) {{
            const R = 6371;
            const p1 = lat1 * Math.PI / 180, p2 = lat2 * Math.PI / 180;
            const dp = (lat2-lat1) * Math.PI / 180, dl = (lon2-lon1) * Math.PI / 180;
            const a = Math.sin(dp/2)**2 + Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)**2;
            return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        }}
        
        const bounds = new google.maps.LatLngBounds();
        const markers = [];
        const infoWindow = new google.maps.InfoWindow();
        
        places.forEach((p, i) => {{
            const isHotel = i === 0;
            const emoji = p.name.split(' ')[0];
            const dist = isHotel ? '🏠 우리 숙소' : `🏨 호텔에서 ${{distKm(hotel.lat, hotel.lon, p.lat, p.lon).toFixed(1)}}km`;
            
            const marker = new google.maps.Marker({{
                position: {{ lat: p.lat, lng: p.lon }},
                map: map,
                title: p.name,
                label: {{
                    text: emoji,
                    fontSize: isHotel ? '20px' : '16px',
                }},
                icon: {{
                    path: google.maps.SymbolPath.CIRCLE,
                    fillColor: isHotel ? '#ff4b4b' : '#ffd60a',
                    fillOpacity: 1,
                    strokeColor: '#fff',
                    strokeWeight: 2,
                    scale: isHotel ? 22 : 18,
                }},
                zIndex: isHotel ? 999 : 1,
            }});
            
            const placeUrl = `https://www.google.com/maps/search/?api=1&query=${{p.lat}},${{p.lon}}`;
            const dirUrl = `https://www.google.com/maps/dir/?api=1&origin=${{hotel.lat}},${{hotel.lon}}&destination=${{p.lat}},${{p.lon}}`;
            
            const content = `
                <div style="min-width:220px; font-family:-apple-system,sans-serif;">
                    <div style="font-weight:800; font-size:1rem; margin-bottom:4px;">${{p.name}}</div>
                    <div style="font-size:0.88rem; color:#555; margin-bottom:6px;">${{p.info}}</div>
                    <div style="font-size:0.82rem; color:#888; margin-bottom:10px;">${{dist}}</div>
                    <div style="display:flex; gap:6px;">
                        <a href="${{placeUrl}}" target="_blank" style="
                            background:#4285f4; color:white; padding:6px 10px;
                            border-radius:6px; text-decoration:none; font-size:0.78rem; font-weight:600;
                        ">📱 구글지도</a>
                        ${{!isHotel ? `<a href="${{dirUrl}}" target="_blank" style="
                            background:#34a853; color:white; padding:6px 10px;
                            border-radius:6px; text-decoration:none; font-size:0.78rem; font-weight:600;
                        ">🚗 길찾기</a>` : ''}}
                    </div>
                </div>`;
            
            marker.addListener('click', () => {{
                infoWindow.setContent(content);
                infoWindow.open(map, marker);
            }});
            
            markers.push(marker);
            bounds.extend(marker.getPosition());
        }});
        
        // 호텔→야시장 점선
        const ntCenter = places.find(p => p.name.includes('야시장'));
        if (ntCenter) {{
            new google.maps.Polyline({{
                path: [
                    {{ lat: hotel.lat, lng: hotel.lon }},
                    {{ lat: ntCenter.lat, lng: ntCenter.lon }}
                ],
                geodesic: true,
                strokeColor: '#ffd60a',
                strokeOpacity: 0,
                icons: [{{
                    icon: {{ path: 'M 0,-1 0,1', strokeOpacity: 0.6, scale: 3 }},
                    offset: '0', repeat: '15px',
                }}],
                map: map,
            }});
        }}
        
        map.fitBounds(bounds);
        
        window._fitAllG = () => map.fitBounds(bounds);
        window._goHotelG = () => {{
            map.setCenter({{ lat: hotel.lat, lng: hotel.lon }});
            map.setZoom(15);
            new google.maps.event.trigger(markers[0], 'click');
        }};
        window._goNTG = () => {{
            map.setCenter({{ lat: 12.245, lng: 109.190 }});
            map.setZoom(14);
        }};
    }}
    </script>
    <script async defer
        src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initGoogleMap&language=ko&region=KR">
    </script>
    """
    st.components.v1.html(google_html, height=620)


def render_map():
    st.markdown("### 🗺️ 깜란 & 나트랑 실시간 지도")
    
    # ─ Google API 키 확인 ─
    google_key = ""
    try:
        google_key = st.secrets["api_keys"]["google_maps"]
    except Exception:
        pass
    
    # ─ 모드 토글 ─
    col_mode, col_info = st.columns([2, 3])
    with col_mode:
        if google_key:
            mode = st.radio(
                "지도 모드",
                ["🟢 Leaflet (무료)", "🔵 Google Maps (실시간)"],
                horizontal=False,
                key="map_mode",
                label_visibility="collapsed",
            )
        else:
            mode = "🟢 Leaflet (무료)"
            st.info("🟢 Leaflet 모드 사용 중")
    
    with col_info:
        if "Google" in mode:
            st.caption("✅ 진짜 구글지도 · 스트리트뷰·교통상황 모두 사용 가능")
        else:
            st.caption("📌 모든 명소가 한 지도에 · 마커 클릭 → 정보 확인 · API 키 불필요")
            if not google_key:
                with st.expander("🔵 진짜 구글지도 사용하고 싶다면?"):
                    st.markdown("""
                    1. https://console.cloud.google.com 접속
                    2. **Maps JavaScript API** 활성화
                    3. API 키 발급 (월 $200 무료 크레딧)
                    4. `.streamlit/secrets.toml`에 추가:
                    ```toml
                    [api_keys]
                    google_maps = "AIza..."
                    ```
                    """)
    
    # ─ 지도 렌더링 ─
    if "Google" in mode and google_key:
        render_map_google(google_key)
    else:
        render_map_leaflet()
    
    # ─ 단일 장소 상세 ─
    st.markdown("---")
    st.markdown("##### 📍 특정 장소 상세 보기")
    
    hotel = PLACES[0]
    col_select, col_info = st.columns([2, 1])
    with col_select:
        selected_name = st.selectbox(
            "장소 선택", [p["name"] for p in PLACES],
            key="map_place_sel", label_visibility="collapsed",
        )
    place = next(p for p in PLACES if p["name"] == selected_name)
    
    with col_info:
        if place["name"] == hotel["name"]:
            dist_text = "🏠 우리 숙소"
        else:
            d = haversine_km(hotel["lat"], hotel["lon"], place["lat"], place["lon"])
            dist_text = f"🏨 호텔에서 약 {d:.1f}km"
        st.markdown(f"""
        <div class='card'>
            <div style='color:#ffd60a; font-weight:700; font-size:0.95rem;'>{place['info']}</div>
            <div style='font-size:0.85rem; color:#9fd0ff; margin-top:4px;'>{dist_text}</div>
        </div>
        """, unsafe_allow_html=True)
    
    embed_url = f"https://maps.google.com/maps?q={place['lat']},{place['lon']}&hl=ko&z=16&output=embed"
    st.components.v1.iframe(embed_url, height=380)
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        gmaps_url = f"https://www.google.com/maps/search/?api=1&query={place['lat']},{place['lon']}"
        st.link_button("📱 구글 지도 앱으로 열기", gmaps_url, use_container_width=True)
    with col_b2:
        if place["name"] != hotel["name"]:
            dir_url = f"https://www.google.com/maps/dir/?api=1&origin={hotel['lat']},{hotel['lon']}&destination={place['lat']},{place['lon']}"
            st.link_button("🚗 호텔에서 길찾기", dir_url, use_container_width=True)
        else:
            st.link_button("ℹ️ 호텔 정보", gmaps_url, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# 10. 화면: 일정 (편집 가능)
# ═══════════════════════════════════════════════════════════════
def render_itinerary():
    st.markdown("### 📅 5박 6일 일정")
    
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.caption("✏️ 편집 모드를 켜면 일정을 자유롭게 수정할 수 있어요")
    with col_h2:
        edit_mode = st.toggle("편집 모드", key="itin_edit")

    today = date.today()
    sorted_keys = sorted(st.session_state.itinerary.keys())
    
    labels = []
    for key in sorted_keys:
        d = date_str_to_obj(key)
        n = (d - TRIP_START).days + 1
        labels.append(f"D{n}·{d.month}/{d.day}({weekday_kr(d)})")

    tabs = st.tabs(labels)
    
    for tab, key in zip(tabs, sorted_keys):
        with tab:
            d = date_str_to_obj(key)
            data = st.session_state.itinerary[key]
            
            badge = ""
            if d == today:
                badge = " <span style='background:#ff4b4b; color:#fff; padding:2px 10px; border-radius:12px; font-size:0.75rem;'>오늘</span>"
            
            if edit_mode:
                with st.container(border=True):
                    new_title = st.text_input("📌 제목", data["title"], key=f"title_{key}")
                    new_tip = st.text_input("💡 그날의 팁", data.get("tip", ""), key=f"tip_{key}")
                    
                    st.session_state.itinerary[key]["title"] = new_title
                    st.session_state.itinerary[key]["tip"] = new_tip
                    
                    st.markdown("**🕐 일정 항목**")
                    for i, item in enumerate(data["items"]):
                        c1, c2, c3, c4 = st.columns([2, 1, 5, 1])
                        with c1:
                            new_time = st.text_input("시간", item[0], key=f"time_{key}_{i}", label_visibility="collapsed")
                        with c2:
                            new_icon = st.text_input("아이콘", item[1], key=f"icon_{key}_{i}", label_visibility="collapsed", max_chars=4)
                        with c3:
                            new_task = st.text_input("내용", item[2], key=f"task_{key}_{i}", label_visibility="collapsed")
                        with c4:
                            if st.button("🗑️", key=f"del_{key}_{i}", use_container_width=True):
                                st.session_state.itinerary[key]["items"].pop(i)
                                st.rerun()
                        st.session_state.itinerary[key]["items"][i] = [new_time, new_icon, new_task]
                    
                    st.markdown("**➕ 새 항목 추가**")
                    nc1, nc2, nc3, nc4 = st.columns([2, 1, 5, 1])
                    with nc1:
                        add_time = st.text_input("시간", key=f"add_time_{key}", placeholder="14:00", label_visibility="collapsed")
                    with nc2:
                        add_icon = st.text_input("아이콘", key=f"add_icon_{key}", placeholder="🍜", label_visibility="collapsed", max_chars=4)
                    with nc3:
                        add_task = st.text_input("내용", key=f"add_task_{key}", placeholder="할 일", label_visibility="collapsed")
                    with nc4:
                        if st.button("➕", key=f"add_btn_{key}", use_container_width=True):
                            if add_time and add_task:
                                st.session_state.itinerary[key]["items"].append([
                                    add_time, add_icon or "📌", add_task
                                ])
                                st.rerun()
            else:
                st.markdown(f"<h4 style='color:#ffd60a; margin-bottom:4px;'>{data['title']}{badge}</h4>", unsafe_allow_html=True)
                if data.get("tip"):
                    st.caption(f"💡 {data['tip']}")
                st.markdown("<br>", unsafe_allow_html=True)
                for item in data["items"]:
                    if len(item) >= 3:
                        time_, icon, task = item[0], item[1], item[2]
                        st.markdown(f"""
                        <div class='timeline-item'>
                            <span class='timeline-time'>{time_}</span> {icon} <b>{task}</b>
                        </div>""", unsafe_allow_html=True)
    
    if edit_mode:
        st.markdown("---")
        if st.button("🔄 일정 기본값 복원", help="모든 일정을 초기 상태로"):
            st.session_state.itinerary = json.loads(json.dumps(DEFAULT_ITINERARY))
            st.rerun()

# ═══════════════════════════════════════════════════════════════
# 11. 화면: AI 비서
# ═══════════════════════════════════════════════════════════════
def render_ai():
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🤖 AI 채팅", "🇻🇳 베트남어 회화", "📷 사진 번역"])

    if st.session_state.active_model:
        rpm_info = {
            "gemini-2.5-flash-lite": "분당 15회",
            "gemini-2.0-flash": "분당 15회",
            "gemini-2.5-flash": "분당 5회",
            "gemini-flash-latest": "가변",
        }
        rpm = rpm_info.get(st.session_state.active_model, "?")
        st.caption(f"✅ 사용 중: `{st.session_state.active_model}` · 무료 한도 {rpm}")

    with sub_tab1:
        st.markdown("##### 무엇이든 물어보세요")
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
                context = f"""당신은 베트남 나트랑/깜란 가족여행 전문 도우미입니다.
여행: 2026.5.10~5.15, 모벤픽 리조트 깜란 5박, 가족 {len(st.session_state.members)}명 (4학년·1학년·미취학 아이 포함, 어르신 포함).
한국어로 친절하고 실용적으로, 핵심만 간결하게 답하세요.

질문: {prompt}"""
                text, err = gemini_call(context)
                if text:
                    st.session_state.messages.append({"role": "assistant", "content": text})
                    st.rerun()
                else:
                    st.error(err)

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
        st.markdown("##### ✨ 실시간 번역 (한 → 베)")
        st.caption("입력 후 Enter → 자동 번역 · 같은 단어는 캐시되어 즉시 표시")
        
        ko_text = st.text_input(
            "번역할 한국어",
            placeholder="예: 이거 포장해주세요",
            key="trans_input",
            label_visibility="collapsed",
        )
        
        if ko_text and ko_text.strip():
            with st.spinner("번역 중..." if not st.session_state.get("_last_trans") == ko_text else ""):
                text, err = cached_translate_to_vi(ko_text.strip())
                st.session_state["_last_trans"] = ko_text
            if text:
                st.success(text)
            elif err:
                st.error(err)

    with sub_tab3:
        st.markdown("##### 📷 메뉴판·간판 사진 번역")
        st.caption("사진 → 실시간 줌으로 확인 → 번역")

        if not KEY_GEMINI:
            st.warning("⚠️ Gemini API 키가 필요합니다. Secrets에 등록해주세요.")
            return

        mode = st.radio(
            "입력 방식",
            ["📷 카메라로 촬영", "📁 갤러리에서 선택"],
            horizontal=True, key="cam_mode",
        )

        img_file = None
        if mode == "📷 카메라로 촬영":
            img_file = st.camera_input("📸 메뉴판이나 간판을 찍어주세요", key="cam_input")
        else:
            img_file = st.file_uploader(
                "이미지 파일 선택 (jpg/png)",
                type=["jpg", "jpeg", "png", "webp"], key="cam_upload",
            )

        if img_file is not None:
            try:
                img = Image.open(img_file)
                max_size = 1600
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.LANCZOS)

                col_img, col_opt = st.columns([2, 1])
                
                with col_img:
                    html_zoom_viewer(img, height=580)
                    
                with col_opt:
                    st.markdown("**번역 모드**")
                    translate_mode = st.radio(
                        "선택",
                        ["🍜 메뉴판", "🪧 간판/표지", "📄 일반 문서"],
                        key="trans_mode", label_visibility="collapsed",
                    )
                    do_translate = st.button(
                        "🔍 번역 시작", use_container_width=True, type="primary",
                    )
                    st.caption(f"📐 원본 {img.size[0]}×{img.size[1]}px")

                if do_translate:
                    if "메뉴판" in translate_mode:
                        prompt = """이 이미지는 베트남 음식점 메뉴판입니다. 다음 형식으로 정리해주세요:

📋 **메뉴 번역**

각 메뉴 항목별로:
- 🇻🇳 원문 (베트남어)
- 🇰🇷 한국어 번역
- 💵 가격 (있는 경우)
- 💡 음식 설명 (한 줄, 매운지/고수 들어가는지 등)

⚠️ **주의사항**: (아이가 먹기 어려운 메뉴, 알레르기 등)

✨ **추천**: 한국 가족(아이 3명 포함)에게 추천할 메뉴 2-3개"""
                    elif "간판" in translate_mode:
                        prompt = """이 이미지의 베트남어 간판/표지를 번역해주세요:

📝 **원문**:
🇰🇷 **번역**:
📍 **장소·용도**:
💡 **참고**:"""
                    else:
                        prompt = """이 이미지의 베트남어 텍스트를 한국어로 번역해주세요:

📝 **원문 (베트남어)**:
🇰🇷 **번역 (한국어)**:
💡 **추가 설명**:"""

                    with st.spinner("🔎 이미지 분석 중... (5~15초)"):
                        text, err = gemini_vision(prompt, img)
                        if text:
                            st.success(text)
                        else:
                            st.error(err)

            except Exception as e:
                st.error(f"이미지 처리 오류: {e}")

        with st.expander("💡 더 정확하게 번역받는 팁"):
            st.markdown("""
            - **밝은 곳에서 촬영** — 그림자 없이 정면에서
            - **글자가 화면에 꽉 차도록** — 너무 멀리서 찍으면 인식 안 됨
            - **흔들림 주의** — 두 손으로 잡고 천천히
            - **메뉴판은 한 면씩** — 양면을 한 번에 찍으면 정확도 ↓
            - **반사 주의** — 코팅된 메뉴판은 각도 살짝 틀어서
            """)

# ═══════════════════════════════════════════════════════════════
# 12. 화면: 가족 (인원 편집 포함)
# ═══════════════════════════════════════════════════════════════
def render_family():
    sub1, sub2, sub3, sub4 = st.tabs(["📍 위치 체크인", "👥 인원 관리", "📢 공지", "🕵️ 미션"])

    with sub1:
        st.markdown("##### 누가 어디에 있나요?")
        if not st.session_state.members:
            st.warning("먼저 '인원 관리' 탭에서 가족을 추가해주세요.")
        else:
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                who = st.selectbox("가족", st.session_state.members, key="loc_who")
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
                if m in st.session_state.members:
                    summary.setdefault(loc, []).append(m)
            for loc, members in summary.items():
                pills = " ".join([f"<span class='location-pill'>{m}</span>" for m in members])
                st.markdown(f"""
                <div class='card'>
                    <div class='card-title'>{loc} ({len(members)}명)</div>
                    {pills}
                </div>""", unsafe_allow_html=True)

    with sub2:
        st.markdown(f"##### 👥 여행 인원 관리 (현재 {len(st.session_state.members)}명)")
        
        c1, c2 = st.columns([4, 1])
        with c1:
            new_member = st.text_input("새 가족 추가", placeholder="예: 사촌 동생", key="new_mem", label_visibility="collapsed")
        with c2:
            if st.button("➕ 추가", use_container_width=True):
                if new_member and new_member not in st.session_state.members:
                    st.session_state.members.append(new_member)
                    st.session_state.locations[new_member] = "🏨 모벤픽"
                    st.rerun()
                elif new_member in st.session_state.members:
                    st.warning("이미 존재하는 이름입니다")
        
        st.markdown("---")
        st.caption("이름 클릭으로 수정, 🗑️ 버튼으로 삭제")
        
        for i, m in enumerate(st.session_state.members):
            c1, c2 = st.columns([5, 1])
            with c1:
                new_name = st.text_input(
                    f"member_{i}", m, 
                    key=f"mem_input_{i}", 
                    label_visibility="collapsed",
                )
                if new_name != m and new_name and new_name not in st.session_state.members:
                    if m in st.session_state.locations:
                        st.session_state.locations[new_name] = st.session_state.locations.pop(m)
                    st.session_state.members[i] = new_name
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"mem_del_{i}", use_container_width=True):
                    if m in st.session_state.locations:
                        del st.session_state.locations[m]
                    st.session_state.members.pop(i)
                    st.rerun()
        
        st.markdown("---")
        if st.button("🔄 기본값으로 복원", help="기본 10명으로 되돌립니다"):
            st.session_state.members = list(DEFAULT_MEMBERS)
            st.session_state.locations = {m: "🏨 모벤픽" for m in DEFAULT_MEMBERS}
            st.rerun()

    with sub3:
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
        for i, n in enumerate(st.session_state.notices):
            color = "#ff4b4b" if "긴급" in n["level"] else ("#ffd60a" if "일정" in n["level"] else "#9fd0ff")
            c1, c2 = st.columns([10, 1])
            with c1:
                st.markdown(f"""
                <div class='card' style='border-left:4px solid {color};'>
                    <b>{n['icon']} {n['level']}</b> · {n['text']}
                    <div style='font-size:0.8rem; color:#9fd0ff; margin-top:4px;'>{n['time']}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                if st.button("🗑️", key=f"noti_del_{i}"):
                    st.session_state.notices.pop(i)
                    st.rerun()

    with sub4:
        st.markdown("##### 아이들을 위한 오늘의 미션 🎯")
        if st.button("🎲 새 미션 뽑기", use_container_width=True):
            with st.spinner("미션 생성 중..."):
                p = """나트랑 가족여행 중 4학년·1학년 아이들이 함께할 미션 4개.
JSON 배열로만 응답: [{"emoji":"🍉","title":"미션이름","points":10}, ...]
다른 설명 없이 JSON만."""
                text, err = gemini_call(p)
                if text:
                    match = re.search(r"\[.*\]", text, re.DOTALL)
                    if match:
                        try:
                            st.session_state.missions = json.loads(match.group(0))
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("미션 형식 파싱 실패")
                else:
                    st.error(err)

        if st.session_state.missions:
            total_done = total_points = 0
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
# 13. 화면: 가계부
# ═══════════════════════════════════════════════════════════════
def render_budget():
    sub1, sub2 = st.tabs(["💰 공동 가계부", "💱 환율 계산기"])

    with sub1:
        with st.expander("⚙️ 예산 설정"):
            new_budget = st.number_input(
                "총 예산 (원)", min_value=0, 
                value=st.session_state.budget, step=100000,
            )
            if new_budget != st.session_state.budget:
                st.session_state.budget = new_budget
                st.rerun()
        
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
        c3.metric("남은 금액", f"{remain:,}원")
        if st.session_state.budget:
            st.progress(min(spent / st.session_state.budget, 1.0))

        st.markdown("##### 최근 지출")
        if not st.session_state.expenses:
            st.info("아직 등록된 지출이 없습니다.")
        for i, e in enumerate(reversed(st.session_state.expenses[-10:])):
            real_idx = len(st.session_state.expenses) - 1 - i
            c1, c2 = st.columns([10, 1])
            with c1:
                st.markdown(f"""
                <div class='card'>
                    <b>{e['cat']}</b> · {e['desc'] or '(내용 없음)'}
                    <span style='float:right; color:#ffd60a; font-weight:700;'>{e['amt']:,}원</span>
                    <div style='font-size:0.8rem; color:#9fd0ff;'>{e.get('time','')}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                if st.button("🗑️", key=f"exp_del_{real_idx}"):
                    st.session_state.expenses.pop(real_idx)
                    st.rerun()

    with sub2:
        st.markdown("##### 빠른 환율 계산")
        
        # 실시간 환율 가져오기
        rates = get_rates()
        if rates["live"]:
            st.caption(f"🟢 실시간 환율 · 1원 = {rates['vnd_per_krw']:.2f} VND / 1$ = {rates['krw_per_usd']:,.0f}원")
            if rates["updated"]:
                st.caption(f"📅 최종 업데이트: {rates['updated']}")
        else:
            st.caption("🟡 환율 API 응답 없음 → 기본값 사용 (1원=18.5동, 1$=1,370원)")
        
        if st.button("🔄 환율 새로고침", help="캐시를 지우고 최신 환율 다시 받기"):
            fetch_exchange_rates.clear()
            st.rerun()
        
        t1, t2, t3 = st.tabs(["원 → 동", "동 → 원", "달러 → 원"])
        with t1:
            krw = st.number_input("원화 (KRW)", min_value=0, value=50000, step=10000, key="krw1")
            if krw > 0:
                vnd = krw * rates["vnd_per_krw"]
                usd = krw * rates["usd_per_krw"]
                st.markdown(f"""
                <div class='card'>
                    🇻🇳 약 <b style='color:#ffd60a; font-size:1.3rem;'>{vnd:,.0f} VND</b><br>
                    🇺🇸 약 <b style='color:#ffd60a; font-size:1.1rem;'>${usd:,.2f} USD</b>
                </div>""", unsafe_allow_html=True)

        with t2:
            vnd = st.number_input("베트남동 (VND)", min_value=0, value=100000, step=50000, key="vnd1")
            if vnd > 0:
                krw_result = vnd / rates["vnd_per_krw"]
                st.markdown(f"""
                <div class='card'>
                    🇰🇷 약 <b style='color:#ffd60a; font-size:1.3rem;'>{krw_result:,.0f}원</b>
                </div>""", unsafe_allow_html=True)
                st.info("💡 꿀팁: VND에서 0 하나 빼고 ÷2 (10만동 ≈ 5천원)")

        with t3:
            usd = st.number_input("미국달러 (USD)", min_value=0.0, value=10.0, step=10.0, key="usd1")
            if usd > 0:
                krw_result = usd * rates["krw_per_usd"]
                vnd_result = usd * rates["vnd_per_usd"]
                st.markdown(f"""
                <div class='card'>
                    🇰🇷 약 <b style='color:#ffd60a; font-size:1.3rem;'>{krw_result:,.0f}원</b><br>
                    🇻🇳 약 <b style='color:#ffd60a; font-size:1.1rem;'>{vnd_result:,.0f} VND</b>
                </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 14. 화면: 준비 (편집 가능 짐 + 비상)
# ═══════════════════════════════════════════════════════════════
def render_prep():
    sub1, sub2 = st.tabs(["🎒 짐 체크리스트", "🚨 비상 연락처"])

    with sub1:
        st.markdown("##### 5박 6일 짐 챙기기")
        edit_mode = st.toggle("✏️ 편집 모드", key="pack_edit", help="항목/카테고리 추가·삭제·수정")
        
        all_done = []
        for cat in list(st.session_state.packing.keys()):
            items = st.session_state.packing[cat]
            with st.expander(f"**{cat}** ({len(items)}개)", expanded=True):
                if edit_mode:
                    for i, item in enumerate(items):
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            new_item = st.text_input(
                                f"item_{cat}_{i}", item,
                                key=f"pack_item_{cat}_{i}",
                                label_visibility="collapsed",
                            )
                            if new_item != item and new_item:
                                st.session_state.packing[cat][i] = new_item
                        with c2:
                            if st.button("🗑️", key=f"pack_del_{cat}_{i}", use_container_width=True):
                                st.session_state.packing[cat].pop(i)
                                st.rerun()
                    
                    nc1, nc2 = st.columns([5, 1])
                    with nc1:
                        new_pack = st.text_input(
                            "새 항목", key=f"pack_add_{cat}",
                            placeholder="추가할 짐", label_visibility="collapsed",
                        )
                    with nc2:
                        if st.button("➕", key=f"pack_add_btn_{cat}", use_container_width=True):
                            if new_pack:
                                st.session_state.packing[cat].append(new_pack)
                                st.rerun()
                else:
                    for i, item in enumerate(items):
                        key = f"chk_{cat}_{i}"
                        checked = st.checkbox(item, key=key)
                        all_done.append(checked)
        
        if edit_mode:
            st.markdown("---")
            st.markdown("##### 📂 카테고리 관리")
            cc1, cc2 = st.columns([5, 1])
            with cc1:
                new_cat = st.text_input("새 카테고리", placeholder="예: 🧳 의류", label_visibility="collapsed", key="new_cat_input")
            with cc2:
                if st.button("➕ 추가", use_container_width=True, key="cat_add"):
                    if new_cat and new_cat not in st.session_state.packing:
                        st.session_state.packing[new_cat] = []
                        st.rerun()
            
            if len(st.session_state.packing) > 0:
                del_cat = st.selectbox("삭제할 카테고리", [""] + list(st.session_state.packing.keys()), key="cat_del_sel")
                if del_cat and st.button("⚠️ 카테고리 통째로 삭제", key="cat_del_btn"):
                    del st.session_state.packing[del_cat]
                    st.rerun()
            
            st.markdown("---")
            if st.button("🔄 짐 목록 기본값 복원"):
                st.session_state.packing = json.loads(json.dumps(DEFAULT_PACKING))
                st.rerun()
        else:
            done = sum(all_done)
            total = len(all_done)
            st.markdown("---")
            if total:
                st.progress(done / total)
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
                <li>여행자보험 회사 연락 (영수증·진단서 보관)</li>
                <li>여권 분실시 → 대사관 → 임시여권 발급</li>
            </ol>
        </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 15. 메인
# ═══════════════════════════════════════════════════════════════
def main():
    st.markdown('<p class="main-title">🌴 나트랑 패밀리 베이스캠프</p>', unsafe_allow_html=True)
    st.markdown(
        f"<p class='subtitle'>2026.05.10 (일) ~ 05.15 (금) · 모벤픽 리조트 깜란 · 가족 {len(st.session_state.members)}명</p>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["🏠 홈", "📅 일정", "🗺️ 지도", "🤖 AI비서", "👨‍👩‍👧‍👦 가족", "💰 가계부", "🎒 준비"])

    with tabs[0]: render_home()
    with tabs[1]: render_itinerary()
    with tabs[2]: render_map()
    with tabs[3]: render_ai()
    with tabs[4]: render_family()
    with tabs[5]: render_budget()
    with tabs[6]: render_prep()


if __name__ == "__main__":
    main()
