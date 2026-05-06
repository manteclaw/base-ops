FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY base_agent_kit_mcp.py .

# Run the MCP server
CMD ["python3", "base_agent_kit_mcp.py"]
