FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY server/assistant/requirements.txt /app/server/assistant/requirements.txt
RUN pip install --no-cache-dir -r server/assistant/requirements.txt \
    && groupadd --gid 10001 assistant \
    && useradd --uid 10001 --gid assistant --no-create-home assistant \
    && mkdir /data && chown assistant:assistant /data
COPY server/assistant/ /app/server/assistant/
COPY server/creator/ /app/server/creator/
COPY server/tours/ /app/server/tours/
COPY web/ /app/web/
COPY deploy/entrypoint.py deploy/smoke.py /app/deploy/
USER 10001:10001
EXPOSE 5180
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD ["python", "/app/deploy/smoke.py", "--health-only", "--base-url", "http://127.0.0.1:5180"]
ENTRYPOINT ["python", "/app/deploy/entrypoint.py"]
