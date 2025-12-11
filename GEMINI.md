# Project Name: Online Yacht Dice Master (Yacht-Web)

## 1. Project Overview
이 프로젝트는 사용자가 웹에서 주사위 게임인 **Yacht(야추)**를 플레이할 수 있는 멀티플레이어 웹 애플리케이션입니다.
Django를 기반으로 하며, 실시간 대전(PvP)과 AI 대전(PvE)을 모두 지원합니다.

### 1.1 Core Gameplay Rules
* **게임 방식:** 표준 Yacht 룰을 따름 (5개의 주사위, 총 12~13라운드).
* **매치 시스템:** **3판 2선승제 (Best of 3)**.
    * 한 번의 매칭에서 최대 3번의 게임(Game)을 진행.
    * 먼저 2승을 거둔 플레이어가 최종 승리(Match Win).
* **승리 조건:** 최종 점수가 높은 쪽이 승리.

---

## 2. Tech Stack & Environment

### 2.1 Backend
* **Language:** Python 3.11+
* **Framework:** Django 5.x
* **Real-time Communication:** **Django Channels** (WebSocket) & Daphne (ASGI Server).
* **Database:**
    * Dev: SQLite
    * Prod: PostgreSQL (GCP Cloud SQL 예정)
* **Cache/Channel Layer:** Redis (Docker로 구동, 실시간 룸 상태 관리).

### 2.2 Frontend
* **Structure:** HTML5, Django Templates (DTL).
* **Styling:** CSS3, Bootstrap 5 (Layout), Custom CSS.
* **Animation Library:**
    * **Anime.js** (추천): 주사위 굴리기, 점수판 갱신 등 부드러운 2D 애니메이션 구현.
    * *Alternative:* Three.js (3D 주사위가 필요할 경우 사용, 현재는 2D 우선).
* **Language:** Vanilla JavaScript (ES6+).

### 2.2 Frontend (Design Guidelines)
* **Theme:** "Dark Luxury" (Inspired by high-end yacht sales pages).
* **Color Palette:**
    * Background: `#1A1A1A` (Dark Charcoal).
    * Accents: Soft Gradients (Blue-Cyan, Peach-Orange) for interactions.
* **UI Components:**
    * Glassmorphism cards (semi-transparent backgrounds with blur).
    * Minimalist typography (Montserrat/Inter).
    * Clean, bar-style indicators for scores and timers (referencing the 'Manhattan 96' spec bars).

### 2.3 AI & External API
* **AI Model:** **Google Gemini Pro** (via Google AI Studio API).
* **Role:** PvE 모드에서 상대방 플레이어 역할 수행 (주사위 선택 및 점수판 기입 결정).
* **Library:** `google-generativeai` Python SDK.

### 2.4 Auth & User System
* **Library:** `django-allauth`.
* **Google Login:** OAuth2 연동.
* **Anonymous User:** 세션 기반의 'Guest' 닉네임 생성 및 임시 플레이 허용.

### 2.5 Deployment (Future Plan)
* **Platform:** Google Cloud Platform (GCP).
* **Service:** Google Cloud Run (Containerized).
* **Static Files:** WhiteNoise or GCS buckets.

---

## 3. Functional Requirements

### 3.1 Lobby & Matchmaking
1.  **Random Match (PvP):**
    * '랜덤 매칭' 버튼 클릭 시 Redis 대기열(Queue)에 등록.
    * 비슷한 시점의 대기 유저와 매칭 -> 고유 `Room Group` 생성.
2.  **Private Room (PvP):**
    * 방 생성 시 6자리 초대 코드 생성.
    * 친구는 코드를 입력하여 입장.
3.  **AI Match (PvE):**
    * 대기 시간 없이 즉시 게임 시작.
    * Gemini API가 상대방 턴을 계산하여 응답.

### 3.2 Game Interface (In-Game)
* **Dice Section:**
    * 5개의 주사위 UI.
    * 'Roll' 버튼 (턴당 최대 3회).
    * 주사위 클릭 시 'Keep(고정)'/'Unkeep' 토글 애니메이션.
* **Scoreboard:**
    * 나의 점수 vs 상대방 점수.
    * 현재 턴에서 기록 가능한 점수 미리보기(Preview).
    * 족보(Ones ~ Yacht) 클릭 시 점수 확정 및 턴 넘김.
* **Match Status:**
    * 현재 몇 번째 판인지 표시 (예: Game 2/3).
    * 현재 스코어 (예: Player 1승 - AI 0승).

### 3.3 AI Logic (Gemini Integration)
* **Prompt Engineering:**
    * Input: 현재 주사위 상태(예: `[1, 1, 4, 5, 6]`), 남은 리롤 횟수, 현재 점수판 상황.
    * Output: JSON 형식.
        * `action`: "roll" or "select_score"
        * `keep_indices`: 리롤 시 유지할 주사위 인덱스 (예: `[0, 1]`)
        * `score_category`: 점수 기록 시 선택할 족보 (예: "fours")

---

## 4. Database Schema (Conceptual)

### User (Custom Model)
* `id`, `username`, `email`
* `is_guest` (Boolean)
* `total_wins`, `total_losses`, `rating` (ELO)

### Match
* `id` (UUID)
* `player1` (FK), `player2` (FK, Nullable for AI)
* `player1_wins` (int), `player2_wins` (int)
* `status` (WAITING, IN_PROGRESS, FINISHED)
* `winner` (FK)
* `created_at`

### GameSession
* `id`
* `match` (FK)
* `round_number` (1, 2, 3)
* `game_log` (JSONField: 전체 턴 기록 저장)
* `result` (P1_WIN, P2_WIN)

---

## 5. Implementation Roadmap

1.  **Phase 1: Setup & Logic**
    * Django 프로젝트 설정 (`settings.py`, `django-allauth`).
    * 순수 Python으로 `YachtGameEngine` 클래스 구현 (룰 검증 로직).
    * Gemini API 연동 테스트.
2.  **Phase 2: WebSocket & Multiplayer**
    * Redis 및 Django Channels 설정.
    * `consumers.py` 작성 (접속, 주사위 굴림, 턴 교환 브로드캐스팅).
    * 로비 및 매칭 대기열 구현.
3.  **Phase 3: Frontend & Animation**
    * Anime.js를 활용한 주사위 3D 회전 효과(혹은 2D 스프라이트 애니메이션).
    * 점수판 UI 반응형 디자인.
4.  **Phase 4: Match System & Polish**
    * 3판 2선승제 로직 연결.
    * 최종 승리 모달 및 재대결 기능.
5.  **Phase 5: GCP Deployment**
    * `Dockerfile` 작성.
    * Cloud Run 배포 및 도메인 연결.

---

## 6. Guidelines for AI Assistant
* 모든 코드는 Python 3.11 및 Django 5.x 문법을 준수하십시오.
* 비동기 코드(`async/await`)는 `consumers.py`와 같은 ASGI 컨텍스트에서만 사용하십시오.
* 프론트엔드 코드 생성 시, 복잡한 로직보다는 가독성과 Anime.js와의 호환성을 우선하십시오.
* GCP 배포를 염두에 두고 환경 변수(`.env`) 관리를 철저히 하십시오.

