pip install fastapi uvicorn openai requests websockets starlette python-multipart python-dotenv

python -m uvicorn main:app --reload
#setx UVICORN_RELOAD_EXCLUDE "env/*"
#uvicorn main:app --reload --workers 1