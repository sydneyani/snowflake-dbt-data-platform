FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /uvx /bin/
WORKDIR /app
ENV UV_LINK_MODE=copy \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false \
    MERIDIAN_ROOT=/app

COPY . .
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "meridian-pipeline"]
