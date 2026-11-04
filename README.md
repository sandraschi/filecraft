# FileCraft

Filesystem, volume analytics, disk usage, and integrity workstation.

## Verbs
- `filecraft list --path <dir>`: Directory listing with file metadata and depth control
- `filecraft hash --path <file>`: Cryptographic hash calculation (sha256, md5, sha1)
- `filecraft grep --path <dir> --pattern <regex>`: High-speed regex search across text files
- `filecraft du --path <dir>`: Recursive disk usage breakdown and tree analysis
- `filecraft find-large --path <dir>`: Identify largest files exceeding size threshold
- `filecraft find-dups --path <dir>`: Duplicate file detection by byte size and hash
- `filecraft strings --file <bin>`: Extract printable strings from binary files
- `filecraft mcp`: FastMCP stdio server
