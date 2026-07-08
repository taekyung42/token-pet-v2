"""Maps live telemetry (speed, 5-hour usage %, time to reset) to a "mood":
a message pool plus a visual treatment (tint/overlay/shake). Having the
mood depend on all three signals -- not just speed -- means the pet reads
differently at "10% used, sprinting" vs "90% used, sprinting" even though
the running animation itself is identical.
"""

from collections import namedtuple

Mood = namedtuple("Mood", ["key", "tint", "overlay", "shake", "messages"])


def _m(key, messages, tint=None, overlay=None, shake=False):
    return Mood(key, tint, overlay, shake, messages)


def _speed_bucket(intensity):
    if intensity < 0.05:
        return "rest"
    if intensity < 0.35:
        return "light"
    if intensity < 0.65:
        return "moderate"
    return "heavy"


def _usage_bucket(pct):
    if pct < 50:
        return "safe"
    if pct < 80:
        return "warm"
    if pct < 100:
        return "hot"
    return "critical"


# (usage_bucket, speed_bucket) -> Mood. 4x4 grid so "a little used + idle"
# reads nothing like "almost out of budget + sprinting".
MOOD_TABLE = {
    ("safe", "rest"): _m(
        "dozing",
        messages=["쿨쿨...", "느긋하게 쉬는 중", "여유만만~", "낮잠 타임"],
    ),
    ("safe", "light"): _m(
        "calm",
        messages=["가볍게 산책 중", "천천히 걷는 중", "널널하다~", "콧노래 부르며 걷기"],
    ),
    ("safe", "moderate"): _m(
        "playful",
        messages=["신나게 뛰는 중!", "이 정도는 껌이지", "재밌다 재밌어", "꼬리 살랑살랑"],
    ),
    ("safe", "heavy"): _m(
        "excited", overlay="sparkle_trail",
        messages=["전속력 질주!!", "바람처럼 빠르다", "으쌰으쌰!", "신남 폭발!"],
    ),
    ("warm", "rest"): _m(
        "resting",
        messages=["숨 고르는 중", "잠깐 쉬어갈게", "물 한 모금...", "슬슬 페이스 조절"],
    ),
    ("warm", "light"): _m(
        "steady",
        messages=["꾸준히 가는 중", "페이스 유지!", "무리 없이 딱 좋아", "차분하게 계속"],
    ),
    ("warm", "moderate"): _m(
        "working", overlay="sweat",
        messages=["열심히 뛰는 중", "슬슬 더워지네", "페이스 올라간다", "좋아 좋아 이 흐름"],
    ),
    ("warm", "heavy"): _m(
        "sweating", tint="amber", overlay="sweat",
        messages=["땀 좀 나는데?", "속도 진짜 빠르다", "이러다 지치겠어", "전력질주 중!"],
    ),
    ("hot", "rest"): _m(
        "wary", tint="amber",
        messages=["슬슬 조심해야겠어", "한도가 얼마 안 남았어", "잠깐, 생각 좀 하자", "눈치 보는 중"],
    ),
    ("hot", "light"): _m(
        "cautious", tint="amber",
        messages=["조심조심 가는 중", "속도 좀 줄일까...", "얼마 안 남았는데", "살살 갈게"],
    ),
    ("hot", "moderate"): _m(
        "stressed", tint="amber", overlay="sweat",
        messages=["이거 좀 빡빡한데", "한도 걱정되기 시작", "헉헉, 페이스가...", "슬슬 힘들어지네"],
    ),
    ("hot", "heavy"): _m(
        "panicked", tint="amber", overlay="sweat_exclaim",
        messages=["헥헥! 거의 다 왔어!", "한도 코앞이야!!", "숨차 숨차!!", "잠깐만!! 너무 빨라!!"],
    ),
    ("critical", "rest"): _m(
        "worn_out", tint="red",
        messages=["완전 지쳤어...", "더는 못 뛰겠어 ㅠㅠ", "한도 거의 다 썼어...", "잠깐만 쉬자..."],
    ),
    ("critical", "light"): _m(
        "anxious", tint="red",
        messages=["이제 진짜 얼마 안 남았어", "조마조마해...", "살얼음판 걷는 기분", "조심 또 조심"],
    ),
    ("critical", "moderate"): _m(
        "desperate", tint="red", overlay="sweat",
        messages=["한계 돌파 직전!!", "더는 무리일지도...", "헥헥... 힘들어...", "거의 한도 끝판왕"],
    ),
    ("critical", "heavy"): _m(
        "redline", tint="red", overlay="sweat_exclaim", shake=True,
        messages=["레드라인이야!!!", "한도 초과 직전!!!", "으아아 못참겠어!!!", "이러다 쓰러지겠어!!"],
    ),
}

NO_SESSION_MESSAGES = ["쿨쿨... 대기 중", "아무 일도 없네", "심심하다~", "부를 때까지 낮잠"]
RESET_SOON_MESSAGES = ["⏰ 곧 리셋될 것 같아!", "조금만 더 버티면 리셋!", "리셋이 코앞이야!"]
CELEBRATE_MESSAGES = ["다시 태어났다!! \U0001f389", "리셋 완료! 새 힘 충전!", "가뿐하다~ 다시 달리자!"]
CLICK_MESSAGES = ["헤헤 좋아!", "왜 불렀어?", "간식...?", "쓰다듬어줘서 좋아!", "멍멍!"]

TINT_COLORS = {
    "amber": (255, 193, 7, 70),
    "red": (220, 30, 30, 115),
}


def get_mood(usage_pct, speed_intensity, active):
    if not active:
        return None
    bucket = (_usage_bucket(usage_pct), _speed_bucket(speed_intensity))
    return MOOD_TABLE[bucket]
