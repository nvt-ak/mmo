"""
VideoScout — FastAPI Backend Entry Point
=========================================
Run:  python -m videoscout.main
API:   http://localhost:8000
Docs:  http://localhost:8000/docs

Old PyQt6 entry: main_qt.py (deprecated)
"""
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "videoscout.api_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
