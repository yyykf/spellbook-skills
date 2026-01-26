#!/usr/bin/env python3
import json
import sys


def _normalize_position(position):
    if not position:
        return None
    file_path = position.get("new_path") or position.get("old_path")
    line = position.get("new_line") or position.get("old_line")
    if not file_path and not line:
        return None
    return {
        "file_path": file_path,
        "line": line,
    }


def main():
    data = json.load(sys.stdin)
    out = []
    for discussion in data:
        notes = discussion.get("notes", [])
        for note in notes:
            if note.get("system"):
                continue
            body = (note.get("body") or "").strip()
            author = (note.get("author") or {}).get("username")
            position = _normalize_position(note.get("position"))
            out.append({
                "author": author,
                "body": body,
                "position": position,
                "created_at": note.get("created_at"),
            })

    out.sort(key=lambda x: (x["position"] is None, x["position"].get("file_path") if x["position"] else "", x["position"].get("line") if x["position"] else 0))

    for item in out:
        if item["position"]:
            fp = item["position"].get("file_path") or "(unknown file)"
            line = item["position"].get("line") or "?"
            header = f"- {fp}:{line}"
        else:
            header = "- (general comment)"
        author = item.get("author") or "unknown"
        body = item.get("body") or ""
        print(f"{header} @{author}: {body}")


if __name__ == "__main__":
    try:
        main()
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        sys.exit(1)
