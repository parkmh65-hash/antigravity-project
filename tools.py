import os
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

@tool
def retrieve(query: str) -> list:
    """검색 쿼리를 바탕으로 벡터 데이터베이스(Supabase)에서 관련 정보를 검색합니다.

    Args:
        query: 검색할 쿼리 문자열
    """
    # Handle direct invocation with args dict
    if isinstance(query, dict):
        query_str = query.get("query", "")
    else:
        query_str = query

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if (not supabase_url or not supabase_key or 
        supabase_url == "your_supabase_url_here" or 
        supabase_key == "your_supabase_anon_key_here"):
        print("[WARNING] Supabase credentials are missing. Returning fallback mock results.")
        return [
            Document(
                page_content=f"'{query_str}'에 대한 가상 검색 결과: Supabase 설정이 필요합니다. RAG 시스템 구축을 위해 .env 파일에 올바른 SUPABASE_URL과 SUPABASE_KEY를 입력해주세요.",
                metadata={"source": "mock"}
            )
        ]

    try:
        supabase = create_client(supabase_url, supabase_key)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        vector_store = SupabaseVectorStore(
            client=supabase,
            embedding=embeddings,
            table_name="documents",
            query_name="match_documents"
        )
        
        docs = vector_store.similarity_search(query_str, k=3)
        return docs
    except Exception as e:
        print(f"[ERROR] Supabase search failure: {e}")
        return [
            Document(
                page_content=f"Supabase 검색 중 오류가 발생했습니다: {str(e)}",
                metadata={"source": "error"}
            )
        ]
