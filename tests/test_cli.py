"""Unit and integration tests for FileCraft CLI verbs."""

import json
from pathlib import Path

import pytest
from filecraft import cli


def test_list_directory(tmp_path):
    (tmp_path / "file1.txt").write_text("Hello", encoding="utf-8")
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "file2.txt").write_text("World", encoding="utf-8")

    res = cli.list_path(tmp_path, recursive=True, depth=2)
    names = [it["name"] for it in res["items"]]
    assert "file1.txt" in names
    assert "subdir" in names
    assert "file2.txt" in names


def test_hash_file(tmp_path):
    target = tmp_path / "data.bin"
    target.write_bytes(b"FileCraft Deterministic Checksum Payload")

    res_sha = cli.hash_path(target, algo="sha256")
    assert len(res_sha["hash"]) == 64
    assert res_sha["size_bytes"] == len(b"FileCraft Deterministic Checksum Payload")

    res_md5 = cli.hash_path(target, algo="md5")
    assert len(res_md5["hash"]) == 32


def test_grep_files(tmp_path):
    f1 = tmp_path / "code1.py"
    f1.write_text("def find_me():\n    return 42\n", encoding="utf-8")

    f2 = tmp_path / "code2.py"
    f2.write_text("def other():\n    pass\n", encoding="utf-8")

    res = cli.grep_path(tmp_path, pattern=r"find_me", file_glob="*.py")
    assert res["match_count"] == 1
    assert res["matches"][0]["line_number"] == 1


def test_disk_usage(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"X" * 1000)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.bin").write_bytes(b"Y" * 2000)

    res = cli.calculate_du(tmp_path, depth=2)
    assert res["total_bytes"] == 3000


def test_find_large_files(tmp_path):
    (tmp_path / "small.txt").write_bytes(b"small")
    (tmp_path / "large.bin").write_bytes(b"Z" * 5000)

    res = cli.find_large_files(tmp_path, min_size_bytes=1000, limit=5)
    assert res["count"] == 1
    assert res["files"][0]["name"] == "large.bin"


def test_find_duplicates(tmp_path):
    content = b"Duplicate content payload 123456789"
    (tmp_path / "orig.txt").write_bytes(content)
    (tmp_path / "copy.txt").write_bytes(content)
    (tmp_path / "diff.txt").write_bytes(b"different")

    res = cli.find_duplicates(tmp_path)
    assert res["duplicate_groups"] == 1
    assert len(res["duplicates"][0]["paths"]) == 2


def test_extract_strings(tmp_path):
    target = tmp_path / "sample.bin"
    target.write_bytes(b"\x00\x00\x00EmbeddedFileCraftString\x00\x00")

    res = cli.extract_strings(target, min_len=4)
    assert any("EmbeddedFileCraftString" in s for s in res["strings"])


def test_cli_runner(tmp_path, capsys):
    f = tmp_path / "test.txt"
    f.write_text("FileCraft CLI Test String", encoding="utf-8")

    rc = cli.main(["hash", "--path", str(f), "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    h_json = json.loads(captured.out)
    assert "hash" in h_json

    rc = cli.main(["grep", "--path", str(tmp_path), "--pattern", "Test String", "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    g_json = json.loads(captured.out)
    assert g_json["match_count"] == 1
