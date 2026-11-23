FROM python:3.11-slim
ARG INSTALL_EXTRAS=ml,pdf
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HOME=/models HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 \
    ANON_LOCAL_FILES_ONLY=true
WORKDIR /service
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu 'torch>=2.6,<3' \
    && pip install --no-cache-dir ".[${INSTALL_EXTRAS}]" \
    && useradd --create-home --uid 10001 service \
    && mkdir /models /state && chown service:service /models /state
COPY scripts ./scripts
USER service
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
