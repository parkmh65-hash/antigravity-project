import os
import json
from supabase import create_client
from neo4j import GraphDatabase

# Get credentials
def get_credentials():
    # 1. Check env
    creds = {
        "SUPABASE_URL": os.environ.get("SUPABASE_URL"),
        "SUPABASE_KEY": os.environ.get("SUPABASE_KEY"),
        "NEO4J_URI": os.environ.get("NEO4J_URI"),
        "NEO4J_USERNAME": os.environ.get("NEO4J_USERNAME"),
        "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD"),
    }
    
    # 2. Check mock_db settings if missing
    base_dir = os.path.dirname(os.path.abspath(__file__))
    mock_db_path = os.path.join(base_dir, "mock_db.json")
    if os.path.exists(mock_db_path):
        try:
            with open(mock_db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                settings = data.get("settings", {})
                for k in creds:
                    if not creds[k]:
                        creds[k] = settings.get(k)
        except Exception as e:
            print(f"Failed to read settings from mock_db.json: {e}")
            
    return creds

def seed_supabase(supabase_client, mock_data):
    print("\n--- Seeding Supabase ---")
    
    # 1. Seed heritages
    heritages = mock_data.get("cultural_heritages", [])
    print(f"Upserting {len(heritages)} heritages...")
    for h in heritages:
        # Determine deterministic amenities based on H_ID number
        try:
            num = int(h["id"][1:])
        except ValueError:
            num = 1
        has_parking = (num % 2 == 0)
        has_restroom = (num % 3 == 0)
        nearby_restaurant = (num % 5 == 0)

        payload = {
            "id": h["id"],
            "name": h["name"],
            "category": h["category"],
            "address": h["address"],
            "dong": h["dong"],
            "description": h.get("description"),
            "era": h["era"],
            "thought_prompt": h.get("thought_prompt"),
            "image_url": h.get("image_url"),
            "images": [h["image_url"]] if h.get("image_url") else [],
            "views": h.get("views", 0),
            "like_count": h.get("views", 0) // 4,
            "type": "official",
            "status": "approved",
            "has_parking": has_parking,
            "has_restroom": has_restroom,
            "nearby_restaurant": nearby_restaurant,
            "reporter_user_id": None,
            "report_reason": None
        }
        supabase_client.table("heritage").upsert(payload).execute()
        
    # 2. Seed citizen_reports
    reports = mock_data.get("citizen_reports", [])
    print(f"Upserting {len(reports)} citizen reports...")
    for r in reports:
        payload = {
            "id": r["id"],
            "reporter_name": r["reporter_name"],
            "title": r["title"],
            "description": r["description"],
            "address": r["address"],
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "historical_significance": r.get("historical_significance"),
            "status": r["status"],
            "admin_comment": r.get("admin_comment")
        }
        supabase_client.table("citizen_report").upsert(payload).execute()
        
    # 3. Seed citizen_heritage_candidates
    candidates = mock_data.get("citizen_heritage_candidates", [])
    print(f"Upserting {len(candidates)} candidates...")
    for c in candidates:
        payload = {
            "id": c["id"],
            "name": c["name"],
            "image_urls": c.get("image_urls", []),
            "latitude": c.get("latitude"),
            "longitude": c.get("longitude"),
            "description": c["description"],
            "reporter_id": c["reporter_id"],
            "votes": c.get("votes", 0),
            "status": c["status"],
            "admin_comment": c.get("admin_comment")
        }
        supabase_client.table("citizen_heritage_candidate").upsert(payload).execute()
        
    # 5. Seed user courses (seeded first because reviews reference courses)
    courses = mock_data.get("user_courses", [])
    print(f"Upserting {len(courses)} user courses...")
    for co in courses:
        payload = {
            "course_id": co["id"],
            "user_id": co["user_id"],
            "name": co["title"],
            "heritage_ids": [s["heritage_id"] for s in co.get("stops", [])],
            "transit_type": co["transit_type"],
            "duration_mins": co["duration_mins"],
            "generated_content": co.get("generated_content"),
            "is_public": True,
            "like_count": 12
        }
        supabase_client.table("user_course").upsert(payload).execute()

    # 4. Seed reviews (nested)
    reviews = mock_data.get("heritage_reviews", [])
    print(f"Upserting {len(reviews)} reviews...")
    for rv in reviews:
        payload = {
            "id": rv["id"],
            "course_id": "c8932912-9d48-4a50-a466-ca22c2bffac3",  # Reference seeded course
            "user_id": rv["user_id"],
            "companion_type": "가족",
            "overall_satisfaction": 5,
            "overall_text": "전체적으로 매우 유익하고 유산 관리가 잘 되어 있는 코스였습니다.",
            "is_recommended": True,
            "is_public": True,
            "image_url": rv.get("image_url"),
            "heritage_reviews": [
                {
                    "heritageId": rv["heritage_id"],
                    "images": [rv["image_url"]] if rv.get("image_url") else [],
                    "isRecommended": True,
                    "text": rv["content"],
                    "amenitySatisfaction": 5,
                    "parkingOk": True,
                    "parkingNeedsImprovement": False,
                    "restroomOk": True,
                    "restroomNeedsImprovement": False,
                    "nearbyRestaurant": True
                }
            ]
        }
        supabase_client.table("heritage_review").upsert(payload).execute()
        
    # 6. Seed recommendation tracker status
    trackers = mock_data.get("user_recommendation_status", [])
    print(f"Upserting {len(trackers)} tracker records...")
    for t in trackers:
        payload = {
            "candidate_id": t["candidate_id"],
            "user_id": t["user_id"],
            "status": t["status"],
            "feedback": t.get("feedback")
        }
        supabase_client.table("user_recommendation_status").upsert(payload).execute()
        
    # 7. Seed AI Magazine
    print("Upserting initial AI magazine log...")
    magazine_payload = {
        "id": 1,
        "course_id": "c8932912-9d48-4a50-a466-ca22c2bffac3",
        "generated_asset_url": "https://example.com/magazine/sejong-healing.pdf",
        "sent_to_email": "demo@sejong.go.kr"
    }
    supabase_client.table("ai_magazine").upsert(magazine_payload).execute()

    print("Supabase seeding completed successfully.")

def sync_supabase_to_neo4j(supabase_client, neo4j_driver, mock_data):
    print("\n--- Syncing Supabase Data to Neo4j ---")
    
    # Fetch all heritages from Supabase
    res = supabase_client.table("heritage").select("*").execute()
    heritages = res.data
    
    print(f"Fetched {len(heritages)} heritages from Supabase.")
    
    # 1. Setup Neo4j constraints
    with neo4j_driver.session() as session:
        session.run("CREATE CONSTRAINT heritage_id_unique IF NOT EXISTS FOR (h:Heritage) REQUIRE h.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE;")
        session.run("CREATE CONSTRAINT era_name_unique IF NOT EXISTS FOR (e:Era) REQUIRE e.name IS UNIQUE;")
        session.run("CREATE CONSTRAINT location_name_unique IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE;")
        session.run("CREATE CONSTRAINT course_id_unique IF NOT EXISTS FOR (co:Course) REQUIRE co.id IS UNIQUE;")
        
    # 2. Sync Heritage nodes and attributes
    print("Populating Heritage, Category, Era, Location nodes & relationships...")
    with neo4j_driver.session() as session:
        for h in heritages:
            session.run("""
            MERGE (h:Heritage {id: $id})
            SET h.name = $name,
                h.address = $address,
                h.description = $description,
                h.thought_prompt = $thought_prompt,
                h.image_url = $image_url,
                h.views = $views
            
            MERGE (c:Category {name: $category})
            MERGE (e:Era {name: $era})
            MERGE (l:Location {name: $dong})
            
            MERGE (h)-[:BELONGS_TO]->(c)
            MERGE (h)-[:FROM_ERA]->(e)
            MERGE (h)-[:LOCATED_IN]->(l)
            """, id=h["id"], name=h["name"], address=h["address"], 
               description=h.get("description"), thought_prompt=h.get("thought_prompt"),
               image_url=h.get("image_url"), views=h.get("views", 0),
               category=h["category"], era=h["era"], dong=h["dong"])
            
    # 3. Sync NEXT_TO spatial proximity connections
    connections = mock_data.get("graph_connections", [])
    print(f"Populating {len(connections)} NEXT_TO spatial relationships...")
    with neo4j_driver.session() as session:
        for conn in connections:
            session.run("""
            MATCH (h1:Heritage {id: $source_id})
            MATCH (h2:Heritage {id: $target_id})
            MERGE (h1)-[r:NEXT_TO {distance_km: $distance_km, travel_time_mins: $travel_time_mins}]->(h2)
            """, source_id=conn["source_id"], target_id=conn["target_id"],
               distance_km=conn["distance_km"], travel_time_mins=conn["travel_time_mins"])
            
    # 4. Sync Course nodes and VISITS relationships
    res_courses = supabase_client.table("user_course").select("*").execute()
    courses = res_courses.data
    print(f"Populating {len(courses)} Course nodes & VISITS relationships...")
    with neo4j_driver.session() as session:
        for co in courses:
            session.run("""
            MERGE (c:Course {id: $course_id})
            SET c.title = $name,
                c.user_id = $user_id,
                c.transit_type = $transit_type,
                c.duration_mins = $duration_mins,
                c.generated_content = $generated_content
            """, course_id=co["course_id"], name=co["name"], user_id=co["user_id"],
               transit_type=co["transit_type"], duration_mins=co["duration_mins"],
               generated_content=co.get("generated_content"))
            
            # Connect to stops
            heritage_ids = co.get("heritage_ids", [])
            for index, h_id in enumerate(heritage_ids):
                session.run("""
                MATCH (c:Course {id: $course_id})
                MATCH (h:Heritage {id: $heritage_id})
                MERGE (c)-[:VISITS {stop_order: $stop_order}]->(h)
                """, course_id=co["course_id"], heritage_id=h_id, stop_order=index + 1)
                
    print("Neo4j sync completed successfully.")

def main():
    creds = get_credentials()
    
    supabase_url = creds["SUPABASE_URL"]
    supabase_key = creds["SUPABASE_KEY"]
    neo4j_uri = creds["NEO4J_URI"]
    neo4j_user = creds["NEO4J_USERNAME"]
    neo4j_pass = creds["NEO4J_PASSWORD"]
    
    if not (supabase_url and supabase_key):
        print("Error: Supabase URL and Key are required. Set them in environment variables or mock_db.json settings.")
        return
        
    if not (neo4j_uri and neo4j_user and neo4j_pass):
        print("Error: Neo4j credentials are required. Set them in environment variables or mock_db.json settings.")
        return
        
    # Read mock data
    base_dir = os.path.dirname(os.path.abspath(__file__))
    mock_db_path = os.path.join(base_dir, "mock_db.json")
    with open(mock_db_path, "r", encoding="utf-8") as f:
        mock_data = json.load(f)
        
    print(f"Connecting to Supabase at: {supabase_url}")
    supabase_client = create_client(supabase_url, supabase_key)
    
    print(f"Connecting to Neo4j at: {neo4j_uri}")
    neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))
    
    # 1. Seed Supabase
    seed_supabase(supabase_client, mock_data)
    
    # 2. Sync to Neo4j
    sync_supabase_to_neo4j(supabase_client, neo4j_driver, mock_data)
    
    neo4j_driver.close()
    print("\n=== DATABASE SEED & SYNC COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
