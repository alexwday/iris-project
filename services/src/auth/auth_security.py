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

    except HTTPException as e:
        logging.error(f"HTTPException occurred: {e.detail}")
        raise e
    except requests.RequestException as pii_error:
        logging.error(f" Auth service request error: {str(pii_error)}")
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_message":"Auth service failed due to an internal error."}
        )


def perform_pii_detection(pii_url: str, request_payload: dict, pii_headers: dict) -> JSONResponse:
    """
    Performs PII detection by making a request to the PII service endpoint.
    Returns the response data if successful, or a JSONResponse with an error message otherwise.
    """
    # Define the PII payload dynamically based on the request payload
    pii_payload = {
        "question": request_payload.get("question"),
        "excludes": app_config.pii_excludes,
        "lang": request_payload.get("lang"),
        "service": request_payload.get("service", "IRIS")
    }

    try:
        analyzer_response = requests.post(
            url=pii_url,
            json=pii_payload,
            headers=pii_headers
        )
        if analyzer_response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            logging.error("PII service is unavailable (503 Service Unavailable).")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PII service is temporarily unavailable. Please try again later."
            )
        elif analyzer_response.ok:
            logging.info(f"No PII: {analyzer_response}")
        else:
            analyzer_json = analyzer_response.json()
            logging.error(f"PII Found: {analyzer_json}")

        return analyzer_response

    except HTTPException as e:
        logging.error(f"HTTPException occurred: {e.detail}")
        raise e
    except requests.RequestException as pii_error:
        logging.error(f"PII detection request error: {str(pii_error)}")
        return HTTPException(
            status_code=500,
            detail={"error_message": "PII detection failed due to an internal error."}
        )


async def validate_token(request: Request, token: str = Depends(security)):
    """
    Validates the provided token and optionally performs PII detection if the route is eligible.
    """
    validation_url = app_config.token_validation_url
    headers = {"Authorization": f"Bearer {token.credentials}"}
    pii_headers = {"Content-Type": "application/json"}

    try:
        # Validate the token
        token_validation_response = validate_token_with_service(validation_url, headers)
        if token_validation_response.status_code != 200:
            response_json = token_validation_response.json()
            raise HTTPException(
                status_code=token_validation_response.status_code,
                detail=response_json.get("detail", "Token validation failed")
            )

        logging.info("Token validation successful.")
        request.state.token_data = token_validation_response.json()

        # Call validate_pii if route is eligible
        if is_route_eligible_for_pii(request):
            return await validate_pii(request, pii_headers)
        else:
            logging.info("PII detection skipped as the request route is not eligible.")
            return token_validation_response

    except PIIException as e:
        logging.error(f"HTTPException occurred: {e.detail}")
        raise e
    except HTTPException as e:
        logging.error(f"HTTPException occurred: {e.detail}")
        raise e
    except Exception  as general_error:
        logging.error(f"Unexpected error: {str(general_error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during validation."
        )

async def validate_pii(request: Request, pii_headers: dict):
    pii_url = app_config.pii_service_url
    if request.headers.get("Content-Type") == "application/json":
        request_payload = await request.json()
        logging.info(f"Payload received in validate_pii: {request_payload}")
    else:
        request_payload = dict(request.query_params)
        logging.info(f"Query parameters received in validate_pii: {request_payload}")

    pii_detection_response = perform_pii_detection(pii_url, request_payload, pii_headers)
    if not isinstance(pii_detection_response, HTTPException) and pii_detection_response.status_code == 403:
        pii_response_json = pii_detection_response.json()
        raise PIIException(
            status_code=pii_detection_response.status_code,
            detail=pii_response_json[0].get('error_message')
        )
    elif not isinstance(pii_detection_response, HTTPException) and pii_detection_response.status_code != 200:
        pii_response_json = pii_detection_response.json()
        raise HTTPException(
            status_code=pii_detection_response.status_code,
            detail=pii_response_json[0].get('error_message')
        )
    return pii_detection_response
