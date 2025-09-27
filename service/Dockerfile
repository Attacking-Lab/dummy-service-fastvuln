FROM python:3.12-slim-bookworm

COPY --from=docker.io/astral/uv:latest /uv /uvx /bin

WORKDIR /app

COPY uv.lock pyproject.toml .

RUN uv sync --frozen --exact

COPY main.py .

CMD ["uv", "run", "main.py"]
