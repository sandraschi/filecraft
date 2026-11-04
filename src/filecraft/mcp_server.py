"""FastMCP server for FileCraft."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from .cli import (
    calculate_du,
    extract_strings as _extract_strings,
    find_duplicates,
    find_large_files,
    grep_path,
    hash_path,
    list_path,
)

mcp = FastMCP("FileCraft", version="0.1.0")


@mcp.tool()
def list_directory(path: str, recursive: bool = False, depth: int = 1) -> dict[str, Any]:
    """List files and folders with size, type, and modified time."""
    return list_path(Path(path), recursive=recursive, depth=depth)


@mcp.tool()
def hash_file(path: str, algo: str = "sha256") -> dict[str, Any]:
    """Calculate cryptographic hash of a file (sha256, md5, sha1)."""
    return hash_path(Path(path), algo=algo)


@mcp.tool()
def grep_files(path: str, pattern: str, glob: str = "*", max_matches: int = 500) -> dict[str, Any]:
    """Search for regex pattern across files under directory."""
    return grep_path(Path(path), pattern=pattern, file_glob=glob, max_matches=max_matches)


@mcp.tool()
def disk_usage(path: str, depth: int = 1) -> dict[str, Any]:
    """Calculate recursive disk usage breakdown for directory tree."""
    return calculate_du(Path(path), depth=depth)


@mcp.tool()
def find_large(path: str, min_size_bytes: int = 1048576, limit: int = 20) -> dict[str, Any]:
    """Find largest files exceeding threshold under target directory."""
    return find_large_files(Path(path), min_size_bytes=min_size_bytes, limit=limit)


@mcp.tool()
def find_dups(path: str) -> dict[str, Any]:
    """Find identical duplicate files by comparing byte sizes and cryptographic hashes."""
    return find_duplicates(Path(path))


@mcp.tool()
def extract_strings(file_path: str, min_len: int = 4) -> dict[str, Any]:
    """Extract printable strings from binary or text file."""
    return _extract_strings(Path(file_path), min_len=min_len)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
