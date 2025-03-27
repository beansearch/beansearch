This is the code that runs https://searchthebeanmachine.boats, a search engine for transcripts of the Three Beans Salad podcast.

### Transcription
`transcribe.py` uses OpenAI's Whisper library to transcribe audio to text.

It stores the output into a sqlite database (`3bs.db`), using a `fts5` virtual table which provides full-text-search functionality.

The audio files are pre-fetched from a Patreon RSS feed; the code here does not cover this process. The audio files are not shared here for obvious copyright reasons. 

### Website
A python flask app (`app.py`) runs the backend service which queries the database. It also serves the static html & js (`static/index.html`) content to the browser.

#### CSS
CSS is handled by `tailwindcss`, to rebuild the stylesheet run:
```
cd static
npm install -D tailwindcss @tailwindcss/cli
npx @tailwindcss/cli -i ./style.css -o ./tailwind.css -m  # Add --watch during development for auto-rebuild
```

### Deployment
The site is run in a small `fly.io` container, built from the `Dockerfile`.

### Future Ideas
 - [ ] Add "last updated" details.
   - Shouldn't be too hard, the most recently added episode can be extract from the database or `.history` file.
 - [ ] Perma-links
   - So you can share links to search results.

 - [ ] Consider Whisper alternatives
   - A quick test suggests [faster-whisper](https://github.com/SYSTRAN/faster-whisper) is significantly faster at transcription. However it produces slightly different segments, which should be evaluated.
 - [ ] Link to playable episodes.
    - The problem is link to where? The RSS feed has links to the post on Patreon, however those will only work for Patreon members. That's not a big deal as the audio transcripts are only of the ad-free Patreon versions anyhow. However Patreon doesn't let you link to a particular timestamp in the way, say, youtube does (https://youtu.be/alN1ePd2mrg?t=10510). It would be great to jump to the timestamp the search result comes from.
 - [ ] Attribute speech to people (diarization).
   -  I've experimented with `pyannote.audio` (also as part of `whisperX`). Like some casual listeners, it too struggles to distinguish Ben & Mike.
 - [ ] Restructure the database
     -  The database schema is currently laughably crude. One table with just "episode title", "segment start", "segment end", "text". There's no unique columns, no IDs for episode or segment. Date is merged in with episode time, along with redundant info like the show name and "ad-free version". Having a dedicated "episodes" table would also help store metadata like URL.
