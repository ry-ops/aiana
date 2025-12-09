# Aiana - AI Conversation Attendant for Claude Code
# Multi-stage build for minimal image size

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install package
RUN pip install --no-cache-dir --user -e .

# Production stage
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Aiana"
LABEL org.opencontainers.image.description="AI Conversation Attendant for Claude Code"
LABEL org.opencontainers.image.source="https://github.com/ry-ops/aiana"
LABEL org.opencontainers.image.licenses="MIT"

# Create non-root user
RUN useradd --create-home --shell /bin/bash aiana

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/aiana/.local

# Copy application code
COPY --chown=aiana:aiana src/ ./src/
COPY --chown=aiana:aiana pyproject.toml README.md LICENSE ./

# Copy entrypoint script
COPY --chown=aiana:aiana docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set environment
ENV PATH="/home/aiana/.local/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create data directories
RUN mkdir -p /home/aiana/.aiana /home/aiana/.claude && \
    chown -R aiana:aiana /home/aiana

# Switch to non-root user
USER aiana

# Volumes for data persistence and Claude Code access
VOLUME ["/home/aiana/.aiana", "/home/aiana/.claude"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD aiana status || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start", "--scan"]
