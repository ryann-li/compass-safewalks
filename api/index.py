from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routes import auth, friends, fob, towers, map as map_routes, tower_ingest
from app.deps import error_response


app = FastAPI(title="Compass SafeWalks API", version="1.0.0")


@app.get("/")
def root():
    # Friendly root endpoint for Vercel root visits.
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):  # type: ignore[override]
    # Let HTTPException (including our error_response) pass through
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        raise exc

    # For unexpected errors, emit generic error shape
    body = {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
        }
    }
    return JSONResponse(status_code=500, content=body)


app.include_router(auth.router)
app.include_router(friends.router)
app.include_router(fob.router)
app.include_router(towers.router)
app.include_router(map_routes.router)
app.include_router(tower_ingest.router)

