from app.main import app, create_app


if __name__ in {"__main__", "__mp_main__"}:
    import os

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
