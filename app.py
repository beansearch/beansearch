#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
import sqlite3
from flask_cors import CORS

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
    return f'"{input.replace("'", "''")}"'


@app.route("/")
def serve_frontend():
    return send_from_directory("static", "index.html")


@app.route("/search", methods=["GET"])
def search():
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
