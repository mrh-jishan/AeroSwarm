FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.8.3

# Create non-root user (security: agents never run as root)
RUN useradd -m -u 1000 agent
USER agent

WORKDIR /home/agent/app

COPY --chown=agent:agent pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi

COPY --chown=agent:agent . .

# Workspace is mounted here at runtime
RUN mkdir -p /workspace

CMD ["poetry", "run", "python", "-m", "agent.main"]
