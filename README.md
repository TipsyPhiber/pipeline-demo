# pipeline-demo

A small, security-focused CI/CD pipeline built with GitHub Actions.

The app is a tiny FastAPI web service. It's intentionally minimal — the goal of
this repo is to show a clean, secure pipeline, not a complex application. The app
is just something real for the pipeline to test, build, scan, sign, and deploy.

---

## What the app does

A web service with three endpoints:

- `GET /healthz` — liveness check (is the process up?)
- `GET /readyz` — readiness check (is it ready for traffic?)
- `POST /transform` — applies a text transform (`upper`, `lower`, or `reverse`)

The `/transform` endpoint is small but security-conscious: it validates and
size-limits its input, only accepts the three transforms from a fixed allow-list
(anything else is rejected), and never writes request data to the logs.

---

## How the pipeline works

There are four workflows in `.github/workflows/`, each with a single job:

| Workflow | Runs on | What it does |
|---|---|---|
| **CI** | every push & PR | Lints the code, runs a security linter, and runs the tests |
| **CodeQL** | push, PR, weekly | Scans the source for security bugs; results appear in the Security tab |
| **Dependency Review** | PRs | Blocks pull requests that add vulnerable or disallowed-license dependencies |
| **Release** | push to `main`, version tags | Builds, scans, and publishes the container image |

### The release flow

When code lands on `main`, the Release workflow builds the container and then
runs these steps **in this order**:

```
build image (locally)  →  scan it  →  publish to GHCR  →  sign  →  attach provenance
                            │
                    stop if a serious
                    vulnerability is found
```

The scan happens **before** the image is published. If a HIGH or CRITICAL
vulnerability is found, the workflow stops and nothing is published — so a
known-vulnerable image never reaches the registry. The published image is then
cryptographically signed and given a provenance record, so anyone pulling it can
verify it really came from this pipeline.

The published image appears under the repo's **Packages**.

---

## Running it locally

You need Python 3.13. (Docker is optional — only needed to build the image
yourself; the pipeline builds it for you.)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run the tests
pytest

# Lint and security-lint (same as CI)
ruff check .
bandit -r app

# Start the app
uvicorn app.main:app --reload
```

Then try it:

```bash
curl localhost:8000/healthz

curl -X POST localhost:8000/transform \
  -H 'content-type: application/json' \
  -d '{"text":"hello","action":"upper"}'
```

To build the container image yourself: `docker build -t pipeline-demo .`

---

## Security choices, and why

**In the pipeline**

- **Code is linted for security issues** (bandit) and **statically analyzed**
  (CodeQL) on every change, so insecure patterns are caught early.
- **Dependencies are reviewed on every PR**, so a vulnerable or
  badly-licensed package can't slip in unnoticed.
- **The image is scanned before it's published** — the registry never holds a
  known-bad image.
- **Images are signed and get a provenance record** so consumers can verify what
  they're running and where it came from. Signing uses short-lived OIDC tokens,
  so there's no signing key stored anywhere to leak.
- **Actions are pinned to exact versions** (by commit hash), so a compromised
  third-party action can't silently change what our pipeline runs.
- **Workflow permissions are minimal by default** (read-only), with write access
  granted only to the specific job that needs it.

**In the container**

- Built in stages so build tools never ship in the final image.
- The base image is pinned to an exact version that can't be swapped out from
  under us.
- The app runs as a non-root user to limit the damage if it's ever compromised.

**In the repository (recommended settings)**

To complete the picture, these are enabled in the repo's settings:

- Branch protection on `main` (require a reviewed pull request to merge).
- Secret scanning with push protection (blocks committed secrets).
- A `CODEOWNERS` file so changes to the pipeline or Dockerfile need review.
- Dependabot to keep dependencies and pinned actions up to date.

---

## What's intentionally left out

To keep this small and clean, the following were skipped on purpose:

- No persistence, authentication, or rate limiting in the app.
- No runtime container hardening (read-only filesystem, seccomp) or Kubernetes
  deployment — "deploy" here means publishing the image.
- No SBOM (software bill of materials) generation yet.
- The image scan reports vulnerabilities that have no fix available, but doesn't
  block on them — a deliberate trade-off to avoid failing on issues we can't act on.
