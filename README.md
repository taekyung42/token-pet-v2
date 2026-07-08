# 🐕 Token Pet v2

Claude Code의 토큰 사용량을 실시간으로 보여주는 데스크톱 펫입니다. 화면 위를 돌아다니는 귀여운 강아지가 지금 얼마나 빠르게 토큰을 쓰고 있는지, 5시간 사용 블록이 얼마나 남았는지에 따라 표정과 기분을 바꿉니다.

## ✨ 주요 기능

- **실시간 토큰 속도** — Claude Code의 로컬 세션 로그(`~/.claude/projects/**/*.jsonl`)를 실시간으로 읽어 초당 토큰 처리량을 계산합니다.
- **5시간 사용 블록 추적** — Anthropic의 rate-limit 창을 본떠 5시간 롤링 블록의 사용량과 남은 시간을 표시합니다.
- **감정 표현** — 속도 · 사용률 · 리셋까지 남은 시간 세 가지 신호를 조합해 펫의 기분(여유·집중·긴장·레드라인 등 16단계)을 결정하고, 대사와 색조·이펙트(땀·반짝임·흔들림)로 표현합니다.
- **자가 보정 예산** — 실제 사용량 API가 닿으면 토큰 예산 추정치를 스스로 위/아래로 보정합니다.
- **Windows 자동 시작** — 부팅 시 자동 실행되도록 등록/해제하는 스크립트를 제공합니다.

## 📦 요구 사항

- Python 3.9+
- [PySide6](https://pypi.org/project/PySide6/) (Qt for Python)
- Claude Code (로컬 세션 로그를 사용)

## 🚀 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py
```

## 🖥️ Windows 자동 시작

빌드된 `token-pet-v2.exe`와 같은 폴더에서 아래 스크립트를 실행하세요.

- `install-autostart.bat` / `install-autostart.ps1` — 부팅 시 자동 시작 등록
- `uninstall-autostart.bat` / `uninstall-autostart.ps1` — 자동 시작 해제

## 🔧 동작 방식

| 파일 | 역할 |
| --- | --- |
| `main.py` | 앱 진입점 — 위젯과 모니터를 연결하고 실행 |
| `log_monitor.py` | 세션 로그를 tail 하며 토큰 속도 · 5시간 블록 통계 산출 |
| `real_usage_monitor.py` | 실제 사용량 API를 폴링해 예산 보정에 활용 |
| `pet_widget.py` | 화면 위 펫 위젯 렌더링 및 상호작용 |
| `expressions.py` | 텔레메트리 → 기분(대사·색조·이펙트) 매핑 |
| `config.py` | 설정 저장/로드 (`~/.token-pet-v2/config.json`) |

## ⚙️ 설정

설정은 `~/.token-pet-v2/config.json`에 저장됩니다.

- `block_budget_tokens` — 5시간 블록의 (가중치 적용) 토큰 예산 추정치
- `window_x`, `window_y` — 펫 위젯의 마지막 위치

## 📝 참고

Anthropic이 공식 쿼터 API를 제공하지 않으므로, 토큰 예산은 사용자 설정값을 기반으로 한 **추정치**이며 캐시 읽기/생성에 가중치를 적용해 실제 비용에 가깝게 계산합니다.
