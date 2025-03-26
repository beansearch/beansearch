#!/usr/bin/env python3
# import tempfile
# import subprocess
# from pyannote.audio import Pipeline
# import torch


# # Convert MP3 to 16kHz mono WAV using ffmpeg
# def convert_mp3_to_wav(mp3_path):
#     wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
#     subprocess.run([
#         "ffmpeg", "-y", "-i", mp3_path,
#         "-ac", "1", "-ar", "16000",
#         wav_file.name
#     ], check=True)
#     return wav_file.name

# # Convert and run diarization
# mp3_file = "test.mp3"  # '20250319 - Three Bean Salad - Gardening ad-free version.mp3'
# wav_file = convert_mp3_to_wav(mp3_file)

# wav_file = "/tmp/tmpzxgt5x5i.wav"

# pipeline = Pipeline.from_pretrained(
#     "pyannote/speaker-diarization-3.1",
#     use_auth_token="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"
# )


# import torch
# pipeline.to(torch.device("cuda"))

# # apply pretrained pipeline
# diarization = pipeline(wav_file)

# for turn, _, speaker in diarization.itertracks(yield_label=True):
#     print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")

from typing import List, Dict, Any, Optional

import sys
sys.path.append("..")
from app import get_db



def assign_speakers(whisper_segments, diarization):
    speaker_segments = []
    for ws in whisper_segments:
        match=False
        mid = (ws['start'] + ws['end']) / 2
        # print(ws['text'])
        for d in diarization:
            if float(d['start']) <= mid <= float(d['end']):
                match=True
                break

        if not match:
            print(ws['start'], ws['end'], ws['text'])
                

                # speaker_segments.append({
                #     "start": ws['start'],
                #     "end": ws['end'],
                #     "text": ws['text'],
                #     "speaker": d['speaker']
                # })
    # return speaker_segments

with get_db() as conn:
    cursor = conn.execute(
        """
        SELECT * FROM
        transcripts WHERE episode = ?
        ORDER BY start ASC;
        """,
        ('20250319 - Three Bean Salad - Gardening ad-free version',),
    )

whisper_segments = [dict(row) for row in cursor.fetchall()]

diarization = []
with open('/tmp/di') as f:
    for d in f.readlines():
        start, stop, speaker = d.split(' ')
        start = start.replace('start=', '')
        stop = stop.replace('stop=', '')
        speaker = speaker.replace('speaker_', '')

        diarization.append({
            'start': float(start.replace("s","")),
            'end': float(stop.replace("s","")),
            'speaker': speaker.replace("\n", "")
        })

from pprint import pprint
assigned = assign_speakers(whisper_segments, diarization)
# for line in assigned:

# segments = assign_speakers(result["segments"], diarization)