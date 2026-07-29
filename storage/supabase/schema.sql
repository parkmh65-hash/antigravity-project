-- Sejong City Cultural Heritage Service - Supabase/PostgreSQL Database Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Define Enum for Historical Eras
CREATE TYPE era_type AS ENUM (
    '삼국시대',
    '통일신라시대',
    '고려시대',
    '조선시대',
    '근대',
    '현대'
);

-- Define Enum for Review Status
CREATE TYPE candidate_status AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED'
);

-- 1. Cultural Heritage Master Table
CREATE TABLE IF NOT EXISTS heritage (
    id VARCHAR(50) PRIMARY KEY,      -- H_ID (e.g., H1 ~ H119)
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,  -- 유형문화재, 기념물, 문화재자료, 현대명소 등
    address TEXT NOT NULL,
    dong VARCHAR(100) NOT NULL,      -- Parsed administrative district (e.g., 전의면, 보람동)
    description TEXT,
    era era_type NOT NULL,           -- Normalized era enum
    thought_prompt TEXT,             -- 생각할 거리
    image_url VARCHAR(255),          -- CDN or static storage file path (deprecating but keeping for compatibility)
    images TEXT[],                   -- Array of image paths
    views INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    type VARCHAR(50) DEFAULT 'official',   -- official | citizen
    status VARCHAR(50) DEFAULT 'approved',  -- pending | approved | needs_review
    has_parking BOOLEAN DEFAULT FALSE,
    has_restroom BOOLEAN DEFAULT FALSE,
    nearby_restaurant BOOLEAN DEFAULT FALSE,
    reporter_user_id VARCHAR(255),
    report_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_heritage_dong ON heritage(dong);
CREATE INDEX IF NOT EXISTS idx_heritage_era ON heritage(era);
CREATE INDEX IF NOT EXISTS idx_heritage_name ON heritage(name);

-- 2. Citizen Recommendations Candidate Table (시민 추천 문화유산 후보)
CREATE TABLE IF NOT EXISTS citizen_heritage_candidate (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    image_urls TEXT[] NOT NULL,      -- Array of uploaded image paths
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    description TEXT NOT NULL,
    reporter_id VARCHAR(255) NOT NULL,
    votes INTEGER DEFAULT 0,         -- Recommendation likes/votes
    status candidate_status DEFAULT 'PENDING',
    admin_comment TEXT,              -- Admin comments or feedback
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON citizen_heritage_candidate
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 4. User Travel Courses (나만의 코스)
CREATE TABLE IF NOT EXISTS user_course (
    course_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    heritage_ids VARCHAR(50)[] NOT NULL,   -- Array of heritage IDs in sequential order
    transit_type VARCHAR(50) NOT NULL,      -- 교통수단: 보행, 차량, 자전거 등
    duration_mins INTEGER NOT NULL,          -- 소요 시간(분 단위)
    generated_content TEXT,                 -- AI generated narrative (magazine/fairy tale format)
    is_public BOOLEAN DEFAULT FALSE,
    like_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER update_user_course_updated_at
    BEFORE UPDATE ON user_course
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 3. Cultural Heritage Reviews (문화유산 후기) - course unit with sub-reviews
CREATE TABLE IF NOT EXISTS heritage_review (
    id SERIAL PRIMARY KEY,
    course_id UUID REFERENCES user_course(course_id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    companion_type VARCHAR(100),          -- 누구와 방문했는지
    overall_satisfaction INTEGER DEFAULT 5, -- 만족도 (별점)
    overall_text TEXT,                    -- 전체 감상 후기
    is_recommended BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT TRUE,
    image_url VARCHAR(255),               -- 대표 사진
    heritage_reviews JSONB,               -- Nested heritage reviews array (JSON format)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_review_course_id ON heritage_review(course_id);

-- 5. User Recommendation Proposal Status Tracker (내가 추천한 문화유산 현황)
CREATE TABLE IF NOT EXISTS user_recommendation_status (
    candidate_id INTEGER REFERENCES citizen_heritage_candidate(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    recommended_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status candidate_status DEFAULT 'PENDING',
    feedback TEXT,
    PRIMARY KEY (candidate_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_rec_status_user_id ON user_recommendation_status(user_id);

-- 6. Administrator Audit Logs (감사 로그 테이블)
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id SERIAL PRIMARY KEY,
    admin_id VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,            -- 'APPROVE_CANDIDATE', 'REJECT_CANDIDATE'
    target_id INTEGER NOT NULL,              -- Target candidate_id
    admin_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_admin ON admin_audit_log(admin_id);

-- 7. Citizen Reports Table (시민 제보)
CREATE TABLE IF NOT EXISTS citizen_report (
    id SERIAL PRIMARY KEY,
    reporter_name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    address TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    historical_significance TEXT,
    status candidate_status DEFAULT 'PENDING',
    admin_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER update_citizen_report_updated_at
    BEFORE UPDATE ON citizen_report
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_citizen_report_status ON citizen_report(status);

-- 8. AI Magazine logs
CREATE TABLE IF NOT EXISTS ai_magazine (
    id SERIAL PRIMARY KEY,
    course_id UUID REFERENCES user_course(course_id) ON DELETE CASCADE,
    generated_asset_url VARCHAR(255) NOT NULL,
    sent_to_email VARCHAR(255) NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_magazine_course_id ON ai_magazine(course_id);
