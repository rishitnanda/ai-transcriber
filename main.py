from fastapi import FastAPI, UploadFile, File, WebSocket, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import openai
import asyncio
from dotenv import load_dotenv
import os
from fastapi.staticfiles import StaticFiles

# Load environment variables
load_dotenv()
ASSEMBLYAI_KEY = os.getenv("ASSEMBLYAI_KEY")
openai.api_key = os.getenv("OPENAI_KEY")

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🏠 Home route
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), media_type="text/html")

# 📁 Upload route (fixing form submission)
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    audio_file = await file.read()

    # Uploading to AssemblyAI
    headers = {
        "authorization": ASSEMBLYAI_KEY
    }

    upload_response = requests.post(
        "https://api.assemblyai.com/v2/upload",
        headers=headers,
        files={"file": ("audio.mp3", audio_file, file.content_type)}  # Correct file upload format
    )

    upload_response.raise_for_status()

    audio_url = upload_response.json().get("upload_url")

    # Start transcription
    transcribe_response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json={"audio_url": audio_url},
        headers=headers
    )

    transcript_id = transcribe_response.json().get("id")

    # Polling for transcription status
    while True:
        status_response = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers
        )
        status = status_response.json()["status"]

        if status == "completed":
            transcript = status_response.json()["text"]
            break
        await asyncio.sleep(3)

    # Summarize with GPT-4
    prompt = f"Summarize the following meeting transcript:\n{transcript}"
    summary_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a helpful meeting assistant."},
                  {"role": "user", "content": prompt}]
    )

    summary = summary_response["choices"][0]["message"]["content"]

    return {
        "transcript": transcript,
        "summary": summary
    }
