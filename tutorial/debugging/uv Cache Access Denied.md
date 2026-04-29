---
tags: [debug, uv, windows, sandbox]
file: uv.lock
---

# uv Cache Access Denied

> `uv` could not access its Windows cache directory from the sandboxed command.

Related: [[gRPC Agent Decomposition]] · [[Home]]

---

## The Error

`error: Failed to initialize cache at C:\Users\jifat\AppData\Local\uv\cache`

`Caused by: failed to open file C:\Users\jifat\AppData\Local\uv\cache\sdists-v9\.git: Access is denied. (os error 5)`

## What Caused It

The command needed to read and write the user-level `uv` cache outside the workspace sandbox.

## How We Diagnosed It

`uv lock` and `uv run python -m grpc_tools.protoc` both failed before doing project work, and both failed at the same cache path.

## The Fix

The commands were rerun with permission to access the external `uv` cache. After that, `uv lock` resolved the new gRPC packages and `grpc_tools.protoc` generated the stubs.

> [!warning]
> This was an environment permission issue, not a Python or protobuf problem.
