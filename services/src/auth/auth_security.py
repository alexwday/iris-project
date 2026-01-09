"""
Authentication and Security Module.

Provides token validation and PII detection middleware for the IRIS API.

Functions:
    is_route_eligible_for_pii: Check if route requires PII detection
    validate_token_with_service: Validate token against auth service
    perform_pii_detection: Perform PII detection on request payload
    validate_token: Main token validation dependency for FastAPI
    validate_pii: Perform PII validation on eligible routes
"""

import logging
from typing import Any, Dict, Union

import requests
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from classes.exceptions.pii_exception import PIIException
from config.config import Config

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30
PII_ELIGIBLE_ROUTES = ["/qa"]

security = HTTPBearer()
app_config = Config()


def is_route_eligible_for_pii(request: Request) -> bool:
    """
    Check if the request route is eligible for PII detection.

    Args:
        request: The incoming FastAPI request.

    Returns:
        True if the route requires PII detection, False otherwise.
    """
    return any(route in request.url.path for route in PII_ELIGIBLE_ROUTES)


def validate_token_with_service(
    validation_url: str, headers: Dict[str, str]
) -> Union[requests.Response, HTTPException]:
    """
    Validate the token by making a request to the token validation endpoint.

    Args:
        validation_url: URL of the token validation service.
        headers: HTTP headers including Authorization.

    Returns:
        Response object if successful, or HTTPException on error.

    Raises:
        HTTPException: If auth service returns 503 or validation fails.
    """
    try:
        response = requests.get(
            validation_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
        )
        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            logger.error("Auth service is unavailable (503 Service Unavailable)")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service temporarily unavailable. Please try again later.",
            )
        if not response.ok:
            logger.error("Token validation failed: %s", response.json())
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("detail", "Token validation failed"),
            )
        logger.info("Token validation successful: %s", response.json())
        return response

    except requests.RequestException as req_error:
        logger.error("Auth service request error: %s", req_error)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_message": "Auth service failed due to an internal error."},
        )


def perform_pii_detection(
    pii_url: str, request_payload: Dict[str, Any], pii_headers: Dict[str, str]
) -> Union[requests.Response, HTTPException]:
    """
    Perform PII detection by making a request to the PII service endpoint.

    Args:
        pii_url: URL of the PII detection service.
        request_payload: The request payload containing the question.
        pii_headers: HTTP headers for the PII request.

    Returns:
        Response object if successful, or HTTPException on error.

    Raises:
        HTTPException: If PII service returns 503.
    """
    pii_payload = {
        "question": request_payload.get("question"),
        "excludes": app_config.pii_excludes,
        "lang": request_payload.get("lang"),
        "service": request_payload.get("service", "IRIS"),
    }

    try:
        analyzer_response = requests.post(
            url=pii_url,
            json=pii_payload,
            headers=pii_headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if analyzer_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            logger.error("PII service is unavailable (503 Service Unavailable)")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PII service temporarily unavailable. Please try again later.",
            )
        if analyzer_response.ok:
            logger.info("No PII detected: %s", analyzer_response.status_code)
        else:
            logger.error("PII Found: %s", analyzer_response.json())

        return analyzer_response

    except requests.RequestException as pii_error:
        logger.error("PII detection request error: %s", pii_error)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_message": "PII detection failed due to an internal error."},
        )


async def validate_token(
    request: Request, token: str = Depends(security)
) -> Union[requests.Response, JSONResponse]:
    """
    Validate the provided token and optionally perform PII detection.

    This is the main authentication dependency for FastAPI routes.

    Args:
        request: The incoming FastAPI request.
        token: Bearer token extracted by HTTPBearer security.

    Returns:
        Token validation response or PII detection response.

    Raises:
        HTTPException: If token validation fails.
        PIIException: If PII is detected in the request.
    """
    validation_url = app_config.token_validation_url
    headers = {"Authorization": f"Bearer {token.credentials}"}
    pii_headers = {"Content-Type": "application/json"}

    try:
        token_validation_response = validate_token_with_service(validation_url, headers)
        if token_validation_response.status_code != 200:
            response_json = token_validation_response.json()
            raise HTTPException(
                status_code=token_validation_response.status_code,
                detail=response_json.get("detail", "Token validation failed"),
            )

        logger.info("Token validation successful")
        request.state.token_data = token_validation_response.json()

        if is_route_eligible_for_pii(request):
            return await validate_pii(request, pii_headers)

        logger.info("PII detection skipped as the request route is not eligible")
        return token_validation_response

    except (ValueError, TypeError, KeyError, RuntimeError) as general_error:
        logger.error("Unexpected error: %s", general_error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during validation.",
        ) from general_error


async def validate_pii(
    request: Request, pii_headers: Dict[str, str]
) -> Union[requests.Response, HTTPException]:
    """
    Perform PII validation on eligible routes.

    Args:
        request: The incoming FastAPI request.
        pii_headers: HTTP headers for the PII request.

    Returns:
        PII detection response.

    Raises:
        PIIException: If PII is detected (403 response).
        HTTPException: If PII detection fails with other error.
    """
    pii_url = app_config.pii_service_url
    if request.headers.get("Content-Type") == "application/json":
        request_payload = await request.json()
        logger.info("Payload received in validate_pii: %s", request_payload)
    else:
        request_payload = dict(request.query_params)
        logger.info("Query parameters received in validate_pii: %s", request_payload)

    pii_detection_response = perform_pii_detection(
        pii_url, request_payload, pii_headers
    )

    if isinstance(pii_detection_response, HTTPException):
        return pii_detection_response

    if pii_detection_response.status_code == 403:
        pii_response_json = pii_detection_response.json()
        raise PIIException(
            status_code=pii_detection_response.status_code,
            detail=pii_response_json[0].get("error_message"),
        )

    if pii_detection_response.status_code != 200:
        pii_response_json = pii_detection_response.json()
        raise HTTPException(
            status_code=pii_detection_response.status_code,
            detail=pii_response_json[0].get("error_message"),
        )

    return pii_detection_response
