import os
import sys
from fastapi import FastAPI, HTTPException, status, Header, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List

# Append the project root to import DB helper and LangGraph agent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from storage.db_helper import SejongDBHelper
from backend.backend.app.services.langgraph_agent import run_agent

# Open API integrations
from fastapi import Query
from backend.backend.app.integrations.sejong_bus import get_transit_duration
from backend.backend.app.integrations.tourapi_service import get_nearby_attractions
from backend.backend.app.integrations.cultural_heritage_sync import sync_heritage_designations

# Initialize DB Helper
db = SejongDBHelper()

# Initialize FastAPI application
app = FastAPI(
    title="Sejong City Cultural Heritage Service API",
    description="FastAPI Backend for Sejong Cultural Heritage with LangGraph Recommendation workflows.",
    version="1.1.0"
)

@app.on_event("startup")
def startup_event():
    # Load settings from db and populate os.environ
    try:
        settings = db.get_settings()
        for k, v in settings.items():
            if v:
                os.environ[k] = v
                print(f"[Startup] Loaded environmental key: {k}")
    except Exception as e:
        print(f"[Startup] Failed to load settings from DB: {e}")

# Enable CORS for frontend and GAS environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files (to serve cultural heritage images)
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ==========================================
# Dependencies & Security
# ==========================================

def get_current_admin(authorization: Optional[str] = Header(None)) -> str:
    """Enforces bearer token authorization checking for Admin RBAC role."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 헤더가 누락되었거나 Bearer 형식이 아닙니다."
        )
    token = authorization.split(" ")[1]
    # For testing, we validate token is 'admin-super-token'
    if token != "admin-super-token":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 리소스에 접근 권한이 없습니다. (관리자 권한 필요)"
        )
    return "admin_user_01"

# ==========================================
# Pydantic Schemas
# ==========================================

class RecommendRequest(BaseModel):
    query: str = Field(..., description="유저 추천 혹은 코스 생성 질문 쿼리", example="비암사 근처 조선시대 역사 코스 추천해줘")

# Citizen recommendation candidate
class CandidateSubmitRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200, example="조치원 정수장 문화정원")
    image_urls: List[str] = Field(..., min_items=1, example=["/static/images/candidates/c1_1.jpg"])
    latitude: Optional[float] = Field(None, example=36.6025)
    longitude: Optional[float] = Field(None, example=127.2981)
    description: str = Field(..., min_length=5, example="옛 정수시설을 조경 정원과 전시실로 탈바꿈한 근대 건축 재생 명소입니다.")
    reporter_id: str = Field(..., example="user_demo_1")

class CandidateReviewRequest(BaseModel):
    candidate_id: int = Field(..., example=1)
    status: str = Field(..., pattern="^(APPROVED|REJECTED)$", description="APPROVED 혹은 REJECTED", example="APPROVED")
    admin_comment: Optional[str] = Field(None, example="근대 재생 공간 가치를 인정함.")

# Review
class ReviewSubmitRequest(BaseModel):
    user_id: str = Field(..., example="user_demo_2")
    image_url: Optional[str] = Field(None, example="/static/images/reviews/r1.jpg")
    content: str = Field(..., min_length=2, example="비암사 경치가 아주 고즈넉하고 힐링됩니다.")

# Course
class CourseCreateRequest(BaseModel):
    user_id: str = Field(..., example="user_demo_1")
    name: str = Field(..., example="전의면 힐링도보 코스")
    heritage_ids: List[str] = Field(..., min_items=1, example=["H1", "H2"])
    transit_type: str = Field(..., example="보행", description="보행, 차량, 자전거 등")
    duration_mins: int = Field(..., example=90, description="소요 시간(분)")
    generated_content: Optional[str] = Field(None, example="동화 형식 스토리텔링 콘텐츠")

# Settings & System config
class SettingsResponse(BaseModel):
    GOOGLE_API_KEY: str
    TOURAPI_KEY: str
    SEJONG_BUS_API_KEY: str
    CULTURAL_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str

class SettingsUpdateRequest(BaseModel):
    GOOGLE_API_KEY: Optional[str] = None
    TOURAPI_KEY: Optional[str] = None
    SEJONG_BUS_API_KEY: Optional[str] = None
    CULTURAL_API_KEY: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    NEO4J_URI: Optional[str] = None
    NEO4J_USERNAME: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None


class ReportReviewRequest(BaseModel):
    report_id: int = Field(..., example=1)
    status: str = Field(..., pattern="^(APPROVED|REJECTED)$", description="APPROVED 혹은 REJECTED", example="APPROVED")
    admin_comment: Optional[str] = Field(None, example="적합한 근대 역사 조형미로 판정함.")

# ==========================================
# REST API Routes (/api/v1/)
# ==========================================

@app.get("/")
def read_root():
    return {
        "service": "Sejong City Cultural Heritage Service API",
        "docs_url": "/docs",
        "api_v1_prefix": "/api/v1"
    }

# 1. Master Heritages
@app.get("/api/v1/heritages")
def get_heritages(
    query: Optional[str] = None, 
    category: Optional[str] = None,
    dong: Optional[str] = None,
    era: Optional[str] = None
):
    """
    Search and filter Sejong City cultural heritages (supports query, category, dong, era filters).
    """
    results = db.search_heritage(query=query, category=category, dong=dong, era=era)
    return {
        "status": "success",
        "count": len(results),
        "data": results
    }

@app.get("/api/v1/heritages/{heritage_id}")
def get_heritage_detail(heritage_id: str):
    """
    Get detailed information for a single cultural heritage site using its H_ID.
    """
    heritage = db.get_heritage_by_id(heritage_id)
    if not heritage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Heritage ID {heritage_id} not found."
        )
    return {
        "status": "success",
        "data": heritage
    }

# 2. Recommendations & Course Generation
@app.post("/api/v1/recommend")
def recommend_heritage_and_course(req: RecommendRequest):
    """
    Generate recommendations or travel courses using the LangGraph AI workflow agent.
    """
    try:
        response = run_agent(req.query)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph execution error: {str(e)}"
        )

# 3. Citizen Candidates (시민 추천 제보)
@app.post("/api/v1/candidates")
def submit_citizen_candidate(req: CandidateSubmitRequest):
    """
    Submit a citizen proposed heritage candidate.
    """
    try:
        candidate = db.submit_citizen_candidate(
            name=req.name,
            image_urls=req.image_urls,
            latitude=req.latitude,
            longitude=req.longitude,
            description=req.description,
            reporter_id=req.reporter_id
        )
        return {
            "status": "success",
            "message": "Candidate submitted successfully.",
            "data": candidate
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get("/api/v1/candidates")
def list_citizen_candidates(status: Optional[str] = None):
    """
    List citizen proposed candidates, optionally filtered by status (PENDING, APPROVED, REJECTED).
    """
    candidates = db.get_citizen_candidates(status=status)
    return {
        "status": "success",
        "count": len(candidates),
        "data": candidates
    }

@app.post("/api/v1/candidates/{candidate_id}/vote")
def vote_candidate(candidate_id: int, user_id: str):
    """
    Vote/Like a citizen-proposed candidate heritage.
    """
    candidate = db.vote_citizen_candidate(candidate_id=candidate_id, user_id=user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Candidate ID {candidate_id} not found."
        )
    return {
        "status": "success",
        "votes": candidate["votes"],
        "data": candidate
    }

@app.post("/api/v1/candidates/review")
def review_citizen_candidate(req: CandidateReviewRequest, admin_id: str = Depends(get_current_admin)):
    """
    Review (approve/reject) a citizen candidate. APPROVED ones get published to heritage master table.
    Requires Admin Authorization Bearer Token. Logs audit event.
    """
    candidate = db.review_citizen_candidate(
        candidate_id=req.candidate_id,
        status=req.status,
        admin_comment=req.admin_comment,
        admin_id=admin_id
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Candidate ID {req.candidate_id} not found."
        )
    return {
        "status": "success",
        "message": f"Candidate ID {req.candidate_id} reviewed successfully. Status: {req.status}",
        "data": candidate
    }

# 4. Heritage Reviews (문화유산 후기)
@app.post("/api/v1/heritages/{heritage_id}/reviews")
def submit_review(heritage_id: str, req: ReviewSubmitRequest):
    """
    Submit a user review/rating for a specific cultural heritage site.
    """
    try:
        review = db.submit_heritage_review(
            heritage_id=heritage_id,
            user_id=req.user_id,
            image_url=req.image_url,
            content=req.content
        )
        return {
            "status": "success",
            "data": review
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/v1/heritages/{heritage_id}/reviews")
def list_heritage_reviews(heritage_id: str):
    """
    Retrieve all user reviews for a specific heritage.
    """
    reviews = db.get_heritage_reviews(heritage_id)
    return {
        "status": "success",
        "count": len(reviews),
        "data": reviews
    }

# 5. User Travel Courses
@app.post("/api/v1/courses")
def create_custom_course(req: CourseCreateRequest):
    """
    Create a user custom travel course, including transit type, duration, and storytelling.
    """
    try:
        course = db.create_user_course(
            user_id=req.user_id,
            name=req.name,
            heritage_ids=req.heritage_ids,
            transit_type=req.transit_type,
            duration_mins=req.duration_mins,
            generated_content=req.generated_content
        )
        return {
            "status": "success",
            "data": course
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/v1/courses/{course_id}")
def get_course_details(course_id: str):
    """
    Get detailed structure of a custom travel course.
    """
    course = db.get_course_details(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course ID {course_id} not found."
        )
    return {
        "status": "success",
        "data": course
    }

# 6. User Recommendation proposal tracker status lookup
@app.get("/api/v1/users/{user_id}/recommendations")
def get_user_recommendations_status(user_id: str):
    """
    Fetch the list and review status of all candidates submitted by a specific user.
    """
    tracks = db.get_user_recommendations(user_id)
    return {
        "status": "success",
        "count": len(tracks),
        "data": tracks
    }

# ==========================================
# Open API Integrations
# ==========================================

@app.get("/api/v1/integrations/transit-time")
def calculate_transit_time(heritage_ids: str = Query(..., description="Comma-separated list of H_IDs, e.g. H1,H2,H3")):
    """
    Calculates the real-time public transit duration (using Sejong Bus API) between a sequence of heritage sites.
    """
    ids = [i.strip() for i in heritage_ids.split(",") if i.strip()]
    if len(ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 heritage IDs are required to calculate route time."
        )
        
    total_duration = 0
    segments = []
    
    for i in range(len(ids) - 1):
        h_start = db.get_heritage_by_id(ids[i])
        h_end = db.get_heritage_by_id(ids[i+1])
        
        if not h_start or not h_end:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Heritage ID {ids[i] if not h_start else ids[i+1]} not found."
            )
            
        duration = get_transit_duration(
            h_start["latitude"], h_start["longitude"],
            h_end["latitude"], h_end["longitude"]
        )
        
        total_duration += duration
        segments.append({
            "from_id": ids[i],
            "from_name": h_start["name"],
            "to_id": ids[i+1],
            "to_name": h_end["name"],
            "duration_mins": duration
        })
        
    return {
        "status": "success",
        "total_duration_mins": total_duration,
        "segments": segments
    }

@app.get("/api/v1/integrations/nearby")
def get_nearby_spots(heritage_id: str, radius: int = Query(3000, description="Search radius in meters")):
    """
    Fetches surrounding tourist spots within a radius from KTO TourAPI.
    """
    heritage = db.get_heritage_by_id(heritage_id)
    if not heritage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Heritage ID {heritage_id} not found."
        )
        
    spots = get_nearby_attractions(
        lat=heritage["latitude"],
        lng=heritage["longitude"],
        radius=radius
    )
    
    return {
        "status": "success",
        "count": len(spots),
        "data": spots
    }

@app.post("/api/v1/integrations/sync")
def trigger_heritage_sync():
    """
    Triggers the batch sync job to align local heritage designation categories with Public API lists.
    """
    sync_results = sync_heritage_designations(db_helper=db)
    return sync_results

# ==========================================
# Security & Uploads & Auditing APIs
# ==========================================

def mask_key(key: Optional[str]) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "[설정됨]"
    return f"{key[:4]}...{key[-4:]}"

@app.get("/api/v1/admin/settings", response_model=SettingsResponse)
def get_backend_settings(admin_id: str = Depends(get_current_admin)):
    """
    Retrieves system API settings with keys masked for security.
    """
    settings = db.get_settings()
    return {
        "GOOGLE_API_KEY": mask_key(settings.get("GOOGLE_API_KEY")),
        "TOURAPI_KEY": mask_key(settings.get("TOURAPI_KEY")),
        "SEJONG_BUS_API_KEY": mask_key(settings.get("SEJONG_BUS_API_KEY")),
        "CULTURAL_API_KEY": mask_key(settings.get("CULTURAL_API_KEY")),
        "SUPABASE_URL": settings.get("SUPABASE_URL", ""),
        "SUPABASE_KEY": mask_key(settings.get("SUPABASE_KEY")),
        "NEO4J_URI": settings.get("NEO4J_URI", ""),
        "NEO4J_USERNAME": settings.get("NEO4J_USERNAME", ""),
        "NEO4J_PASSWORD": mask_key(settings.get("NEO4J_PASSWORD"))
    }

@app.post("/api/v1/admin/settings")
def update_backend_settings(req: SettingsUpdateRequest, admin_id: str = Depends(get_current_admin)):
    """
    Updates system API settings. Skips values that are masked placeholders.
    """
    current_settings = db.get_settings()
    updated = False
    
    for k, v in req.dict(exclude_unset=True).items():
        # Update if it's not a masked value (like "[설정됨]" or "...")
        if v is not None:
            if v == "":
                current_settings[k] = ""
                if k in os.environ:
                    del os.environ[k]
                updated = True
            elif not (v.startswith("[설정됨]") or "..." in v):
                current_settings[k] = v
                os.environ[k] = v
                updated = True
                
    if updated:
        db.save_settings(current_settings)
        # Re-initialize DB helper clients dynamically
        db.init_supabase()
        db.init_neo4j()
        
    return {
        "status": "success",
        "message": "시스템 설정이 성공적으로 업데이트되었습니다."
    }

# ==========================================
# Citizen Reports Administration APIs
# ==========================================

@app.get("/api/v1/reports/pending")
def list_pending_reports(admin_id: str = Depends(get_current_admin)):
    """
    Retrieves pending citizen reports (Protected).
    """
    reports = db.get_pending_reports()
    return {
        "status": "success",
        "count": len(reports),
        "data": reports
    }

@app.post("/api/v1/reports/review")
def review_citizen_report(req: ReportReviewRequest, admin_id: str = Depends(get_current_admin)):
    """
    Approves or Rejects a citizen report. APPROVED ones are published to cultural_heritages.
    """
    report = db.review_report(
        report_id=req.report_id,
        status=req.status,
        admin_comment=req.admin_comment,
        admin_id=admin_id
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report ID {req.report_id} not found."
        )
    return {
        "status": "success",
        "message": f"Report ID {req.report_id} reviewed successfully. Status: {req.status}",
        "data": report
    }

@app.get("/api/v1/admin/audit-logs")
def list_admin_audit_logs(admin_id: str = Depends(get_current_admin)):
    """
    Returns administrative review audit log entries (Protected).
    """
    logs = db.get_admin_audit_logs()
    return {
        "status": "success",
        "count": len(logs),
        "data": logs
    }

@app.post("/api/v1/candidates/upload")
def upload_candidate_photo(file: UploadFile = File(...)):
    """
    Handles candidate photo upload with strict size and type constraints.
    """
    # 1. Size constraint: 5MB maximum
    max_size_bytes = 5 * 1024 * 1024
    contents = file.file.read()
    if len(contents) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail="업로드 파일 용량 제한 초과: 최대 5MB까지만 허용됩니다."
        )
        
    # 2. Type validation: JPEG, PNG, WEBP only
    file.file.seek(0) # Reset stream pointer
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="허용되지 않는 파일 형식입니다. JPEG, PNG, WEBP 파일만 업로드할 수 있습니다."
        )
        
    # 3. Simulated malware inspection
    if b"MALWARE_TEST_TRIGGER" in contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="악성 파일 검증 실패: 유해 코드 혹은 악성 파일 패턴이 발견되었습니다."
        )
        
    # Generate mock URL
    return {
        "status": "success",
        "message": "파일 업로드 및 보안 검증 통과 완료.",
        "image_url": f"/static/images/candidates/{file.filename}"
    }
