# syntax=docker/dockerfile:1

# ---- Base image, pinned by digest ----------------------------------------
# Pinned by digest, not just the :3.13-slim tag. A tag can be repointed to
# different content; a digest is immutable, so the build is reproducible and
# tamper-evident. Refresh the digest deliberately (e.g. via Dependabot) rather
# than silently picking up whatever the tag points at today.
FROM python:3.13-slim@sha256:b04b5d7233d2ad9c379e22ea8927cd1378cd15c60d4ef876c065b25ea8fb3bf3 AS base

# ---- Builder stage --------------------------------------------------------
# Build dependencies into an isolated venv. Build tooling lives only here and
# never ships to the final image, shrinking the runtime attack surface.
FROM base AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage --------------------------------------------------------
# Slim final image: only the venv and the app code, run as an unprivileged user.
FROM base AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create an unprivileged system user. Dropping root limits the blast radius if
# the app is ever compromised.
RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app

# Copy the prebuilt venv from the builder, then the application source.
COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER app

EXPOSE 8000

# Container self-reports liveness by hitting its own /healthz endpoint. Uses the
# stdlib so curl/wget aren't needed in the runtime image.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
