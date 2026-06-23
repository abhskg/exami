import logging
import pytest
from fastapi import APIRouter
from app.main import app

# Register temporary test routes directly on the FastAPI app instance for testing
router = APIRouter(prefix="/api/test-logging-exception", tags=["test-logging-exception"])

@router.get("/error")
def raise_unhandled_error():
    raise ValueError("Simulated unhandled exception")

@router.get("/http-error")
def raise_http_error():
    from fastapi import HTTPException
    raise HTTPException(status_code=400, detail="Simulated client error")

app.include_router(router)

def test_global_exception_handler_unhandled(client, caplog):
    """Verify that unhandled exceptions are caught by global handler, return 500, and are logged."""
    with caplog.at_level(logging.ERROR):
        response = client.get("/api/test-logging-exception/error")
            
    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected error occurred. Please try again later."}
    
    # Assert that the error traceback is logged
    log_messages = [record.message for record in caplog.records]
    assert any("Unhandled exception occurred while processing GET /api/test-logging-exception/error" in msg for msg in log_messages)

def test_global_exception_handler_http(client, caplog):
    """Verify that HTTPExceptions are logged at warning level and return correct status code/payload."""
    with caplog.at_level(logging.WARNING):
        response = client.get("/api/test-logging-exception/http-error")
        
    assert response.status_code == 400
    assert response.json() == {"detail": "Simulated client error"}
    
    # Assert that warning log is recorded
    log_messages = [record.message for record in caplog.records]
    assert any("HTTP exception on GET /api/test-logging-exception/http-error: status_code=400 detail=Simulated client error" in msg for msg in log_messages)

def test_request_logging_middleware(client, caplog):
    """Verify that the middleware logs incoming and completed requests."""
    with caplog.at_level(logging.INFO):
        # Hit the /health endpoint
        response = client.get("/health")
        
    assert response.status_code == 200
    
    log_messages = [record.message for record in caplog.records]
    assert any("Incoming request: GET /health" in msg for msg in log_messages)
    assert any("Completed request: GET /health - Status 200" in msg for msg in log_messages)
