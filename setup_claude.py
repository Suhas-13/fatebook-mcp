#!/usr/bin/env python3
"""
Setup script to configure the Fatebook MCP server for Claude Desktop
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_claude_config():
    """Setup Claude Desktop configuration for the Fatebook MCP server"""
    
    # Path to Claude Desktop config
    claude_config_dir = Path.home() / "Library" / "Application Support" / "Claude"
    claude_config_file = claude_config_dir / "claude_desktop_config.json"
    
    # Ensure config directory exists
    claude_config_dir.mkdir(parents=True, exist_ok=True)
    
    # Current working directory (where server.py is located)
    server_path = Path(__file__).parent.absolute() / "server.py"
    
    # MCP server configuration
    fatebook_config = {
        "command": "python3.10",
        "args": [str(server_path)],
        "env": {
            "FATEBOOK_API_KEY": os.environ.get("FATEBOOK_API_KEY", "")
        }
    }
    
    # Load existing config or create new one
    if claude_config_file.exists():
        with open(claude_config_file, 'r') as f:
            config = json.load(f)
    else:
        config = {
            "mcpServers": {}
        }
    
    # Ensure mcpServers key exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add or update the Fatebook MCP server
    config["mcpServers"]["fatebook"] = fatebook_config
    
    # Write config back
    with open(claude_config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✓ Claude Desktop configuration updated!")
    print(f"  Config file: {claude_config_file}")
    print(f"  Server path: {server_path}")
    print("\nTo use the Fatebook MCP server:")
    print("1. Restart Claude Desktop")
    print("2. In Claude, you can now use commands like:")
    print("   - 'List my Fatebook predictions'")
    print("   - 'Search for predictions about AI'") 
    print("   - 'Update my prediction about GPT-5 to 75%'")
    print("\nNote: Make sure you have some predictions in Fatebook first!")

if __name__ == "__main__":
    setup_claude_config()