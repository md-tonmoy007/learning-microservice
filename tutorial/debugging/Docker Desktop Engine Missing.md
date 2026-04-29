---
tags: [debug, docker, windows]
file: docker-compose.yml
---

# Docker Desktop Engine Missing

> Docker Compose config validated, but image build could not start because Docker Desktop's Linux engine was unavailable.

Related: [[gRPC Agent Decomposition]] · [[Docker and Compose]] · [[Home]]

---

## The Error

`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.`

## What Caused It

Docker Desktop was not running, or its Linux engine pipe was not available to the shell.

## How We Diagnosed It

`docker compose config --quiet` succeeded, which means the Compose YAML was structurally valid. `docker compose build planner-agent` failed before any Dockerfile step ran, so this was a Docker daemon availability issue.

## The Fix

The code-side fix was to make Docker build contexts use the workspace root so service images can see `uv.lock` and run `uv sync --frozen` correctly. The remaining build verification needs Docker Desktop running.

> [!tip]
> Start Docker Desktop, wait for the Linux engine to report ready, then rerun `docker compose build planner-agent`.
