#!/bin/bash

# Script to restart Claude Desktop and test the MCP server

echo "Fatebook MCP Server Restart Helper"
echo "=================================="
echo ""

# Check if Claude Desktop is running
if pgrep -x "Claude" > /dev/null; then
    echo "✓ Claude Desktop is running"
    echo ""
    echo "To restart Claude Desktop:"
    echo "1. Quit Claude Desktop (Cmd+Q)"
    echo "2. Reopen Claude Desktop"
    echo ""
    read -p "Press Enter after you've restarted Claude Desktop..."
else
    echo "✗ Claude Desktop is not running"
    echo "Please start Claude Desktop first"
fi

echo ""
echo "Testing MCP server directly..."
echo "------------------------------"
echo ""

# Test the server can start
cd "$(dirname "$0")"
timeout 5 python3.10 server.py < /dev/null > /tmp/mcp_test.log 2>&1 &
SERVER_PID=$!

sleep 2

if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✓ MCP server started successfully"
    kill $SERVER_PID 2>/dev/null
else
    echo "✗ MCP server failed to start"
    echo "Error log:"
    cat /tmp/mcp_test.log
fi

echo ""
echo "MCP Configuration Details:"
echo "-------------------------"
echo "Config file: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "Server path: $(pwd)/server.py"
echo "Python version: $(python3.10 --version)"
echo ""
echo "To use in Claude Desktop:"
echo "1. Make sure Claude Desktop is restarted"
echo "2. Look for 'fatebook' in the MCP tools menu"
echo "3. Try commands like:"
echo "   - 'List my predictions'"
echo "   - 'Show my unresolved predictions'"
echo "   - 'Search for predictions about AI'"
echo ""
echo "If it's still not working:"
echo "1. Check Claude Desktop logs: ~/Library/Logs/Claude/"
echo "2. Try running: python3.10 test_server.py"