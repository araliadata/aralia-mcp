# Aralia Open Data MCP Server

This MCP server enables you to receive structured data in response to your queries.

It provides organized information from Aralia's databases relevant to your questions.

## Prerequisites

1. MCP client: Cursor, Claude desktop, or similar applications
2. UV package manager: Installation instructions available at https://docs.astral.sh/uv/getting-started/installation/


## Clone repository
```bash
git clone https://github.com/araliadata/aralia-mcp.git

```

## MCP settings 

Configure your MCP settings by adding the following JSON configuration to your settings file.
(You'll need to register at https://www.araliadata.io/ to obtain your ARALIA_USERNAME and ARALIA_PASSWORD credentials)

```json
{
  "mcpServers": {
    "data-search-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/aralia-mcp",  // Please replace this with the full path to your locally cloned aralia-mcp project
        "run",
        "server.py"             
      ],
      "env": {
        "ARALIA_USERNAME": "your_registered_email@example.com",  // Please enter your email registered at araliadata.io
        "ARALIA_PASSWORD": "your_secure_password"                // Please enter your account password for araliadata.io
      }
    }
  }
}
```
