import requests
import logging
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from classes.exceptions.pii_exception import PIIException
from config.config import Config

security = HTTPBearer()
app_config = Config()

PII_ELIGIBLE_ROUTES = ["/qa"]

def is_route_eligible_for_pii(request: Request) -> bool:
    """
    Checks if the request route is eligible for PII detection.
    """
    return any(route in request.url.path for route in PII_ELIGIBLE_ROUTES)

def validate_token_with_service(validation_url: str, headers: dict) -> dict:
    """
    Validates the token by making a request to the token validation endpoint.
    Returns the response data if successful, or a JSONResponse with an error message otherwise.
    """
    try:
        response = requests.get(validation_url, headers=headers)
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            logging.error("Auth service is unavailable (503 Service Unavailable).")
            raise HTTPException(
                status_code= status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service is temporarily unavailable. Please try again later."
            )
        elif not response.ok:
            logging.error(f"Token validation failed: {response.json()}")
            raise HTTPException(status_code=response.status_code, detail=response.json().get("detail", "Token validation failed"))
        logging.info(f"Token validation successful: {response.json()}")

        return response
