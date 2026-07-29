import os
import sys
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

# LangGraph imports
from langgraph.graph import StateGraph, END

# Import DB helper (ensure the root folder is accessible)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from storage.db_helper import SejongDBHelper

# 1. State Definition
class AgentState(TypedDict):
    query: str
    intent: Dict[str, Any]
    vector_results: List[Dict[str, Any]]
    graph_results: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    formatted_response: Dict[str, Any]

# Instantiate DB Helper
db = SejongDBHelper()

# ==========================================
# Graph Nodes Implementation
# ==========================================

def query_analysis_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 1: Analyze user query intent to identify category and historical era filters.
    """
    query = state.get("query", "").lower()
    intent = {
        "category": None,
        "era": None,
        "is_course": "코스" in query or "여행" in query or "추천" in query
    }
    
    # Simple rule-based intent parsing (fallback / mock LLM)
    if "유형문화재" in query or "문화재" in query:
        intent["category"] = "유형문화재"
    elif "기념물" in query or "은행나무" in query:
        intent["category"] = "기념물"
    elif "문화재자료" in query or "정자" in query:
        intent["category"] = "문화재자료"
    elif "현대" in query or "명소" in query or "호수" in query or "휴양림" in query:
        intent["category"] = "현대명소"
        
    if "조선" in query:
        intent["era"] = "조선시대"
    elif "고려" in query:
        intent["era"] = "고려시대"
    elif "현대" in query:
        intent["era"] = "현대"
        
    return {"intent": intent}


def vector_search_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2: Perform vector semantic search (simulated via db search).
    """
    query = state.get("query", "")
    intent = state.get("intent", {})
    
    # Retrieve candidates matching text and category
    vector_results = db.search_heritage(
        query=query if not intent.get("category") else None,
        category=intent.get("category")
    )
    
    # If no results found, perform broad search
    if not vector_results:
        vector_results = db.search_heritage(query=query)
        
    return {"vector_results": vector_results}


def graph_lookup_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 3: Fetch graph-connected neighbors for spatial and theme relationships (simulating Neo4j).
    """
    vector_results = state.get("vector_results", [])
    graph_results = []
    
    # For each candidate from vector search, find nearby connections
    seen_ids = set()
    for item in vector_results:
        heritage_id = item.get("id")
        if heritage_id:
            nearby = db.get_nearby_recommendations(heritage_id, limit=2)
            for n in nearby:
                neighbor = n["heritage"]
                n_id = neighbor["id"]
                if n_id not in seen_ids and n_id != heritage_id:
                    seen_ids.add(n_id)
                    graph_results.append({
                        "source_heritage": item["name"],
                        "target_heritage": neighbor,
                        "distance_km": n["distance_km"],
                        "travel_time_mins": n["travel_time_mins"]
                    })
                    
    return {"graph_results": graph_results}


def generate_recommendations_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 4: Core reasoning node. Generates recommendation details.
    Combines vector search and graph-related paths.
    """
    query = state.get("query", "")
    intent = state.get("intent", {})
    vector_results = state.get("vector_results", [])
    graph_results = state.get("graph_results", [])
    
    recommendations = []
    
    # Check if we should call Gemini API
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if google_api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.prompts import ChatPromptTemplate
            
            # Setup Gemini model
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_api_key)
            
            context = "\n".join([
                f"- {h['name']} ({h['category']}): {h['description']}" 
                for h in vector_results[:3]
            ])
            
            graph_context = "\n".join([
                f"- {g['source_heritage']} -> {g['target_heritage']['name']} (거리: {g['distance_km']}km, 시간: {g['travel_time_mins']}분)" 
                for g in graph_results[:3]
            ])
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "당신은 세종시 문화유산 전문 해설사 AI입니다. 제공된 후보 유산 정보와 장소 간 경로 데이터를 활용하여 사용자의 질문에 답변하고 여행 코스 또는 장소를 상세히 추천해 주세요. '생각할 거리'(역사적 가치, 감상 포인트 등)도 한 문장 포함해 주세요."),
                ("human", "질문: {query}\n\n[검색된 문화유산]\n{context}\n\n[장소 간 근접 경로 정보]\n{graph_context}")
            ])
            
            chain = prompt | llm
            response = chain.invoke({
                "query": query,
                "context": context,
                "graph_context": graph_context
            })
            
            # Formulate result structure from LLM content
            recommendations.append({
                "source": "Gemini Engine",
                "content": response.content,
                "candidates": [h["name"] for h in vector_results[:3]]
            })
            return {"recommendations": recommendations}
            
        except Exception as e:
            # Fallback to local rule engine if LLM fails
            print(f"Gemini API invocation failed: {e}. Falling back to rule-based generation.")
            
    # Rule-Based AI Engine Fallback (Deterministic, robust for offline testing)
    content = ""
    candidates = [h for h in vector_results[:3]]
    
    if intent.get("is_course"):
        content += f"사용자님의 질문 '{query}'에 맞춰 최적의 세종시 여행 코스를 생성했습니다.\n\n"
        if len(candidates) >= 2:
            content += "◆ 추천 경로:\n"
            route_names = [c["name"] for c in candidates]
            content += " -> ".join(route_names) + "\n\n"
            
            # Add routing details from graph connections if available
            connections_desc = []
            for g in graph_results:
                connections_desc.append(
                    f"- {g['source_heritage']}에서 {g['target_heritage']['name']}까지는 약 {g['distance_km']}km 이며 이동 시간은 약 {g['travel_time_mins']}분 소요됩니다."
                )
            if connections_desc:
                content += "◆ 이동 정보:\n" + "\n".join(connections_desc) + "\n\n"
        else:
            content += f"충분한 문화유산이 검색되지 않아 '{candidates[0]['name'] if candidates else '목록'}' 중심의 단일 방문을 추천합니다.\n\n"
            
        content += "◆ 생각할 거리 (생각해 볼 질문):\n"
        content += "\"우리가 세종시의 고즈넉한 옛 사찰과 역사공원을 걸을 때, 과거 유학자들과 성현들이 바랐던 이상적인 국가는 어떤 모습이었을까요?\"\n"
    else:
        content += f"사용자님께서 찾으시는 세종시 문화유산 상세 정보와 추천 명소입니다.\n\n"
        for h in candidates:
            content += f"■ {h['name']} ({h['category']})\n"
            content += f" - 주소: {h['address']}\n"
            content += f" - 상세설명: {h['description']}\n\n"
            
        content += "◆ 생각할 거리:\n"
        content += f"\"{candidates[0]['name'] if candidates else '문화유산'}이 수백 년간 한자리에서 전해 내려오며 현대 도심에 주는 친환경적 휴식의 가치는 무엇인지 고민해 보세요.\"\n"
        
    recommendations.append({
        "source": "Local Agent Engine",
        "content": content,
        "candidates": [h["name"] for h in candidates]
    })
    
    return {"recommendations": recommendations}


def format_response_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 5: Package results into standardized API format.
    """
    query = state.get("query", "")
    recommendations = state.get("recommendations", [])
    vector_results = state.get("vector_results", [])
    graph_results = state.get("graph_results", [])
    
    formatted_response = {
        "status": "success",
        "query": query,
        "recommendation": recommendations[0] if recommendations else {},
        "metadata": {
            "searched_candidates_count": len(vector_results),
            "graph_paths_count": len(graph_results),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    # If the user asked for a course, structure the course stops
    if state.get("intent", {}).get("is_course"):
        formatted_response["course_stops"] = [
            {
                "stop_order": idx + 1,
                "id": h["id"],
                "name": h["name"],
                "address": h["address"],
                "latitude": h.get("latitude"),
                "longitude": h.get("longitude")
            }
            for idx, h in enumerate(vector_results[:4])
        ]
        
    return {"formatted_response": formatted_response}

# ==========================================
# LangGraph Workflow Construction
# ==========================================

workflow = StateGraph(AgentState)

# Register nodes
workflow.add_node("query_analysis", query_analysis_node)
workflow.add_node("vector_search", vector_search_node)
workflow.add_node("graph_lookup", graph_lookup_node)
workflow.add_node("generate_recommendations", generate_recommendations_node)
workflow.add_node("format_response", format_response_node)

# Set edges
workflow.set_entry_point("query_analysis")
workflow.add_edge("query_analysis", "vector_search")
workflow.add_edge("vector_search", "graph_lookup")
workflow.add_edge("graph_lookup", "generate_recommendations")
workflow.add_edge("generate_recommendations", "format_response")
workflow.add_edge("format_response", END)

# Compile graph
agent_app = workflow.compile()

def run_agent(query_text: str) -> Dict[str, Any]:
    """Runs the full compiled workflow with the input query."""
    initial_state = {
        "query": query_text,
        "intent": {},
        "vector_results": [],
        "graph_results": [],
        "recommendations": [],
        "formatted_response": {}
    }
    result = agent_app.invoke(initial_state)
    return result.get("formatted_response", {})
