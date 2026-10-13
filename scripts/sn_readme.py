#!/usr/bin/env python3
"""Regenerate the counts table in README.md (between the COUNTS markers)."""
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def counts():
    rows = {}
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "scripts"]
        md = [f for f in files if f.endswith(".md") and not (root == REPO and f == "README.md")]
        if not md:
            continue
        rel = os.path.relpath(root, REPO)
        parts = rel.split(os.sep)
        # group year sub-directories under their category
        key = "/".join(p for p in parts if not re.match(r"^(\d{4}|undated)$", p)) + "/"
        rows[key] = rows.get(key, 0) + len(md)
    return rows


def main():
    rows = counts()
    total = sum(rows.values())
    table = ["| Directory | Files |", "|---|---|"] + ["| `%s` | %d |" % (k, v) for k, v in sorted(rows.items())]
    table.append("| **Total** | **%d** |" % total)
    p = os.path.join(REPO, "README.md")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"<!-- COUNTS -->.*?<!-- /COUNTS -->", "<!-- COUNTS -->\n" + "\n".join(table) + "\n<!-- /COUNTS -->", s, flags=re.S)
    open(p, "w", encoding="utf-8").write(s)
    print("total", total)


if __name__ == "__main__":
    main()
