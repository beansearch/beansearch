#!/usr/bin/env python3
"""One-off migration: crude single FTS table -> normalized episodes/segs + external-content FTS.

Reads an existing 3bs.db (single `transcripts` fts5 table) and writes a new,
much smaller database with:
  - episodes(id, title)           -- episode title stored once
  - segs(id, ep, start, end, text)
  - fts USING fts5(text, content='segs', content_rowid='id')  -- text indexed once
Sync triggers keep `fts` up to date on any write to `segs`.

Usage: python scripts/migrate_db.py [old.db] [new.db]
"""
import sqlite3
import sys

SCHEMA = """
CREATE TABLE episodes(id INTEGER PRIMARY KEY, title TEXT UNIQUE);
CREATE TABLE segs(
    id    INTEGER PRIMARY KEY,
    ep    INTEGER NOT NULL REFERENCES episodes(id),
    start REAL,
    end   REAL,
    text  TEXT
);
CREATE INDEX segs_ep_start ON segs(ep, start);
CREATE VIRTUAL TABLE fts USING fts5(text, content='segs', content_rowid='id');

CREATE TRIGGER segs_ai AFTER INSERT ON segs BEGIN
    INSERT INTO fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER segs_ad AFTER DELETE ON segs BEGIN
    INSERT INTO fts(fts, rowid, text) VALUES ('delete', old.id, old.text);
END;
CREATE TRIGGER segs_au AFTER UPDATE ON segs BEGIN
    INSERT INTO fts(fts, rowid, text) VALUES ('delete', old.id, old.text);
    INSERT INTO fts(rowid, text) VALUES (new.id, new.text);
END;
"""


def main() -> None:
    old_path = sys.argv[1] if len(sys.argv) > 1 else "3bs.db"
    new_path = sys.argv[2] if len(sys.argv) > 2 else "3bs.new.db"

    new = sqlite3.connect(new_path)
    new.executescript(SCHEMA)
    new.execute("ATTACH ? AS old", (old_path,))

    # Populate episodes (title stored once), then segments in original rowid
    # order so group_concat() context and search ordering stay stable.
    new.execute("INSERT INTO episodes(title) SELECT DISTINCT episode FROM old.transcripts")
    new.execute(
        """
        INSERT INTO segs(ep, start, end, text)
        SELECT e.id, t.start, t.end, t.text
        FROM old.transcripts t
        JOIN episodes e ON e.title = t.episode
        ORDER BY t.rowid
        """
    )
    new.execute("INSERT INTO fts(fts) VALUES('optimize')")
    new.commit()
    new.execute("DETACH old")
    new.execute("VACUUM")
    new.commit()

    n_eps = new.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    n_seg = new.execute("SELECT COUNT(*) FROM segs").fetchone()[0]
    new.close()
    print(f"Wrote {new_path}: {n_eps} episodes, {n_seg} segments")


if __name__ == "__main__":
    main()
