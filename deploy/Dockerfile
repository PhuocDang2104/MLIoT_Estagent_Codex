FROM python:3.13-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg=7:5.1.9-0+deb12u1 && rm -rf /var/lib/apt/lists/*
ARG WITH_BLENDER=0
RUN if [ "$WITH_BLENDER" = "1" ]; then apt-get update && apt-get install -y --no-install-recommends blender python3-numpy && rm -rf /var/lib/apt/lists/*; fi
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY server/assistant/requirements.txt /app/server/assistant/requirements.txt
RUN pip install --no-cache-dir -r server/assistant/requirements.txt \
    && groupadd --gid 10001 assistant \
    && useradd --uid 10001 --gid assistant --no-create-home assistant \
    && mkdir /data && chown assistant:assistant /data
COPY server/assistant/ /app/server/assistant/
COPY server/creator/ /app/server/creator/
COPY pipelines/core/ /app/pipelines/core/
COPY server/tours/ /app/server/tours/
COPY server/exports/ /app/server/exports/
COPY server/narration/ /app/server/narration/
COPY server/demos/ /app/server/demos/
COPY server/limits.py /app/server/limits.py
COPY server/file_lock.py /app/server/file_lock.py
COPY server/storage.py /app/server/storage.py
COPY server/object_storage.py /app/server/object_storage.py
COPY web/ /app/web/
COPY deploy/entrypoint.py deploy/smoke.py deploy/backup_data.py /app/deploy/
USER 10001:10001
EXPOSE 5180
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD ["python", "/app/deploy/smoke.py", "--health-only", "--base-url", "http://127.0.0.1:5180"]
ENTRYPOINT ["python", "/app/deploy/entrypoint.py"]
