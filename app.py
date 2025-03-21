#!/usr/bin/env python3
from flask import Flask, Response, request, jsonify, send_from_directory, abort
from werkzeug.test import TestResponse
import sqlite3
from flask_cors import CORS
import json
import os
from typing import List, Dict, Any, Optional

app: Flask = Flask(__name__, static_folder="static")
CORS(app)

DB_PATH: str = "3bs.db"


def get_db() -> sqlite3.Connection:
    # I attempted to be clever and reuse the DB connection, but flask
    # doesn't want to share it between requests. So *shrug*.
    conn: sqlite3.Connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def fts5_escaped_query(input: str) -> str:
    # Sigh. This horrible mangling is need to make searching an fts5
    # table with apostrophes possible. Note how it needs both the
    # double and single quotes added.
    #   wouldn't --> "wouldn''t"
    escaped_words: List[str] = [
        f'"{word.replace("'", "''")}"' if "'" in word else word
        for word in input.split()
    ]
    return " ".join(escaped_words)


@app.route("/")
def serve_frontend() -> Response:
    return send_from_directory("static", "index.html")


@app.route("/search", methods=["GET"])
def search() -> Response:
    """Do a full-text-search for the given query string."""
    query: str = request.args.get("q", "").strip()

    if not query:
        abort(400, description="Query parameter is required")

    with get_db() as conn:
        cursor: sqlite3.Cursor = conn.execute(
            """
            SELECT episode, start, end, text FROM
            transcripts WHERE text MATCH ?
            ORDER BY episode ASC;
            """,
            (fts5_escaped_query(query),),
        )
        results: List[Dict[str, Any]] = [dict(row) for row in cursor.fetchall()]
    return jsonify(results)


@app.route("/context", methods=["GET"])
def context() -> Response:
    """For a provided episode and timestamp, return extra context around it."""
    episode: str = request.args.get("e", "").strip()
    start: str = request.args.get("s", "").strip()

    if not episode:
        return jsonify([])

    start_float: float = float(start)

    conn: sqlite3.Connection = get_db()
    cursor: sqlite3.Cursor = conn.execute(
        """
        SELECT '...' || group_concat(text, ' ') || ' ...' AS context 
        FROM transcripts 
        WHERE episode = ? 
        AND start > (? - 30) 
        AND end < (? + 30);
        """,
        (episode, start_float, start_float),
    )
    results: Optional[sqlite3.Row] = cursor.fetchone()
    conn.close()

    return jsonify({"context": results[0] if results else ""})


@app.route("/test", methods=["GET"])
def test() -> Response:
    """Run tests to ensure the backend & database is returning expected results."""
    tests: Dict[str, List[str]] = {
        # Fuzzy matching (distant words, and reversed order), no special characters
        "dying genius": [
            " A bit like, on the positive side, a child genius, but who is dying.",
            " So there's a lot of a dying child genius.",
        ],
        # Fuzzy matching with an apostrophe which needs escaping.
        "wouldn't lightly": [" we wouldn't say this lightly,"],
        # This unquoted string should fuzzy match two results...
        "his family business": [
            " make it a family business yeah it'll be beans and sons with his many sons and it'll be so sad when",
            " in his family business",
        ],
        # ...but when quoted it should match exactly one.
        '"his family business"': [" in his family business"],
    }

    for k, v in tests.items():
        response: TestResponse = app.test_client().get(f"/search?q={k}")
        r: List[str] = [i["text"] for i in json.loads(response.data)]
        if r != v:
            msg: str = f"""<pre>Test failed!
            Query: {k}
            Expected: {v}
            Received: {r}
            </pre>
            """
            return Response(msg, status=500)

    return Response("All tests passed!")


@app.route("/info", methods=["GET"])
def info() -> str:
    """An envvar containing git rev info is set at build time by flyctl"""
    return "Current commit: " + os.environ.get("GIT_INFO", "unknown")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
