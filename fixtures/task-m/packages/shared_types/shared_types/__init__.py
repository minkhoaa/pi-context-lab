from typing import TypedDict, Optional, Dict, Any


class RequestHeaders(TypedDict, total=False):
    authorization: str
    x_user_id: str
    x_tenant_id: str
    x_correlation_id: str


class ResponsePayload(TypedDict):
    status_code: int
    data: Dict[str, Any]
    error: Optional[str]
