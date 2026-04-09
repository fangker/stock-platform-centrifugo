FROM python:3.11-slim AS builder

WORKDIR /app

# 只安装 bridge 运行需要的依赖（不含 pandas）
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install \
    centrifuge-python>=0.4.3 \
    aiohttp>=3.9.0 \
    redis>=5.0.0

# --- 运行阶段 ---
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ ./src/
COPY docker_entry.py .

CMD ["python", "docker_entry.py"]
