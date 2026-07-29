import json
import os
import uuid
from datetime import datetime

class SejongDBHelper:
    """
    Helper class to manage and query the mock database for Sejong City Cultural Heritage Service.
    Supports master data searches, citizen candidates, voting, reviews, courses, and LLM prompt templates.
    """
    def __init__(self, db_path=None):
        if db_path is None:
            # Default to mock_db.json in the same directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "mock_db.json")
        self.db_path = db_path
        self.data = {}
        self.load_db()

        self.supabase_client = None
        self.neo4j_driver = None

        self.init_supabase()
        self.init_neo4j()

    def init_supabase(self):
        url = os.environ.get("SUPABASE_URL") or self.get_setting("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY") or self.get_setting("SUPABASE_KEY")
        if url and key:
            try:
                from supabase import create_client
                self.supabase_client = create_client(url, key)
                print("[SejongDBHelper] Supabase client initialized successfully.")
            except Exception as e:
                print(f"[SejongDBHelper] Failed to initialize Supabase client: {e}")
        else:
            self.supabase_client = None
            print("[SejongDBHelper] Supabase URL/Key missing. Local fallback.")

    def init_neo4j(self):
        uri = os.environ.get("NEO4J_URI") or self.get_setting("NEO4J_URI")
        user = os.environ.get("NEO4J_USERNAME") or self.get_setting("NEO4J_USERNAME")
        password = os.environ.get("NEO4J_PASSWORD") or self.get_setting("NEO4J_PASSWORD")
        if uri and user and password:
            try:
                from neo4j import GraphDatabase
                self.neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
                print("[SejongDBHelper] Neo4j driver initialized successfully.")
            except Exception as e:
                print(f"[SejongDBHelper] Failed to initialize Neo4j driver: {e}")
        else:
            self.neo4j_driver = None
            print("[SejongDBHelper] Neo4j URI/User/Pass missing. Local fallback.")

    def get_setting(self, key, default=None):
        return self.get_settings().get(key, default)

    def load_db(self):
        """Loads data from the JSON file. If file doesn't exist, initializes empty schema."""
        if os.path.exists(self.db_path):
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            # Ensure settings is initialized if reading an older file
            if "settings" not in self.data:
                self.data["settings"] = {}
        else:
            self.data = {
                "cultural_heritages": [],
                "citizen_reports": [],
                "citizen_heritage_candidates": [],
                "heritage_reviews": [],
                "user_courses": [],
                "user_recommendation_status": [],
                "graph_connections": [],
                "settings": {}
            }
            self.save_db()

    def save_db(self):
        """Saves current state back to mock_db.json."""
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ==========================================
    # Master Heritage Table Queries
    # ==========================================

    def search_heritage(self, query=None, category=None, dong=None, era=None):
        """
        Search heritages by name/description and filter by category, dong, or era.
        """
        if self.supabase_client:
            try:
                qb = self.supabase_client.table("heritage").select("*")
                if category:
                    qb = qb.eq("category", category)
                if dong:
                    qb = qb.eq("dong", dong)
                if era:
                    qb = qb.eq("era", era)
                res = qb.execute()
                results = res.data
                if query:
                    query = query.lower()
                    results = [
                        h for h in results
                        if query in h.get("name", "").lower() or query in h.get("description", "").lower()
                    ]
                return results
            except Exception as e:
                print(f"[SejongDBHelper] Supabase search_heritage failed: {e}. Falling back to mock DB.")

        results = self.data.get("cultural_heritages", [])
        
        if category:
            results = [h for h in results if h.get("category") == category]
        if dong:
            results = [h for h in results if h.get("dong") == dong]
        if era:
            results = [h for h in results if h.get("era") == era]
            
        if query:
            query = query.lower()
            results = [
                h for h in results 
                if query in h.get("name", "").lower() or query in h.get("description", "").lower()
            ]
            
        return results

    def get_heritage_by_id(self, heritage_id):
        """Retrieves a single heritage by H_ID (e.g. H1) and increments views."""
        if self.supabase_client:
            try:
                res = self.supabase_client.table("heritage").select("*").eq("id", heritage_id).execute()
                if res.data:
                    h = res.data[0]
                    views = h.get("views", 0) + 1
                    self.supabase_client.table("heritage").update({"views": views}).eq("id", heritage_id).execute()
                    h["views"] = views
                    return h
                return None
            except Exception as e:
                print(f"[SejongDBHelper] Supabase get_heritage_by_id failed: {e}. Falling back to mock DB.")

        for h in self.data.get("cultural_heritages", []):
            if h.get("id") == heritage_id:
                h["views"] = h.get("views", 0) + 1
                self.save_db()
                return h
        return None

    # ==========================================
    # Citizen Heritage Candidates & Voting
    # ==========================================

    def get_citizen_candidates(self, status=None):
        """Retrieves proposed candidates, optionally filtered by status."""
        if self.supabase_client:
            try:
                qb = self.supabase_client.table("citizen_heritage_candidate").select("*")
                if status:
                    qb = qb.eq("status", status)
                res = qb.execute()
                return res.data
            except Exception as e:
                print(f"[SejongDBHelper] Supabase get_citizen_candidates failed: {e}. Falling back to mock DB.")

        candidates = self.data.get("citizen_heritage_candidates", [])
        if status:
            candidates = [c for c in candidates if c.get("status") == status]
        return candidates

    def submit_citizen_candidate(self, name, image_urls, latitude, longitude, description, reporter_id):
        """
        Submit a new candidate. Default status is 'PENDING'.
        Adds to candidate table and initializes tracker status.
        """
        if self.supabase_client:
            try:
                new_candidate = {
                    "name": name,
                    "image_urls": image_urls,
                    "latitude": latitude,
                    "longitude": longitude,
                    "description": description,
                    "reporter_id": reporter_id,
                    "votes": 0,
                    "status": "PENDING",
                    "admin_comment": None
                }
                res = self.supabase_client.table("citizen_heritage_candidate").insert(new_candidate).execute()
                if res.data:
                    cand = res.data[0]
                    # Add tracker record
                    tracker = {
                        "candidate_id": cand["id"],
                        "user_id": reporter_id,
                        "status": "PENDING",
                        "feedback": "심사가 시작되었습니다."
                    }
                    self.supabase_client.table("user_recommendation_status").insert(tracker).execute()
                    return cand
            except Exception as e:
                print(f"[SejongDBHelper] Supabase submit_citizen_candidate failed: {e}. Falling back to mock DB.")

        candidates = self.data.get("citizen_heritage_candidates", [])
        new_id = max([c.get("id", 0) for c in candidates]) + 1 if candidates else 1
        
        new_candidate = {
            "id": new_id,
            "name": name,
            "image_urls": image_urls,
            "latitude": latitude,
            "longitude": longitude,
            "description": description,
            "reporter_id": reporter_id,
            "votes": 0,
            "status": "PENDING",
            "admin_comment": None,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        candidates.append(new_candidate)
        
        # Add tracker record
        tracker = self.data.get("user_recommendation_status", [])
        tracker.append({
            "candidate_id": new_id,
            "user_id": reporter_id,
            "recommended_date": datetime.utcnow().isoformat() + "Z",
            "status": "PENDING",
            "feedback": "심사가 시작되었습니다."
        })
        
        self.save_db()
        return new_candidate

    def vote_citizen_candidate(self, candidate_id, user_id):
        """Increments vote count for a proposed candidate."""
        if self.supabase_client:
            try:
                res = self.supabase_client.table("citizen_heritage_candidate").select("votes").eq("id", candidate_id).execute()
                if res.data:
                    votes = (res.data[0]["votes"] or 0) + 1
                    update_res = self.supabase_client.table("citizen_heritage_candidate").update({"votes": votes}).eq("id", candidate_id).execute()
                    return update_res.data[0] if update_res.data else None
            except Exception as e:
                print(f"[SejongDBHelper] Supabase vote_citizen_candidate failed: {e}. Falling back to mock DB.")

        candidates = self.data.get("citizen_heritage_candidates", [])
        for c in candidates:
            if c.get("id") == candidate_id:
                c["votes"] = c.get("votes", 0) + 1
                self.save_db()
                return c
        return None

    def review_citizen_candidate(self, candidate_id, status, admin_comment=None, admin_id="system_admin"):
        """
        Admin reviews candidate. If APPROVED, parses details and 
        publishes to master heritage table under H{ID}.
        Also records an audit log event.
        """
        if status not in ["APPROVED", "REJECTED"]:
            raise ValueError("Status must be 'APPROVED' or 'REJECTED'")
            
        if self.supabase_client:
            try:
                res = self.supabase_client.table("citizen_heritage_candidate").update({
                    "status": status,
                    "admin_comment": admin_comment
                }).eq("id", candidate_id).execute()
                
                if res.data:
                    cand = res.data[0]
                    self.supabase_client.table("user_recommendation_status").update({
                        "status": status,
                        "feedback": admin_comment or f"제보가 {status} 처리되었습니다."
                    }).eq("candidate_id", candidate_id).execute()
                    
                    self.supabase_client.table("admin_audit_log").insert({
                        "admin_id": admin_id,
                        "action": "APPROVE_CANDIDATE" if status == "APPROVED" else "REJECT_CANDIDATE",
                        "target_id": candidate_id,
                        "admin_comment": admin_comment
                    }).execute()
                    
                    if status == "APPROVED":
                        h_res = self.supabase_client.table("heritage").select("id").execute()
                        h_nums = []
                        for h in h_res.data:
                            h_id = h.get("id", "")
                            if h_id.startswith("H"):
                                try:
                                    h_nums.append(int(h_id[1:]))
                                except ValueError:
                                    pass
                        next_h_num = max(h_nums) + 1 if h_nums else 120
                        new_h_id = f"H{next_h_num}"
                        
                        address = cand.get("address") or "세종특별자치시 새롬동"
                        tokens = address.split()
                        dong = "새롬동"
                        for t in tokens:
                            if t.endswith(('읍', '면', '동')):
                                dong = t
                                break
                        
                        new_h = {
                            "id": new_h_id,
                            "name": cand.get("name"),
                            "category": "현대명소",
                            "address": address,
                            "dong": dong,
                            "latitude": cand.get("latitude"),
                            "longitude": cand.get("longitude"),
                            "description": f"{cand.get('description')} (시민 제보 후보 승인)",
                            "thought_prompt": "시민이 참여해 발굴한 이 유산이 미래 세대에 어떤 의미를 줄지 관찰해 보세요.",
                            "image_url": cand.get("image_urls")[0] if cand.get("image_urls") else "/static/images/default.jpg",
                            "views": 0
                        }
                        self.supabase_client.table("heritage").insert(new_h).execute()
                        
                    return cand
                return None
            except Exception as e:
                print(f"[SejongDBHelper] Supabase review_citizen_candidate failed: {e}. Falling back to mock DB.")

        candidates = self.data.get("citizen_heritage_candidates", [])
        target_cand = None
        for c in candidates:
            if c.get("id") == candidate_id:
                target_cand = c
                break
                
        if not target_cand:
            return None
            
        target_cand["status"] = status
        target_cand["admin_comment"] = admin_comment
        
        tracker = self.data.get("user_recommendation_status", [])
        for t in tracker:
            if t.get("candidate_id") == candidate_id:
                t["status"] = status
                t["feedback"] = admin_comment or f"제보가 {status} 처리되었습니다."
                
        if status == "APPROVED":
            heritages = self.data.get("cultural_heritages", [])
            
            h_nums = []
            for h in heritages:
                h_id = h.get("id", "")
                if h_id.startswith("H"):
                    try:
                        h_nums.append(int(h_id[1:]))
                    except ValueError:
                        pass
            next_h_num = max(h_nums) + 1 if h_nums else 120
            new_h_id = f"H{next_h_num}"
            
            address = target_cand.get("address", "세종특별자치시 새롬동")
            tokens = address.split()
            dong = "새롬동"
            for t in tokens:
                if t.endswith(('읍', '면', '동')):
                    dong = t
                    break
                    
            new_heritage = {
                "id": new_h_id,
                "name": target_cand.get("name"),
                "category": "현대명소",
                "address": address,
                "dong": dong,
                "latitude": target_cand.get("latitude"),
                "longitude": target_cand.get("longitude"),
                "description": f"{target_cand.get('description')} (시민 제보 후보 승인)",
                "thought_prompt": "시민이 참여해 발굴한 이 유산이 미래 세대에 어떤 의미를 줄지 관찰해 보세요.",
                "image_url": target_cand.get("image_urls")[0] if target_cand.get("image_urls") else "/static/images/default.jpg",
                "views": 0
            }
            heritages.append(new_heritage)
            
        # Write admin audit log
        audit_logs = self.data.setdefault("admin_audit_logs", [])
        new_log_id = max([x.get("id", 0) for x in audit_logs]) + 1 if audit_logs else 1
        action = "APPROVE_CANDIDATE" if status == "APPROVED" else "REJECT_CANDIDATE"
        audit_logs.append({
            "id": new_log_id,
            "admin_id": admin_id,
            "action": action,
            "target_id": candidate_id,
            "admin_comment": admin_comment,
            "created_at": datetime.utcnow().isoformat() + "Z"
        })
            
        self.save_db()
        return target_cand

    # ==========================================
    # Heritage Reviews (문화유산 후기)
    # ==========================================

    def submit_heritage_review(self, heritage_id, user_id, image_url, content):
        """Submit user review for a specific heritage."""
        if self.supabase_client:
            try:
                heritage = self.get_heritage_by_id(heritage_id)
                if not heritage:
                    raise ValueError(f"Heritage ID {heritage_id} does not exist.")
                new_review = {
                    "heritage_id": heritage_id,
                    "user_id": user_id,
                    "image_url": image_url,
                    "content": content
                }
                res = self.supabase_client.table("heritage_review").insert(new_review).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                print(f"[SejongDBHelper] Supabase submit_heritage_review failed: {e}. Falling back to mock DB.")

        heritage = self.get_heritage_by_id(heritage_id)
        if not heritage:
            raise ValueError(f"Heritage ID {heritage_id} does not exist.")
            
        reviews = self.data.get("heritage_reviews", [])
        new_id = max([r.get("id", 0) for r in reviews]) + 1 if reviews else 1
        
        new_review = {
            "id": new_id,
            "heritage_id": heritage_id,
            "user_id": user_id,
            "image_url": image_url,
            "content": content,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        reviews.append(new_review)
        self.save_db()
        return new_review

    def get_heritage_reviews(self, heritage_id):
        """Fetch all reviews for a heritage."""
        if self.supabase_client:
            try:
                res = self.supabase_client.table("heritage_review").select("*").eq("heritage_id", heritage_id).execute()
                return res.data
            except Exception as e:
                print(f"[SejongDBHelper] Supabase get_heritage_reviews failed: {e}. Falling back to mock DB.")

        reviews = self.data.get("heritage_reviews", [])
        return [r for r in reviews if r.get("heritage_id") == heritage_id]

    # ==========================================
    # User Course & AI Generated Narrative
    # ==========================================

    def create_user_course(self, user_id, name, heritage_ids, transit_type, duration_mins, generated_content=None):
        """Creates a custom tour route for a user with transit details and AI narratives."""
        if self.supabase_client:
            try:
                for h_id in heritage_ids:
                    if not self.get_heritage_by_id(h_id):
                        raise ValueError(f"Heritage ID {h_id} does not exist.")
                course_id = str(uuid.uuid4())
                payload = {
                    "course_id": course_id,
                    "user_id": user_id,
                    "name": name,
                    "heritage_ids": heritage_ids,
                    "transit_type": transit_type,
                    "duration_mins": duration_mins,
                    "generated_content": generated_content
                }
                res = self.supabase_client.table("user_course").insert(payload).execute()
                
                # Sync new course to Neo4j dynamically if driver exists
                if self.neo4j_driver:
                    try:
                        with self.neo4j_driver.session() as session:
                            session.run("""
                            MERGE (c:Course {id: $course_id})
                            SET c.title = $name,
                                c.user_id = $user_id,
                                c.transit_type = $transit_type,
                                c.duration_mins = $duration_mins,
                                c.generated_content = $generated_content
                            """, course_id=course_id, name=name, user_id=user_id,
                               transit_type=transit_type, duration_mins=duration_mins,
                               generated_content=generated_content)
                            for index, h_id in enumerate(heritage_ids):
                                session.run("""
                                MATCH (c:Course {id: $course_id})
                                MATCH (h:Heritage {id: $heritage_id})
                                MERGE (c)-[:VISITS {stop_order: $stop_order}]->(h)
                                """, course_id=course_id, heritage_id=h_id, stop_order=index + 1)
                    except Exception as ge:
                        print(f"[SejongDBHelper] Neo4j course sync failed: {ge}")

                if res.data:
                    c = res.data[0]
                    return {
                        "id": c["course_id"],
                        "user_id": c["user_id"],
                        "title": c["name"],
                        "name": c["name"],
                        "description": f"교통수단: {transit_type}, 소요시간: {duration_mins}분 코스",
                        "theme": "맞춤 탐방",
                        "transit_type": transit_type,
                        "duration_mins": duration_mins,
                        "generated_content": generated_content,
                        "stops": [{"stop_order": i + 1, "heritage_id": h_id} for i, h_id in enumerate(heritage_ids)]
                    }
            except Exception as e:
                print(f"[SejongDBHelper] Supabase create_user_course failed: {e}. Falling back to mock DB.")

        courses = self.data.get("user_courses", [])
        course_id = str(uuid.uuid4())
        
        stops = []
        for index, h_id in enumerate(heritage_ids):
            heritage = self.get_heritage_by_id(h_id)
            if not heritage:
                raise ValueError(f"Heritage ID {h_id} does not exist.")
            stops.append({
                "stop_order": index + 1,
                "heritage_id": h_id
            })
            
        new_course = {
            "id": course_id,
            "user_id": user_id,
            "title": name,
            "name": name,
            "description": f"교통수단: {transit_type}, 소요시간: {duration_mins}분 코스",
            "theme": "맞춤 탐방",
            "transit_type": transit_type,
            "duration_mins": duration_mins,
            "generated_content": generated_content,
            "stops": stops,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        courses.append(new_course)
        self.save_db()
        return new_course

    def get_course_details(self, course_id):
        """Returns the full details of a course including detailed stops info."""
        if self.supabase_client:
            try:
                res = self.supabase_client.table("user_course").select("*").eq("course_id", course_id).execute()
                if res.data:
                    c = res.data[0]
                    heritage_ids = c.get("heritage_ids", [])
                    stops_detailed = []
                    for index, h_id in enumerate(heritage_ids):
                        heritage = self.get_heritage_by_id(h_id)
                        stops_detailed.append({
                            "stop_order": index + 1,
                            "heritage": heritage
                        })
                    return {
                        "id": c["course_id"],
                        "user_id": c["user_id"],
                        "title": c["name"],
                        "name": c["name"],
                        "description": f"교통수단: {c['transit_type']}, 소요시간: {c['duration_mins']}분 코스",
                        "theme": "맞춤 탐방",
                        "transit_type": c["transit_type"],
                        "duration_mins": c["duration_mins"],
                        "generated_content": c.get("generated_content"),
                        "stops": stops_detailed
                    }
                return None
            except Exception as e:
                print(f"[SejongDBHelper] Supabase get_course_details failed: {e}. Falling back to mock DB.")

        for course in self.data.get("user_courses", []):
            if course.get("id") == course_id:
                stops_detailed = []
                sorted_stops = sorted(course.get("stops", []), key=lambda s: s.get("stop_order"))
                for s in sorted_stops:
                    heritage = self.get_heritage_by_id(s.get("heritage_id"))
                    stops_detailed.append({
                        "stop_order": s.get("stop_order"),
                        "heritage": heritage
                    })
                
                course_copy = dict(course)
                course_copy["stops"] = stops_detailed
                return course_copy
        return None

    # ==========================================
    # Recommendation Status Tracker lookup
    # ==========================================

    def get_user_recommendations(self, user_id):
        """Returns proposed candidates list submitted by the user."""
        if self.supabase_client:
            try:
                res = self.supabase_client.table("user_recommendation_status").select("*").eq("user_id", user_id).execute()
                detailed_tracks = []
                for t in res.data:
                    c_res = self.supabase_client.table("citizen_heritage_candidate").select("*").eq("id", t["candidate_id"]).execute()
                    candidate = c_res.data[0] if c_res.data else None
                    detailed_tracks.append({
                        "candidate": candidate,
                        "recommended_date": t.get("recommended_date"),
                        "status": t["status"],
                        "feedback": t.get("feedback")
                    })
                return detailed_tracks
            except Exception as e:
                print(f"[SejongDBHelper] Supabase get_user_recommendations failed: {e}. Falling back to mock DB.")

        tracker = self.data.get("user_recommendation_status", [])
        user_tracks = [t for t in tracker if t.get("user_id") == user_id]
        
        candidates = self.data.get("citizen_heritage_candidates", [])
        detailed_tracks = []
        for t in user_tracks:
            candidate = next((c for c in candidates if c["id"] == t["candidate_id"]), None)
            detailed_tracks.append({
                "candidate": candidate,
                "recommended_date": t["recommended_date"],
                "status": t["status"],
                "feedback": t["feedback"]
            })
        return detailed_tracks

    # ==========================================
    # Graph-like Recommendation Simulation (Neo4j)
    # ==========================================

    def get_nearby_recommendations(self, heritage_id, limit=3):
        """Simulates or queries Neo4j spatial connection lookups."""
        if self.neo4j_driver:
            try:
                query = """
                MATCH (h1:Heritage {id: $heritage_id})-[r:NEXT_TO]->(h2:Heritage)
                RETURN h2, r.distance_km AS distance_km, r.travel_time_mins AS travel_time_mins
                ORDER BY distance_km ASC LIMIT $limit
                """
                with self.neo4j_driver.session() as session:
                    result = session.run(query, heritage_id=heritage_id, limit=limit)
                    nearby = []
                    for record in result:
                        h2 = record["h2"]
                        heritage_dict = {
                            "id": h2.get("id"),
                            "name": h2.get("name"),
                            "category": h2.get("category"),
                            "address": h2.get("address"),
                            "dong": h2.get("dong"),
                            "latitude": h2.get("latitude"),
                            "longitude": h2.get("longitude"),
                            "description": h2.get("description"),
                            "image_url": h2.get("image_url"),
                            "views": h2.get("views"),
                            "thought_prompt": h2.get("thought_prompt")
                        }
                        nearby.append({
                            "heritage": heritage_dict,
                            "distance_km": record["distance_km"],
                            "travel_time_mins": record["travel_time_mins"]
                        })
                    return nearby
            except Exception as e:
                print(f"[SejongDBHelper] Neo4j get_nearby_recommendations failed: {e}. Falling back to mock DB.")

        connections = self.data.get("graph_connections", [])
        nearby_candidates = []
        
        for conn in connections:
            neighbor_id = None
            dist = conn.get("distance_km")
            time = conn.get("travel_time_mins")
            
            if conn.get("source_id") == heritage_id:
                neighbor_id = conn.get("target_id")
            elif conn.get("target_id") == heritage_id:
                neighbor_id = conn.get("source_id")
                
            if neighbor_id:
                neighbor = self.get_heritage_by_id(neighbor_id)
                if neighbor:
                    nearby_candidates.append({
                        "heritage": neighbor,
                        "distance_km": dist,
                        "travel_time_mins": time
                    })
                    
        nearby_candidates = sorted(nearby_candidates, key=lambda c: c["distance_km"])
        return nearby_candidates[:limit]

    # ==========================================
    # LLM Context Utility
    # ==========================================

    def get_llm_context_string(self, heritage_id):
        """Formats a heritage site's details into a clean text block."""
        h = self.get_heritage_by_id(heritage_id)
        if not h:
            return "문화유산 정보가 존재하지 않습니다."
            
        nearby = self.get_nearby_recommendations(heritage_id, limit=3)
        nearby_str = ", ".join([f"{n['heritage']['name']}({n['distance_km']}km)" for n in nearby])
        if not nearby_str:
            nearby_str = "주변 연계 가능한 문화유산 없음"
            
        context = (
            f"=== 세종시 문화유산 정보 ===\n"
            f"H_ID: {h.get('id')}\n"
            f"명칭: {h.get('name')}\n"
            f"분류: {h.get('category')} / 시대: {h.get('era')}\n"
            f"행정동: {h.get('dong')} / 주소: {h.get('address')}\n"
            f"소개: {h.get('description')}\n"
            f"생각할 거리: {h.get('thought_prompt')}\n"
            f"주변 인접 명소: {nearby_str}\n"
            f"=============================="
        )
        return context

    # ==========================================
    # Admin Audit Logs
    # ==========================================

    def get_admin_audit_logs(self):
        """Fetch all administrative review action log records."""
        if self.supabase_client:
            try:
                res = self.supabase_client.table("admin_audit_log").select("*").execute()
                return res.data
            except Exception as e:
                print(f"[SejongDBHelper] Supabase get_admin_audit_logs failed: {e}. Falling back to mock DB.")

        return self.data.get("admin_audit_logs", [])

    # ==========================================
    # System Settings Management
    # ==========================================

    def get_settings(self):
        """Fetch settings dictionary."""
        return self.data.setdefault("settings", {})

    def save_settings(self, settings_dict):
        """Save settings dictionary to DB."""
        self.data["settings"] = settings_dict
        self.save_db()

    # ==========================================
    # Citizen Reports & Auditing APIs
    # ==========================================

    def get_pending_reports(self):
        """Fetch all citizen reports with PENDING status."""
        if self.supabase_client:
            try:
                res = self.supabase_client.table("citizen_report").select("*").eq("status", "PENDING").execute()
                return res.data
            except Exception as e:
                print(f"[SejongDBHelper] Supabase get_pending_reports failed: {e}. Falling back to mock DB.")

        reports = self.data.setdefault("citizen_reports", [])
        return [r for r in reports if r.get("status") == "PENDING"]

    def review_report(self, report_id, status, admin_comment=None, admin_id="system_admin"):
        """Admin reviews a citizen report (APPROVE/REJECT). If APPROVED, publishes to cultural_heritages."""
        if status not in ["APPROVED", "REJECTED"]:
            raise ValueError("Status must be 'APPROVED' or 'REJECTED'")
            
        if self.supabase_client:
            try:
                res = self.supabase_client.table("citizen_report").update({
                    "status": status,
                    "admin_comment": admin_comment
                }).eq("id", report_id).execute()
                
                if res.data:
                    rep = res.data[0]
                    self.supabase_client.table("admin_audit_log").insert({
                        "admin_id": admin_id,
                        "action": "APPROVE_REPORT" if status == "APPROVED" else "REJECT_REPORT",
                        "target_id": report_id,
                        "admin_comment": admin_comment
                    }).execute()
                    
                    if status == "APPROVED":
                        h_res = self.supabase_client.table("heritage").select("id").execute()
                        h_nums = []
                        for h in h_res.data:
                            h_id = h.get("id", "")
                            if h_id.startswith("H"):
                                try:
                                    h_nums.append(int(h_id[1:]))
                                except ValueError:
                                    pass
                        next_h_num = max(h_nums) + 1 if h_nums else 120
                        new_h_id = f"H{next_h_num}"
                        
                        address = rep.get("address") or "세종특별자치시 보람동"
                        tokens = address.split()
                        dong = "보람동"
                        for t in tokens:
                            if t.endswith(('읍', '면', '동')):
                                dong = t
                                break
                                
                        new_h = {
                            "id": new_h_id,
                            "name": rep.get("title"),
                            "category": "현대명소",
                            "address": address,
                            "dong": dong,
                            "latitude": rep.get("latitude"),
                            "longitude": rep.get("longitude"),
                            "description": f"{rep.get('description')} (시민 제보 승인)",
                            "thought_prompt": "시민이 참여해 발굴한 이 유산이 미래 세대에 어떤 의미를 줄지 관찰해 보세요.",
                            "image_url": "/static/images/default.jpg",
                            "views": 0
                        }
                        self.supabase_client.table("heritage").insert(new_h).execute()
                        
                    return rep
                return None
            except Exception as e:
                print(f"[SejongDBHelper] Supabase review_report failed: {e}. Falling back to mock DB.")

        reports = self.data.setdefault("citizen_reports", [])
        target_report = None
        for r in reports:
            if r.get("id") == report_id:
                target_report = r
                break
                
        if not target_report:
            return None
            
        target_report["status"] = status
        target_report["admin_comment"] = admin_comment
        target_report["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        if status == "APPROVED":
            heritages = self.data.setdefault("cultural_heritages", [])
            h_nums = []
            for h in heritages:
                h_id = h.get("id", "")
                if h_id.startswith("H"):
                    try:
                        h_nums.append(int(h_id[1:]))
                    except ValueError:
                        pass
            next_h_num = max(h_nums) + 1 if h_nums else 120
            new_h_id = f"H{next_h_num}"
            
            address = target_report.get("address", "세종특별자치시 보람동")
            tokens = address.split()
            dong = "보람동"
            for t in tokens:
                if t.endswith(('읍', '면', '동')):
                    dong = t
                    break
                    
            new_heritage = {
                "id": new_h_id,
                "name": target_report.get("title"),
                "category": "현대명소",
                "address": address,
                "dong": dong,
                "latitude": target_report.get("latitude"),
                "longitude": target_report.get("longitude"),
                "description": f"{target_report.get('description')} (시민 제보 승인)",
                "thought_prompt": "시민이 참여해 발굴한 이 유산이 미래 세대에 어떤 의미를 줄지 관찰해 보세요.",
                "image_url": "/static/images/default.jpg",
                "views": 0
            }
            heritages.append(new_heritage)
            
        # Write admin audit log
        audit_logs = self.data.setdefault("admin_audit_logs", [])
        new_log_id = max([x.get("id", 0) for x in audit_logs]) + 1 if audit_logs else 1
        action = "APPROVE_REPORT" if status == "APPROVED" else "REJECT_REPORT"
        audit_logs.append({
            "id": new_log_id,
            "admin_id": admin_id,
            "action": action,
            "target_id": report_id,
            "admin_comment": admin_comment,
            "created_at": datetime.utcnow().isoformat() + "Z"
        })
        self.save_db()
        return target_report
