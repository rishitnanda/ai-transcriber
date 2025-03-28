#python -m uvicorn main:app --reload
setx UVICORN_RELOAD_EXCLUDE "env/*"
uvicorn main:app --reload --workers 1