# 세종시 문화유산 서비스 (Sejong City Cultural Heritage Service)

세종시의 문헌 및 문화유산 정보를 수집·분석하고, AI 기반 추천 및 코스 생성 기능을 제공하는 클라우드 네이티브 웹/앱 서비스입니다. 사용자는 문화유산을 검색하고 관심 장소를 조합해 나만의 여행 코스를 만들 수 있으며, 시민 참여형 제보 기능을 통해 새로운 문화유산 후보를 제보·추천하고 관리자가 승인 시 마스터 DB에 즉시 공개되는 선순환 구조를 가집니다.

---

## 1. 기술 스택 요약 (Tech Stack)

| 영역 | 기술 스택 | 상세 역할 |
| :--- | :--- | :--- |
| **백엔드** | Python, FastAPI, Google Cloud Run | REST API 서버 구축 및 서버리스 클라우드 배포 환경 |
| **LLM/AI** | Gemini, LangChain, LangGraph | 오케스트레이션 및 5단계 상태 그래프 기반 AI 워크플로우 구성 |
| **벡터 DB / RAG** | Supabase (pgvector) | RAG(검색 증강 생성) 구축 및 의미론적 벡터 검색 지원 |
| **그래프 DB** | Neo4j | 문화유산 장소 간 근접성, 테마, 역사 시대 관계의 지식 그래프 구축 |
| **프론트엔드** | React, Google Apps Script & Sites | 맞춤형 추천 UI, 시각화 대시보드 및 신속한 제보 승인 관리 포털 |
| **지도** | Google Maps API | 위치 기반 문화유산 매핑 및 경로 시각화 |
| **협업/저장소** | Google Drive, Google Workspace, GitHub | 협업 공간 연동 및 형상 관리 |

---

## 2. 시스템 아키텍처 (System Architecture)

시스템은 4개 계층(4-Layer Architecture)으로 구성되어 있습니다:

```
[ FRONTEND ] ──── (React Web App / Google Apps Script Dashboard)
      │ (REST API / JSON)
      ▼
[ AI & ENGINE ] ── (FastAPI Server on Cloud Run / LangGraph Workflow)
      │ (Local DB Helper / SQL & Cypher queries)
      ▼
[ STORAGE ] ───── (Supabase PostgreSQL pgvector / Neo4j Graph Database)
      ▲
      │ (Data Sync)
[ EXTERNAL ] ──── (한국관광데이터랩 API / 국문 관광정보 서비스 Open API)
```

---

## 3. 디렉토리 구조 및 핵심 파일 안내

- **`storage/`**: 데이터 스토리지 모델 및 가상화 파일
  - [supabase/schema.sql](file:///c:/Users/user/Documents/ict_project/storage/supabase/schema.sql): PostgreSQL 관계형 스키마 및 제보 처리 트리거 정의.
  - [neo4j/schema.cypher](file:///c:/Users/user/Documents/ict_project/storage/neo4j/schema.cypher): 그래프 네트워크 모델링 및 Cypher 쿼리 제약 조건 정의.
  - [mock_db.json](file:///c:/Users/user/Documents/ict_project/storage/mock_db.json): 세종시 실측 문화유산 및 경로 가중치가 담긴 고품질 로컬 데이터셋.
  - [db_helper.py](file:///c:/Users/user/Documents/ict_project/storage/db_helper.py): mock_db를 활용한 로컬 SQL/Graph 시뮬레이션 쿼리 래퍼.
  - [README.md](file:///c:/Users/user/Documents/ict_project/storage/README.md): 스토리지 스키마 상세 설명서.
- **`backend/`**: AI 추천 엔진 및 FastAPI 애플리케이션
  - [backend/app/main.py](file:///c:/Users/user/Documents/ict_project/backend/backend/app/main.py): REST API 엔드포인트 및 Pydantic 유효성 검사.
  - [backend/app/services/langgraph_agent.py](file:///c:/Users/user/Documents/ict_project/backend/backend/app/services/langgraph_agent.py): Query Analysis ➔ Vector Search ➔ Graph Lookup ➔ Generate Recommendations ➔ Format Response 로 연결되는 LangGraph 워크플로우 엔진.
  - [Dockerfile](file:///c:/Users/user/Documents/ict_project/backend/Dockerfile): Google Cloud Run 배포용 Docker 설정.
- **`gas/`**: 관리자 포털 및 신속 배포용 Google Apps Script
  - [Code.gs](file:///c:/Users/user/Documents/ict_project/gas/Code.gs): 백엔드 API 연동용 GAS 스크립트.
  - [Index.html](file:///c:/Users/user/Documents/ict_project/gas/Index.html): 글래스모피즘 어두운 테마 기반의 시민 제보 심사 관리 대시보드 UI.

---

## 4. 로컬 테스트 및 실행 방법

### 4.1 백엔드 요구사항 설치 및 실행
```bash
# 의존성 패키지 설치
cd backend
pip install -r requirements.txt

# FastAPI 개발 서버 실행 (8080 포트)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
```

### 4.2 GAS 어플리케이션 연동 방법
1. [Index.html](file:///c:/Users/user/Documents/ict_project/gas/Index.html)과 [Code.gs](file:///c:/Users/user/Documents/ict_project/gas/Code.gs)를 Google Apps Script 프로젝트에 붙여넣습니다.
2. `Code.gs` 내 `API_BASE_URL` 변수를 실행 중인 로컬 uvicorn 주소 혹은 배포 완료된 Cloud Run URL로 교체합니다.
3. 웹 앱(Web App)으로 배포한 후 관리자용 화면으로 접속하여 실시간 제보 승인/반려 기능을 테스트합니다.

---

## 5. 개발 우선순위 및 구현 현황 (Roadmap Status)

프로젝트 기획에 맞춰 개발 단계별 구현이 완료되었으며, 현재 상태는 다음과 같습니다:

- **[x] 1단계 (데이터 기반 구축)**: `heritage` 테이블 119건 엑셀 시딩 완료, 119건 원본 이미지 매핑/저장 및 검증 검사 완료, FastAPI 기본 CRUD 설계 완료, Supabase 벡터 스키마 구조 구축 완료.
- **[x] 2단계 (핵심 조회 기능)**: 홈화면, 검색, 상세 조회 API 구현 완료, 소개 필드 기반 실시간 '생각할 거리' 생성을 위한 LLM 프롬프트 템플릿( prompts/thinking_prompt.txt ) 작성 완료.
- **[x] 3단계 (코스 생성)**: 지도 연동용 지오 좌표계 시뮬레이션, Neo4j 관계형 지식 그래프 스키마( schema.cypher ) 설계 완료, 나만의 코스 데이터 및 교통수단/소요 시간 API 연동 완료 (세종 버스 API 연동).
- **[x] 4단계 (시민 참여)**: 시민 추천 등록(candidates), 투표(likes/votes), 후기(reviews), 사용자별 추천 상태 추적 API 구현 완료. GAS 기반의 관리자 제보 실시간 승인/반려 대시보드 프론트엔드 연동 완료.
- **[/] 5단계 (고도화)**: LangGraph 기반의 AI 대화형 검색 및 추천 체인 연동 완료. 동화/잡지 형식 콘텐츠 생성 필드 모델링 완료.

