FROM python:3.12-slim

WORKDIR /app

# Install core + MCP extras
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e ".[mcp,llm]"

# Data directory for SQLite history
RUN mkdir -p /app/data
ENV TREND_PULSE_DB=/app/data/history.db

EXPOSE 8080

CMD ["trend-pulse-server"]
