from fastapi import FastAPI, UploadFile, File, WebSocket, Response, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import openai
import asyncio
from dotenv import load_dotenv
import os
from fastapi.staticfiles import StaticFiles
import time

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
    """ Serve the home page """
    print("Home route accessed ✅")
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="text/html")
    except Exception as e:
        print(f"Error loading index.html: {e}")
        return JSONResponse(content={"error": "Failed to load index.html"}, status_code=500)


# 📁 Upload route
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """ Upload file, transcribe it, and return the transcript ID """
    print("UPLOAD route hit! ✅")

    if not file:
        return JSONResponse(content={"error": "No file uploaded"}, status_code=400)

    audio_file = await file.read()
    print(f"Received file: {file.filename} of size {len(audio_file)} bytes")

    # Uploading to AssemblyAI
    headers = {"authorization": ASSEMBLYAI_KEY}

    try:
        upload_response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            files={"file": ("audio.mp3", audio_file, file.content_type)},
            verify=False  # ✅ Ignore SSL
        )

        upload_response.raise_for_status()

        audio_url = upload_response.json().get("upload_url")
        print(f"Uploaded to AssemblyAI: {audio_url}")

    except Exception as e:
        print(f"AssemblyAI upload failed ❌: {e}")
        return JSONResponse(content={"error": "Failed to upload file"}, status_code=500)

    # Start transcription
    try:
        transcribe_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json={"audio_url": audio_url},
            headers=headers,
            verify=False  # ✅ Ignore SSL
        )

        transcribe_response.raise_for_status()

        transcript_id = transcribe_response.json().get("id")
        print(f"Transcription ID: {transcript_id}")

        # Return transcript ID to the frontend
        return JSONResponse(content={"transcript_id": transcript_id}, status_code=200)

    except Exception as e:
        print(f"Transcription start failed ❌: {e}")
        return JSONResponse(content={"error": "Failed to start transcription"}, status_code=500)


# 🔥 STATUS CHECK ENDPOINT 🔥
@app.get("/status/")
async def get_status(transcript_id: str = Query(...)):
    """ Check transcription status by ID """
    headers = {"authorization": ASSEMBLYAI_KEY}

    print(f"Checking status for ID: {transcript_id} 🔍")

    try:
        while True:
            status_response = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers,
                verify=False  # ✅ Ignore SSL
            )

            if status_response.status_code != 200:
                print(f"Failed to fetch status ❌: {status_response.text}")
                return JSONResponse(content={"error": "Failed to fetch status"}, status_code=500)

            data = status_response.json()
            status = data.get("status")

            if status == "completed":
                transcript = data.get("text")
                print("Transcription completed ✅")

                # Summarize with GPT-4
                prompt = f"Summarize the following meeting transcript:\n{transcript}"

                try:
                    summary_response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are a helpful meeting assistant."},
                            {"role": "user", "content": prompt}
                        ]
                    )

                    summary = summary_response["choices"][0]["message"]["content"]
                    print("Summarization completed ✅")

                    return JSONResponse(
                        content={
                            "status": "completed",
                            "transcript": transcript,
                            "summary": summary
                        },
                        status_code=200
                    )

                except Exception as e:
                    print(f"GPT-4 summarization failed ❌: {e}")
                    return JSONResponse(
                        content={"status": "failed", "error": "Summarization error"},
                        status_code=500
                    )

            elif status == "failed":
                print("Transcription failed ❌")
                return JSONResponse(
                    content={"status": "failed", "error": data.get("error", "Unknown error")},
                    status_code=500
                )

            print("Transcription still processing 🔄")
            await asyncio.sleep(3)

    except Exception as e:
        print(f"Error in status check ❌: {e}")
        return JSONResponse(content={"error": "Failed to check status"}, status_code=500)
