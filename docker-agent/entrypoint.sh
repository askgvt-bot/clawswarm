#!/bin/bash
set -e

echo "🦞 ClawSwarm Agent Starting..."
echo "   Agent ID: ${AGENT_ID}"
echo "   Agent Name: ${AGENT_NAME}"
echo "   Agent Type: ${AGENT_TYPE}"

# Create workspace structure
mkdir -p /workspace/.openclaw/workspace

# Write SOUL.md from environment or use default
if [ -n "$AGENT_SOUL" ]; then
    echo "$AGENT_SOUL" > /workspace/.openclaw/workspace/SOUL.md
else
    cat > /workspace/.openclaw/workspace/SOUL.md << 'SOUL'
# SOUL.md - ClawSwarm Agent

You are a specialized AI agent running in ClawSwarm.
Your agent type: ${AGENT_TYPE}
Your agent ID: ${AGENT_ID}

Focus on your assigned tasks. Be efficient and thorough.
Report results clearly. Ask for clarification if needed.
SOUL
fi

# Create OpenClaw directory structure
mkdir -p /workspace/.openclaw/agents/main/agent

# Determine which provider to use based on available API keys
if [ -n "${ANTHROPIC_API_KEY}" ]; then
    PRIMARY_PROVIDER="anthropic"
    PRIMARY_KEY="${ANTHROPIC_API_KEY}"
elif [ -n "${OPENAI_API_KEY}" ]; then
    PRIMARY_PROVIDER="openai"
    PRIMARY_KEY="${OPENAI_API_KEY}"
else
    PRIMARY_PROVIDER="openai"
    PRIMARY_KEY=""
fi

# Write auth-profiles.json with API keys (correct format)
cat > /workspace/.openclaw/agents/main/agent/auth-profiles.json << EOF
{
  "version": 1,
  "profiles": {
    "openai:default": {
      "type": "api_key",
      "provider": "openai",
      "key": "${OPENAI_API_KEY:-}"
    },
    "anthropic:default": {
      "type": "api_key",
      "provider": "anthropic",
      "key": "${ANTHROPIC_API_KEY:-}"
    }
  },
  "lastGood": {
    "${PRIMARY_PROVIDER}": "${PRIMARY_PROVIDER}:default"
  }
}
EOF

# Set file permissions
chmod 600 /workspace/.openclaw/agents/main/agent/auth-profiles.json

# Determine model based on available keys
if [ -n "${OPENAI_API_KEY}" ]; then
    DEFAULT_MODEL="openai/gpt-4o"
elif [ -n "${ANTHROPIC_API_KEY}" ]; then
    DEFAULT_MODEL="anthropic/claude-sonnet-4-20250514"
else
    DEFAULT_MODEL="openai/gpt-4o"
fi

# Write minimal valid openclaw.json config with model override
cat > /workspace/.openclaw/openclaw.json << EOF
{
  "agents": {
    "defaults": {
      "workspace": "/workspace/.openclaw/workspace",
      "model": {
        "primary": "${DEFAULT_MODEL}"
      }
    }
  },
  "gateway": {
    "mode": "local",
    "port": 18789,
    "bind": "loopback"
  },
  "auth": {
    "profiles": {
      "openai:default": {
        "provider": "openai",
        "mode": "api_key"
      },
      "anthropic:default": {
        "provider": "anthropic",
        "mode": "api_key"
      }
    }
  }
}
EOF

echo "   Default Model: ${DEFAULT_MODEL}"

echo "   Primary Provider: ${PRIMARY_PROVIDER}"

# Initialize git repo (OpenClaw needs this)
cd /workspace
git init 2>/dev/null || true
git config user.email "agent@clawswarm.local"
git config user.name "ClawSwarm Agent"

# Start the agent wrapper (handles task communication)
exec node /opt/agent-wrapper.js
