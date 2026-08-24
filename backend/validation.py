"""Validation error responses that never echo submitted sensitive values."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def sanitized_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = []
    for error in exc.errors():
        details.append(
            {
                "type": error.get("type", "validation_error"),
                "loc": list(error.get("loc", ())),
                "msg": error.get("msg", "输入不符合要求"),
            }
        )
    return JSONResponse(status_code=422, content={"detail": details})
