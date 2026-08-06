import sys

# Windows consoles often default to a non-UTF-8 codepage, which breaks the
# emoji used throughout the log/print statements ported from the Rust server.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
