#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
import sqlite3
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

DB_PATH = "3bs.db"


def fts5_escaped_query(input):
    # Sigh. This horrible mangling is need to make searching an fts5 table with apostrophes possible.
    #   wouldn't --> "wouldn''t"  (note it needs both the double and single quotes added).
    return f'"{input.replace("'", "''")}"'


@app.route("/")
def serve_frontend():
    return send_from_directory("static", "index.html")


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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

    if not episode or not start:
        return jsonify([])

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
