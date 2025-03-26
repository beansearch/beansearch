#!/usr/bin/env python3
import os
import re

# import whisper
from faster_whisper import WhisperModel
import fcntl
from app import get_db

model_name = "turbo"
input_dir = "./episodes"
# history_file = ".history_faster"
db_file = "3bs_faster.db"

model_loaded = False

# The published date on some episodes is incorrect because they were added
# to Patreon a while after initial release. This is the list of corrections.
date_corrections = {
    "Purple": "20210629",
    "Posters": "20210427",
    "Lizards": "20210505",
    "Rome": "20210511",
    "Submarines": "20210519",
    "Bags": "20210526",
    "Asteroids": "20210601",
    "Sleep": "20210609",
    "Musical Instruments": "20210616",
    "Magic": "20210623",
    "The Titanic": "20211020",
    "Condiments": "20210818",
    "Romance": "20210825",
    "Dystopia": "20210901",
    "Buffets": "20210907",
    "Flags": "20210914",
    "Islands": "20210922",
    "Jeffreys": "20210929",
    "Pagans": "20211006",
    "Portraiture": "20211012",
    "Exercise": "20211201",
    "Immortality": "20211208",
    "Biscuits": "20211215",
    "Zombies": "20211222",
    "Elevators": "20220105",
    "Museums": "20220112",
    "Aliens": "20220119",
    "Spies": "20220126",
    "Dinosaurs": "20220302",
}


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


# def check_history(name):
#     with open(history_file, "r", encoding="utf-8") as file:
#         if name in [line.strip() for line in file]:
#             return True
#     return False


# def append_history(name):
#     with open(history_file, "a", encoding="utf-8") as f:
#         f.write(f"{name}\n")


def extract_title_metadata(filename):
    """Extract episode title and date from filename. Also corrects some dates.
    Input: "20220608 - Three Bean Salad - Prizes ad-free version.mp3"
    Output: ("20220608", "Prizes")
    """

    date, title = filename.split(" - ", 1)

    # Strip unnecessary text from title
    title = (
        title.replace(".mp3", "")
        .replace("ad-free version", "")
        .replace("Three Bean Salad -", "")
        .strip()
    )

    # Remove patterns like "S3 E12" from the title
    title = re.sub(r"S\d+ E\d+ - ", "", title)

    # Consult the date correction dictionary
    date = date_corrections.get(title, date)

    return date, title


def merge_segments(segments, pause_threshold=0.001):
    merged = []
    buffer = []
    last_end = 0.0

    for seg in segments:
        if seg.start - last_end > pause_threshold and buffer:
            merged.append(" ".join(buffer))
            buffer = []
        buffer.append(seg.text.strip())
        last_end = seg.end

    if buffer:
        merged.append(" ".join(buffer))
    return merged


if __name__ == "__main__":
    # Create history file if it doesn't exist
    # if not os.path.exists(history_file):
    #     open(history_file, "w").close()

    # Create database if it doesn't exist
    with get_db("rwc") as conn:
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS transcripts USING fts5(episode_id, start, end, text)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                date TEXT,
                transcribed BOOLEAN DEFAULT FALSE,
                UNIQUE(title, date)
            );
            """
        )
        conn.commit()

    # for file in os.listdir(input_dir):
    for file in ["20220330 - Three Bean Salad - Five Wednesday Month Alert.mp3"]:
        if file.endswith(".mp3"):
            date, episode_name = extract_title_metadata(file)

            # with get_db("rw") as conn:
            #     conn.execute(
            #         f"""
            #         INSERT INTO episodes (title, date)
            #         VALUES ("{episode_name}", "{date}") ON CONFLICT DO NOTHING
            #         """
            #     )
            #     conn.commit()
            #     res = conn.execute(
            #         f"""
            #         SELECT id, transcribed FROM episodes WHERE title = "{episode_name}" AND date = "{date}"
            #         """)
            #     episode_id, transcribed = list(res.fetchone())

            #     if transcribed:
            #         print(f"🆗 {file} already done, skipping.")
            #         continue

            if not model_loaded:
                print(f"Loading model {model_name} (this might take a minute...)")
                model = WhisperModel(model_name, device="cuda", compute_type="float16")
                model_loaded = True
                print("Model loaded.")


            try:
                lock = lock_file(f"/tmp/{file}")
                if not lock:
                    print(f"⚠️ Skipping {file}, already being processed.")
                    continue
            except PermissionError:
                print(f"⚠️ Locking issue {file}, skipping.")
                continue

            # try:

            mp3_path = os.path.join(input_dir, file)
            print(f"📝 Transcribing {mp3_path}")
            segments, info = model.transcribe(mp3_path)

            # with get_db("rw") as conn:
            #     for segment in segments:
            #         conn.execute(
            #             """
            #             INSERT INTO transcripts (episode_id, start, end, text)
            #             VALUES (?, ?, ?, ?)""",
            #             (episode_id, segment.start, segment.end, segment.text)
            #         )
            #     conn.execute("UPDATE episodes SET transcribed = TRUE WHERE id = ?", (episode_id,))
            #     conn.commit()
            # avg=[]
            # for segment in segments:
            #     avg.append(
            #         len(segment.text.split())
            #         )
            
            merged_sentences = merge_segments(segments)
            
            avg=[]
            for segment in merged_sentences:
                print(segment)
                avg.append(
                    len(segment.split())
                    )

            print(
                sum(avg)/len(avg),
            )

            from pprint import pprint
            pprint(merged_sentences)


            print(f"✅ {file}.")

            # finally:
            #     # unlock_file(lock)
            #     pass

    print("Transcription complete.")
