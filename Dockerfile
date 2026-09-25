FROM python:3.12.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY pyproject.toml ./
COPY sadwave ./sadwave
COPY migrations ./migrations
COPY scripts ./scripts

RUN python -m pip install --upgrade pip==25.2 \
    && python -m pip install .

USER 10001
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/health', timeout=3).read()"

CMD ["python", "-m", "sadwave"]
