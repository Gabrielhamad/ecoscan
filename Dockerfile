FROM python:3.12.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home appuser \
    && chown appuser:appuser /app

COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.lock \
    && python -m pip check

COPY --chown=10001:10001 config ./config
COPY --chown=10001:10001 assets ./assets
COPY --chown=10001:10001 models/semantic-v1 ./models/semantic-v1
COPY --chown=10001:10001 src ./src
COPY --chown=10001:10001 templates ./templates
COPY --chown=10001:10001 migrations ./migrations
COPY --chown=10001:10001 .streamlit ./.streamlit
COPY --chown=10001:10001 streamlit_app.py ./streamlit_app.py

USER 10001:10001
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/_stcore/health', timeout=2)"
CMD ["sh", "-c", "exec streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=\"${PORT}\" --server.headless=true --browser.gatherUsageStats=false"]
