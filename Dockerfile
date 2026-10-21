FROM python:3.14-slim

WORKDIR /app

# Install core + MCP extras
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e ".[mcp,llm]"

# Data directory for SQLite history
RUN mkdir -p /app/data
ENV TREND_PULSE_DB=/app/data/history.db

EXPOSE 8080

# Streamable HTTP MCP endpoint at http://<host>:8080/mcp (stdio would exit as soon as stdin closes)
CMD ["trend-pulse-server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8080"]
