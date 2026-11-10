#!/usr/bin/env python3
import os
import sys
import traceback
import whisper
import sqlite3
import fcntl

model_name = "turbo"
input_dir = "./episodes"
history_file = ".history"
db_file = "3bs.db"

model_loaded = False


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

failed = []

for file in os.listdir(input_dir):
    if file.endswith(".mp3"):
        if check_history(file):
            print(f"🆗 {file} done, skipping.")
            continue

        if not model_loaded:
            print(f"Loading model {model_name} (this might take a minute...)")
            model = whisper.load_model(model_name)
            model_loaded = True
            print("Model loaded.")

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
            # Normalized schema: episode title stored once in `episodes`, segments
            # in `segs`, and an external-content fts5 index (`fts`) kept in sync by
            # triggers. See scripts/migrate_db.py for the full definition.
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS episodes(id INTEGER PRIMARY KEY, title TEXT UNIQUE);
                CREATE TABLE IF NOT EXISTS segs(
                    id    INTEGER PRIMARY KEY,
                    ep    INTEGER NOT NULL REFERENCES episodes(id),
                    start REAL,
                    end   REAL,
                    text  TEXT
                );
                CREATE INDEX IF NOT EXISTS segs_ep_start ON segs(ep, start);
                CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(text, content='segs', content_rowid='id');
                CREATE TRIGGER IF NOT EXISTS segs_ai AFTER INSERT ON segs BEGIN
                    INSERT INTO fts(rowid, text) VALUES (new.id, new.text);
                END;
                CREATE TRIGGER IF NOT EXISTS segs_ad AFTER DELETE ON segs BEGIN
                    INSERT INTO fts(fts, rowid, text) VALUES ('delete', old.id, old.text);
                END;
                CREATE TRIGGER IF NOT EXISTS segs_au AFTER UPDATE ON segs BEGIN
                    INSERT INTO fts(fts, rowid, text) VALUES ('delete', old.id, old.text);
                    INSERT INTO fts(rowid, text) VALUES (new.id, new.text);
                END;
                """
            )

            conn.execute(
                "INSERT OR IGNORE INTO episodes(title) VALUES (?)", (episode,)
            )
            ep_id = conn.execute(
                "SELECT id FROM episodes WHERE title = ?", (episode,)
            ).fetchone()[0]

            for segment in result["segments"]:
                conn.execute(
                    "INSERT INTO segs (ep, start, end, text) VALUES (?, ?, ?, ?)",
                    (ep_id, segment["start"], segment["end"], segment["text"]),
                )
            conn.commit()

            append_history(file)
            print(f"✅ {file}.")
        except Exception as e:
            failed.append(file)
            print(f"❌ Failed processing {file}: {type(e).__name__}: {e}")
            print(f"   episode: {episode!r}")
            try:
                print(f"   failing segment: {segment!r}")
            except NameError:
                pass
            traceback.print_exc()
        finally:
            unlock_file(lock)

print("Transcription complete.")

# Exit non-zero if any episode failed, so cron notices. Without this a
# half-failed run looks identical to a clean one.
if failed:
    print(f"{len(failed)} episode(s) failed: {', '.join(failed)}")
    sys.exit(1)
