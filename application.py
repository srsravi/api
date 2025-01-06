from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from project.routes.api import router as api_router
from project.common.utility import Utility
from project.constant.status_constant import SUCCESS, FAIL
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import List, Dict, Any
from fastapi.responses import JSONResponse
import re
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from time import time
from typing import Dict
from collections import defaultdict

import pkgutil
import sys
import importlib

# Workaround for Python 3.12 where 'ImpImporter' is removed
if not hasattr(pkgutil, 'ImpImporter'):
    sys.modules['pkgutil'].ImpImporter = importlib.machinery.FileFinder

# This way all the tables can be created in database but cannot be updated for that use alembic migrations
# user.Base.metadata.create_all(bind=engine)
# Settings
REQUEST_LIMIT = 4  # Max number of requests allowed
TIME_PERIOD = 60  # Time period in seconds
# In-memory storage for rate limiting
request_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "time": time()})

app = FastAPI(title="TFS APP", description="TFS",version="1.0")
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, limit: int = REQUEST_LIMIT, period: int = TIME_PERIOD):
        super().__init__(app)
        self.limit = limit
        self.period = period

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time()
        client_data = request_counts[client_ip]

        # Reset the count if the time period has passed
        if current_time - client_data["time"] > self.period:
            client_data["count"] = 0
            client_data["time"] = current_time

        # Increment request count
        client_data["count"] += 1

        # Check if the limit has been exceeded
        if client_data["count"] > self.limit:
            #raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
            return JSONResponse({"status":422,"message":f'Your access is excedeed {client_ip}=={client_data["count"]}',"errors":"dhgdhg","code":"INPUT_VALIDATION_ERROR"},status_code=422)
        response = await call_next(request)
        return response

# Add middleware to the FastAPI app
#app.add_middleware(RateLimitMiddleware)

# Custom error response format
def format_error_details(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    formatted_errors = {}
    for error in errors:
        loc = "->".join(str(i) for i in error["loc"])
        print(loc)
        loc = loc.replace("body->","")
        context = error.get("ctx", {})
        reason =context.get("reason",[])
        formatted_errors[str(loc)] = {
            "message": re.sub(re.escape("value error, "), '', error["msg"], flags=re.IGNORECASE) ,
            "input": error.get("input", ''),
            #"context": context, #error.get("ctx", {})
            "reason":str(reason)
        }
    return formatted_errors

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = format_error_details(exc.errors())
    
    return JSONResponse({
        "status":422,
        "message":"Validation Error",
        "errors":formatted_errors,
        "code":"INPUT_VALIDATION_ERROR"

    },status_code=422)

origins = ["*","http://192.168.0.143:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
#9989678268
class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # default to 10MB
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        # Get the request body and check its size
        body = await request.body()
        if len(body) > self.max_size:
            return JSONResponse(
                content={"detail": "Request Entity Too Large"},
                status_code=413,
            )
        # Continue with the request processing
        return await call_next(request)

# Add the middleware with a size limit of 50 MB
app.add_middleware(BodySizeLimitMiddleware, max_size=500 * 1024 * 1024)

@app.get("/")
def read_root():
    try:
        return Utility.json_response(status=SUCCESS, message="Welcome to M-Remitence",
                                     error=[], data={})
    except Exception as E:
        print(E)
        return Utility.json_response(status=FAIL, message="Something went wrong", error=[], data={})


@app.get("/media/images/{image}")
def images( image: str):
    file_location = f"project/media/images/{image}"
    return FileResponse(file_location)

# if __name__ == '__main__':
#     uvicorn.run("application:app", host='localhost', port=8000, log_level="debug", reload=True)
#     print("running")
