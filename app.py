#!/usr/bin/env python3
from flask import Flask, Response, request, jsonify, send_from_directory
import sqlite3
from flask_cors import CORS
import json
import subprocess

app = Flask(__name__, static_folder="static")
CORS(app)

DB_PATH = "3bs.db"


def get_db():
    # I attempted to be clever and reuse the DB connection, but flask
    # doesn't want to share it between requests. So *shrug*.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def fts5_escaped_query(input):
    # Sigh. This horrible mangling is need to make searching an fts5
    # table with apostrophes possible. Note how it needs both the
    # double and single quotes added.
    #   wouldn't --> "wouldn''t"
    a = [
        f'"{word.replace("'", "''")}"' if "'" in word else word
        for word in input.split()
    ]
    # print(a)
    return " ".join(a)


@app.route("/")
def serve_frontend():
    return send_from_directory("static", "index.html")


@app.route("/search", methods=["GET"])
def search():
    """Do a full-text-search for the given query string."""
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])

    conn = get_db()
    cursor = conn.execute(
        """
        SELECT episode, start, end, text FROM
        transcripts WHERE text MATCH ?
        ORDER BY episode ASC;
        """,
        (fts5_escaped_query(query),),
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(results)


@app.route("/context", methods=["GET"])
def context():
    """For a provided episode and timestamp, return extra context around it."""
    episode = request.args.get("e", "").strip()
    start = request.args.get("s", "").strip()
    start = float(start)

    if not episode:
        return jsonify([])

    conn = get_db()
    cursor = conn.execute(
        """
        SELECT '...' || group_concat(text, ' ') || ' ...' AS context 
        FROM transcripts 
        WHERE episode = ? 
        AND start > (? - 30) 
        AND end < (? + 30);
    """,
        (episode, start, start),
    )
    results = cursor.fetchone()
    conn.close()
    return jsonify({"context": results[0]})


@app.route("/test", methods=["GET"])
def test():
    """Run tests to ensure the backend & database is returning expected results."""
    tests = {
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
        response = app.test_client().get(f"/search?q={k}")
        r = [i["text"] for i in json.loads(response.data)]
        if r != v:
            msg = f"""<pre>Test failed!
            Query: {k}
            Expected: {v}
            Received: {r}
            </pre>
            """
            return Response(msg, status=500)

    return "All tests passed!"





@app.route("/info", methods=["GET"])
def info():
    with open('git_revision.txt', 'r') as f:
        rev = f.readline()
    return f"Current commit: {rev}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
