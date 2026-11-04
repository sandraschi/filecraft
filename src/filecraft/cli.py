"""FileCraft CLI: Headless verbs for filesystem analytics, hashing, search, and disk usage."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def list_path(
    target_dir: Path,
    recursive: bool = False,
    depth: int = 1,
) -> dict[str, Any]:
    """List directory contents with metadata and depth control."""
    if not target_dir.exists():
        raise FileNotFoundError(f"Path not found: {target_dir}")

    items: list[dict[str, Any]] = []

    def _scan(curr: Path, curr_depth: int):
        try:
            with os.scandir(curr) as it:
                for entry in it:
                    try:
                        stat = entry.stat(follow_symlinks=False)
                        is_dir = entry.is_dir(follow_symlinks=False)
                        items.append({
                            "name": entry.name,
                            "path": str(Path(entry.path).resolve()),
                            "is_dir": is_dir,
                            "size_bytes": stat.st_size if not is_dir else 0,
                            "modified": stat.st_mtime,
                        })
                        if is_dir and recursive and curr_depth < depth:
                            _scan(Path(entry.path), curr_depth + 1)
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass

    if target_dir.is_dir():
        _scan(target_dir, 1)
    else:
        stat = target_dir.stat()
        items.append({
            "name": target_dir.name,
            "path": str(target_dir.resolve()),
            "is_dir": False,
            "size_bytes": stat.st_size,
            "modified": stat.st_mtime,
        })

    return {
        "root": str(target_dir.resolve()),
        "total_items": len(items),
        "items": items,
    }


def hash_path(
    file_path: Path,
    algo: str = "sha256",
) -> dict[str, Any]:
    """Calculate cryptographic hash of a file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    algo_name = algo.lower()
    if algo_name not in hashlib.algorithms_available:
        raise ValueError(f"Unsupported hash algorithm: {algo}")

    h = hashlib.new(algo_name)
    size = 0
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
            size += len(chunk)

    return {
        "file": str(file_path.resolve()),
        "algorithm": algo_name,
        "hash": h.hexdigest(),
        "size_bytes": size,
    }


def grep_path(
    target_dir: Path,
    pattern: str,
    file_glob: str = "*",
    max_matches: int = 1000,
) -> dict[str, Any]:
    """Search for regex pattern across files matching glob pattern."""
    if not target_dir.exists():
        raise FileNotFoundError(f"Directory not found: {target_dir}")

    regex = re.compile(pattern, re.IGNORECASE)
    matches: list[dict[str, Any]] = []

    files_to_check: list[Path] = []
    if target_dir.is_file():
        files_to_check.append(target_dir)
    else:
        for root, _, filenames in os.walk(target_dir):
            for fn in filenames:
                if fnmatch.fnmatch(fn, file_glob):
                    files_to_check.append(Path(root) / fn)

    for p in files_to_check:
        if len(matches) >= max_matches:
            break
        try:
            # Quick binary check: read first 1024 bytes
            with p.open("rb") as f:
                head = f.read(1024)
                if b"\x00" in head:
                    continue  # skip binary

            with p.open("r", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, start=1):
                    if regex.search(line):
                        matches.append({
                            "file": str(p.resolve()),
                            "line_number": line_no,
                            "line": line.strip()[:300],
                        })
                        if len(matches) >= max_matches:
                            break
        except (PermissionError, OSError):
            continue

    return {
        "target": str(target_dir.resolve()),
        "pattern": pattern,
        "glob": file_glob,
        "match_count": len(matches),
        "matches": matches,
    }


def calculate_du(
    target_dir: Path,
    depth: int = 1,
) -> dict[str, Any]:
    """Calculate recursive disk usage for directory and subdirectories."""
    if not target_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {target_dir}")

    tree_usage: list[dict[str, Any]] = []

    def _dir_size(p: Path) -> int:
        total = 0
        try:
            with os.scandir(p) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False):
                            total += _dir_size(Path(entry.path))
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass
        return total

    total_dir_size = 0
    try:
        with os.scandir(target_dir) as it:
            for entry in it:
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    sz = _dir_size(Path(entry.path)) if is_dir else entry.stat(follow_symlinks=False).st_size
                    total_dir_size += sz
                    tree_usage.append({
                        "name": entry.name,
                        "path": str(Path(entry.path).resolve()),
                        "is_dir": is_dir,
                        "size_bytes": sz,
                    })
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass

    tree_usage.sort(key=lambda x: x["size_bytes"], reverse=True)

    return {
        "target": str(target_dir.resolve()),
        "total_bytes": total_dir_size,
        "entries": tree_usage[:100],
    }


def find_large_files(
    target_dir: Path,
    min_size_bytes: int = 1048576,  # 1MB default
    limit: int = 20,
) -> dict[str, Any]:
    """Find largest files exceeding threshold under target directory."""
    if not target_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {target_dir}")

    large_files: list[dict[str, Any]] = []

    for root, _, files in os.walk(target_dir):
        for f in files:
            p = Path(root) / f
            try:
                sz = p.stat(follow_symlinks=False).st_size
                if sz >= min_size_bytes:
                    large_files.append({
                        "file": str(p.resolve()),
                        "name": f,
                        "size_bytes": sz,
                    })
            except (PermissionError, OSError):
                continue

    large_files.sort(key=lambda x: x["size_bytes"], reverse=True)

    return {
        "target": str(target_dir.resolve()),
        "min_size_bytes": min_size_bytes,
        "count": len(large_files[:limit]),
        "files": large_files[:limit],
    }


def find_duplicates(
    target_dir: Path,
) -> dict[str, Any]:
    """Find identical duplicate files by comparing sizes then SHA-256 hashes."""
    if not target_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {target_dir}")

    by_size: dict[int, list[Path]] = {}
    for root, _, files in os.walk(target_dir):
        for f in files:
            p = Path(root) / f
            try:
                sz = p.stat(follow_symlinks=False).st_size
                if sz > 0:
                    by_size.setdefault(sz, []).append(p)
            except (PermissionError, OSError):
                continue

    duplicates: list[dict[str, Any]] = []
    for sz, paths in by_size.items():
        if len(paths) < 2:
            continue
        # Hash potential duplicates
        by_hash: dict[str, list[str]] = {}
        for p in paths:
            try:
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                by_hash.setdefault(h, []).append(str(p.resolve()))
            except Exception:
                continue

        for h, dups in by_hash.items():
            if len(dups) > 1:
                duplicates.append({
                    "hash": h,
                    "size_bytes": sz,
                    "paths": dups,
                })

    return {
        "target": str(target_dir.resolve()),
        "duplicate_groups": len(duplicates),
        "duplicates": duplicates,
    }


def extract_strings(
    file_path: Path,
    min_len: int = 4,
) -> dict[str, Any]:
    """Extract printable strings from file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    data = file_path.read_bytes()
    pattern = re.compile(rb"[\x20-\x7e\t\r\n]{" + str(min_len).encode() + rb",}")
    matches = [m.group().decode("latin-1") for m in pattern.finditer(data)]

    return {
        "file": str(file_path.resolve()),
        "count": len(matches),
        "strings": matches[:200],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filecraft",
        description="FileCraft: High-performance filesystem and disk usage workstation",
    )
    parser.add_argument("--version", action="version", version="filecraft 0.1.0")

    sub = parser.add_subparsers(dest="verb", required=True)

    # list
    p_ls = sub.add_parser("list", help="List directory contents")
    p_ls.add_argument("--path", required=True, type=Path, help="Directory path")
    p_ls.add_argument("--recursive", action="store_true", help="Recursive scan")
    p_ls.add_argument("--depth", type=int, default=1, help="Max depth")
    p_ls.add_argument("--json", action="store_true", help="Output JSON")

    # hash
    p_h = sub.add_parser("hash", help="Calculate cryptographic hash of file")
    p_h.add_argument("--path", required=True, type=Path, help="Target file")
    p_h.add_argument("--algo", default="sha256", help="Algorithm (sha256, md5, sha1)")
    p_h.add_argument("--json", action="store_true", help="Output JSON")

    # grep
    p_g = sub.add_parser("grep", help="Regex search text files")
    p_g.add_argument("--path", required=True, type=Path, help="Directory or file path")
    p_g.add_argument("--pattern", required=True, help="Regex pattern")
    p_g.add_argument("--glob", default="*", help="File glob filter")
    p_g.add_argument("--json", action="store_true", help="Output JSON")

    # du
    p_du = sub.add_parser("du", help="Recursive disk usage breakdown")
    p_du.add_argument("--path", required=True, type=Path, help="Target directory")
    p_du.add_argument("--depth", type=int, default=1, help="Depth limit")
    p_du.add_argument("--json", action="store_true", help="Output JSON")

    # find-large
    p_fl = sub.add_parser("find-large", help="Find largest files")
    p_fl.add_argument("--path", required=True, type=Path, help="Target directory")
    p_fl.add_argument("--min-size", type=int, default=1048576, help="Min size in bytes")
    p_fl.add_argument("--limit", type=int, default=20, help="Max items")
    p_fl.add_argument("--json", action="store_true", help="Output JSON")

    # find-dups
    p_fd = sub.add_parser("find-dups", help="Find duplicate files by content hash")
    p_fd.add_argument("--path", required=True, type=Path, help="Target directory")
    p_fd.add_argument("--json", action="store_true", help="Output JSON")

    # strings
    p_s = sub.add_parser("strings", help="Extract printable strings from file")
    p_s.add_argument("--file", required=True, type=Path, help="Target file")
    p_s.add_argument("--min-len", type=int, default=4, help="Min string length")
    p_s.add_argument("--json", action="store_true", help="Output JSON")

    # mcp
    sub.add_parser("mcp", help="Run FastMCP stdio server")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.verb == "list":
            res = list_path(args.path, recursive=args.recursive, depth=args.depth)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                for it in res["items"]:
                    kind = "<DIR>" if it["is_dir"] else f"{it['size_bytes']:>10}"
                    print(f"{kind}  {it['name']}")
            return 0

        if args.verb == "hash":
            res = hash_path(args.path, algo=args.algo)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"{res['algorithm']}: {res['hash']}  {res['file']}")
            return 0

        if args.verb == "grep":
            res = grep_path(args.path, pattern=args.pattern, file_glob=args.glob)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"Found {res['match_count']} matches for '{args.pattern}':")
                for m in res["matches"][:50]:
                    print(f"{m['file']}:{m['line_number']}: {m['line']}")
            return 0

        if args.verb == "du":
            res = calculate_du(args.path, depth=args.depth)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"Total Disk Usage for {res['target']}: {res['total_bytes']:,} bytes")
                for e in res["entries"][:30]:
                    print(f"{e['size_bytes']:>12,} bytes  {e['name']}")
            return 0

        if args.verb == "find-large":
            res = find_large_files(args.path, min_size_bytes=args.min_size, limit=args.limit)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"Top {len(res['files'])} files >= {res['min_size_bytes']:,} bytes:")
                for f in res["files"]:
                    print(f"{f['size_bytes']:>12,} bytes  {f['name']}")
            return 0

        if args.verb == "find-dups":
            res = find_duplicates(args.path)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"Found {res['duplicate_groups']} duplicate groups in {res['target']}:")
                for g in res["duplicates"]:
                    print(f"\nHash {g['hash']} ({g['size_bytes']} bytes):")
                    for p in g["paths"]:
                        print(f"  {p}")
            return 0

        if args.verb == "strings":
            res = extract_strings(args.file, min_len=args.min_len)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                for s in res["strings"]:
                    print(s)
            return 0

        if args.verb == "mcp":
            from .mcp_server import mcp

            mcp.run()
            return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
