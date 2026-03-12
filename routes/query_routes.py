from fastapi import APIRouter
from models.query_model import QueryRequest, QueryResponse
from services.llm_service import get_legal_response
from services.parser import parse_llm_output

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def handle_query(req: QueryRequest):
    raw_output = get_legal_response(req.query)
    parsed = parse_llm_output(raw_output)
    return parsed
