# ============================================
# Salon Booking API - Dockerfile
# ============================================

# ---------- Stage 1: Build Dependencies ----------
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

RUN groupadd -r salon && useradd -r -g salon -d /app salon

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

RUN chmod +x /app/scripts/entrypoint.sh \
    && mkdir -p /app/logs \
    && chown -R salon:salon /app

USER salon

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=5)" || exit 1

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]