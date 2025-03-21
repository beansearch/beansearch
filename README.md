This is the code that runs `https://searchthebeanmachine.boats`, a search engine for transcripts of the Three Beans Salad podcast.

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
npx @tailwindcss/cli -o ./tailwind.css -m  # Add --watch during development for auto-rebuild
```

### Deployment
The site is run in a small `fly.io` container, built from the `Dockerfile`.
