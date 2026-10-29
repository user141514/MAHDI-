# MAHDI Offline Deployment Implementation Plan

> **For agentic workers:** Execute the approved deployment inline, task by task. No Git repository is present, so do not commit or create a worktree.

**Goal:** Build and verify a Linux amd64 image locally, then deploy it with Docker Compose to `/opt/MT-wuleirencaizhinengti` on port 8901 without restarting or changing other projects.

**Architecture:** One isolated Compose project named `mahdi`, one application container, and a host bind mount for SQLite. The image includes Chromium and Chinese fonts. The host imports a versioned image archive and never builds application dependencies. The user explicitly approved this plan and server deployment in this chat on 2026-10-27.

**Tech Stack:** Python 3.11, FastAPI, SQLite, Playwright Chromium, Docker, Docker Compose, PowerShell and SSH.

- [x] Inspect the server: target directory empty, port 8901 unused, existing applications managed by Compose, public IP port 80 serves Paperpro.
- [x] Check the local Linux Docker engine is running.
- [x] Add deployment files: `Dockerfile`, `.dockerignore`, `compose.yaml`, `.env.example`, and `docs/DEPLOYMENT.md`.
- [x] Add production password hashing, configured teacher password and closed debug reset-link behavior; add focused authentication regressions. Preserve old local accounts through login-time password conversion without a schema change.
- [x] Run `D:/anaconda/envs/mahdi/python.exe -B -m pytest tests -q -p no:cacheprovider`; 69 passed, 3 subtests passed. Synthetic diagnostics also passed.
- [x] Build `mahdi:release-<timestamp>` for `linux/amd64`, using only application source and excluding credentials, database files and local environments.
- [x] Verify the built image locally with a separate temporary data directory and port: real registration/login, 12-question lite assessment, 32-question upgrade, teacher statistics, actual PDFs, production reset-link protection and hashed database values. Real browser flow and mobile overflow checks passed; UID 65534, hashed accounts and restart persistence verified.
- [x] Request a focused independent review of the production protections and deployment isolation before release. Three script guards were strengthened and re-reviewed; no important findings remain.
- [x] Export the tested image to a compressed archive and record SHA256 checksums. Release `release-20261027-210358`, archive 436309125 bytes.
- [x] Record existing remote container IDs, start times and restart counts under the target project's `.ops/`; upload only the reviewed package into that directory.
- [x] Verify uploaded checksums, create a private server `.env` with a random teacher password, create the project data directory, import the image, and run `docker compose -p mahdi up -d --no-build --pull never --wait`. Container `mahdi-app-1` is healthy; imported image identity matches the tested image exactly.
- [x] Add only the public-zone TCP 8901 firewall rule if needed. Runtime and permanent rules added; no global service reload or restart.
- [x] Verify remotely and from the public network; confirm existing container identities, start times and restart counts are unchanged. All original 25 containers unchanged, 26 running after deployment. Online `teststudent` created and login verified without submitting assessments.
- [x] Record the release, validation and exact update/backup/rollback commands in the deployment documentation and return the working URL. Public URL `http://8.138.102.225:8901` verified through direct HTTP and a real browser.

## Rollback boundary

Only operate on `/opt/MT-wuleirencaizhinengti`, image tags beginning `mahdi:`, Compose project `mahdi` and TCP 8901. If first deployment fails, stop that project's container; retain its data and diagnostics. Remove only a firewall rule added by this deployment if rollback is needed. On later updates, retain the previous image and use SQLite's online backup API before replacement. Never overwrite existing data, use `down -v`, prune Docker or modify Nginx routes for other projects.
