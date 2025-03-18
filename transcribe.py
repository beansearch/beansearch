#!/usr/bin/env python3
import os
import whisper
import sqlite3
import signal
import sys
import fcntl

model_name = "turbo"
input_dir = "./episodes"
history_file = ".history"
db_file = "3bs.db"

model_loaded = False

def load_model():
    print(f"Loading model {model_name} (this might take a minute...)")
    model = whisper.load_model(model_name)
    model_loaded = True
    print("Model loaded.")

def lock_file(file_path):
    """Lock file to prevent duplicate processing."""
    lock_path = file_path + ".lock"
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)  # Lock file
        return lock_file
    except BlockingIOError:
        return None  # File is already locked

def unlock_file(lock_file):
    """Unlock file after processing."""
    fcntl.flock(lock_file, fcntl.LOCK_UN)
    lock_file.close()
    os.remove(lock_file.name)

def check_history(name):
    with open(history_file, "r", encoding="utf-8") as file:
        if name in [line.strip() for line in file]:
            return True
    return False


def append_history(name):
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"{name}\n")


if not os.path.exists(history_file):
    open(history_file, "w").close()

for file in os.listdir(input_dir):
    if file.endswith(".mp3"):
        if check_history(file):
            print(f"🆗 {file} done, skipping.")
            continue

        if not model_loaded:
            load_model()

        episode = file.replace(".mp3", "")
        mp3_path = os.path.join(input_dir, file)

        try:
            lock = lock_file(f"/tmp/{file}")
            if not lock:
                print(f"⚠️ Skipping {file}, already being processed.")
                continue
        except PermissionError:
            print(f"⚠️ Locking issue {file}, skipping.")
            continue

        try:
            print(f"📝 Transcribing {mp3_path}")
            result = model.transcribe(mp3_path)

            conn = sqlite3.connect(db_file)
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS transcripts USING fts5(episode, start, end, text)"
            )

            for segment in result["segments"]:
                conn.execute(
                    f'INSERT INTO transcripts (episode, start, end, text) VALUES ("{episode}", {segment["start"]}, {segment["end"]}, "{segment["text"]}")'
                )
            conn.commit()

            append_history(file)
            print(f"✅ {file}.")
        finally:
            unlock_file(lock)

print("Transcription complete.")
