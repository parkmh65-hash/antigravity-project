import os
import time
import httpx
from .cache_manager import cached_api_response

# Base URL for KTO TourAPI 4.0
TOUR_API_URL = "http://apis.data.go.kr/B551011/KorService1"

@cached_api_response(ttl_seconds=3600)
def get_nearby_attractions(lat: float, lng: float, radius: int = 3000) -> list:
    """
    Fetches surrounding tourist spots within a radius (meters) using TourAPI.
    Uses TourAPI locationBasedList1 if key is present, otherwise returns generated local context mockups.
    """
    api_key = os.environ.get("TOURAPI_KEY")
    
    if api_key:
        try:
            url = f"{TOUR_API_URL}/locationBasedList1"
            params = {
                "serviceKey": api_key,
                "numOfRows": 10,
                "pageNo": 1,
                "MobileOS": "ETC",
                "MobileApp": "SejongHeritage",
                "_type": "json",
                "listYN": "Y",
                "arrange": "A",
                "mapX": lng, # TourAPI uses mapX for longitude
                "mapY": lat, # TourAPI uses mapY for latitude
                "radius": radius
            }
            
            response = httpx.get(url, params=params, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                body = data.get("response", {}).get("body", {})
                items = body.get("items", {})
                if items and "item" in items:
                    item_list = items["item"]
                    if not isinstance(item_list, list):
                        item_list = [item_list]
                        
                    formatted_items = []
                    for i in item_list:
                        formatted_items.append({
                            "name": i.get("title"),
                            "address": i.get("addr1"),
                            "image_url": i.get("firstimage") or "/static/images/default_spot.jpg",
                            "distance_meters": int(float(i.get("dist", 0))),
                            "content_type": "관광지",
                            "coordinates": {
                                "latitude": float(i.get("mapy", 0)),
                                "longitude": float(i.get("mapx", 0))
                            }
                        })
                    return formatted_items
        except Exception as e:
            print(f"TourAPI call failed: {e}. Using fallback generator.")
            
    # --- Contextual Fallback Mock Generator ---
    # Simulate network latency (100ms delay)
    time.sleep(0.10)
    # Generate spots near the target coordinates (Sejong areas)
    spots = []
    
    # Check if coords are in Northern Sejong (Jochiwon/ 전의면 - Lat > 36.55)
    if lat > 36.55:
        spots = [
            {
                "name": "조치원 전통시장 먹거리길",
                "address": "세종특별자치시 조치원읍 정리 12",
                "image_url": "/static/images/default_spot.jpg",
                "distance_meters": 1200,
                "content_type": "음식점",
                "coordinates": {"latitude": lat - 0.005, "longitude": lng + 0.003}
            },
            {
                "name": "비암사 등산 탐방로",
                "address": "세종특별자치시 전의면 비암사길 137",
                "image_url": "/static/images/default_spot.jpg",
                "distance_meters": 450,
                "content_type": "자연관광",
                "coordinates": {"latitude": lat + 0.002, "longitude": lng - 0.001}
            },
            {
                "name": "전의 왕의 물 테마공원",
                "address": "세종특별자치시 전의면 관정리",
                "image_url": "/static/images/default_spot.jpg",
                "distance_meters": 2300,
                "content_type": "관광명소",
                "coordinates": {"latitude": lat - 0.012, "longitude": lng + 0.008}
            }
        ]
    else:
        # Southern Sejong (Administrative town)
        spots = [
            {
                "name": "세종호수공원 무대섬",
                "address": "세종특별자치시 다솜로 216",
                "image_url": "/static/images/default_spot.jpg",
                "distance_meters": 850,
                "content_type": "문화시설",
                "coordinates": {"latitude": lat + 0.003, "longitude": lng + 0.004}
            },
            {
                "name": "국립세종수목원 사계절온실",
                "address": "세종특별자치시 수목원로 136",
                "image_url": "/static/images/default_spot.jpg",
                "distance_meters": 1600,
                "content_type": "관광지",
                "coordinates": {"latitude": lat - 0.004, "longitude": lng + 0.007}
            },
            {
                "name": "금강 수변 상가 카페거리",
                "address": "세종특별자치시 보람동 시청대로",
                "image_url": "/static/images/default_spot.jpg",
                "distance_meters": 1100,
                "content_type": "음식점",
                "coordinates": {"latitude": lat - 0.006, "longitude": lng - 0.002}
            }
        ]
        
    return spots
