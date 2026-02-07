# ClawSwarm Agent - OpenClaw in Docker
FROM node:22-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install OpenClaw globally
RUN npm install -g openclaw

# Create workspace directory
RUN mkdir -p /workspace /config
WORKDIR /workspace

# Copy agent wrapper script
COPY agent-wrapper.js /opt/agent-wrapper.js
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

# Environment variables for configuration
ENV AGENT_ID=""
ENV AGENT_NAME=""
ENV AGENT_TYPE=""
ENV AGENT_TASK=""
ENV ORCHESTRATOR_URL="http://host.docker.internal:8420"
ENV OPENAI_API_KEY=""
ENV ANTHROPIC_API_KEY=""

# Expose port for agent API
EXPOSE 8421

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8421/health || exit 1

ENTRYPOINT ["/opt/entrypoint.sh"]
