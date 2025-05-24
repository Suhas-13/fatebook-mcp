#!/usr/bin/env python3
"""
Fatebook MCP Server

An MCP server that provides tools to interact with Fatebook predictions.
Allows listing, searching, and updating predictions with natural language descriptions.
"""

import asyncio
import logging
import os
from typing import Any, Sequence, Optional, List, Dict
from urllib.parse import urlencode
import re
from datetime import datetime, timezone
from fuzzywuzzy import fuzz, process

import httpx
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fatebook-mcp")

# Fatebook API configuration
FATEBOOK_BASE_URL = "https://fatebook.io/api"
# You can set the API key here or via environment variable FATEBOOK_API_KEY
API_KEY = os.environ.get("FATEBOOK_API_KEY", "f6rv23i5jqspkgb6ih9ew8")

class FatebookClient:
    """Client for interacting with the Fatebook API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient()
    
    async def get_questions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of questions from Fatebook"""
        return await self.get_questions_with_params(limit=limit)
    
    async def get_questions_with_params(
        self, 
        limit: int = 50,
        resolved: Optional[bool] = None,
        unresolved: Optional[bool] = None,
        show_all_public: bool = False,
        search_string: Optional[str] = None,
        filter_tag_ids: Optional[List[str]] = None,
        filter_tournament_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of questions from Fatebook with advanced filtering"""
        url = f"{FATEBOOK_BASE_URL}/v0/getQuestions"
        params = {"apiKey": self.api_key, "limit": limit}
        
        if resolved is not None:
            params["resolved"] = "true" if resolved else "false"
        if unresolved is not None:
            params["unresolved"] = "true" if unresolved else "false"
        if show_all_public:
            params["showAllPublic"] = "true"
        if search_string:
            params["searchString"] = search_string
        if filter_tag_ids:
            for tag_id in filter_tag_ids:
                params.setdefault("filterTagIds", []).append(tag_id)
        if filter_tournament_id:
            params["filterTournamentId"] = filter_tournament_id
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            logger.info(f"API Response: {response.status_code}")
            logger.info(f"Response data keys: {list(data.keys())}")
            # The API returns questions under 'items' key, not 'questions'
            questions = data.get("items", [])
            logger.info(f"Questions returned: {len(questions)}")
            return questions
        except Exception as e:
            logger.error(f"Error fetching questions: {e}")
            logger.error(f"Response status: {getattr(response, 'status_code', 'N/A')}")
            if hasattr(response, 'text'):
                logger.error(f"Response text: {response.text}")
            return []
    
    async def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific question by ID"""
        url = f"{FATEBOOK_BASE_URL}/v0/getQuestion"
        params = {"apiKey": self.api_key, "questionId": question_id}
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching question {question_id}: {e}")
            return None
    
    async def add_forecast(self, question_id: str, forecast: float, comment: str = "") -> bool:
        """Add a forecast to a question"""
        url = f"{FATEBOOK_BASE_URL}/v0/addForecast"
        data = {
            "apiKey": self.api_key,
            "questionId": question_id,
            "forecast": forecast
        }
        if comment:
            data["comment"] = comment
        
        try:
            response = await self.client.post(url, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error adding forecast to {question_id}: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

class PredictionMatcher:
    """Handles matching user descriptions to predictions"""
    
    @staticmethod
    def find_matching_predictions(description: str, questions: List[Dict[str, Any]], threshold: int = 60) -> List[Dict[str, Any]]:
        """Find predictions that match the given description"""
        if not questions:
            return []
        
        # Extract question titles for matching
        titles = [(q.get("title", ""), i) for i, q in enumerate(questions)]
        
        # Use fuzzy matching to find similar titles
        matches = process.extract(description, [title for title, _ in titles], limit=10, scorer=fuzz.token_sort_ratio)
        
        # Filter by threshold and return matching questions
        matching_questions = []
        for match_text, score in matches:
            if score >= threshold:
                # Find the original question index
                for title, idx in titles:
                    if title == match_text:
                        question = questions[idx].copy()
                        question["_match_score"] = score
                        matching_questions.append(question)
                        break
        
        # Sort by match score (descending)
        matching_questions.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
        
        return matching_questions[:2]  # Return top 2 matches

# Initialize the Fatebook client
fatebook_client = FatebookClient(API_KEY)
prediction_matcher = PredictionMatcher()

# Create the MCP server
server = Server("fatebook-mcp")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="list_predictions",
            description="List your Fatebook predictions/questions",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of predictions to return (default: 20)",
                        "default": 20
                    }
                },
                "required": []
            },
        ),
        Tool(
            name="search_predictions",
            description="Search for predictions matching a description",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description to search for in prediction titles"
                    },
                    "threshold": {
                        "type": "integer",
                        "description": "Minimum similarity score (0-100, default: 60)",
                        "default": 60
                    }
                },
                "required": ["description"]
            },
        ),
        Tool(
            name="update_prediction",
            description="Update a prediction probability based on a description",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of the prediction to update"
                    },
                    "new_probability": {
                        "type": "number",
                        "description": "New probability (0.0 to 1.0)"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional comment explaining the update",
                        "default": ""
                    }
                },
                "required": ["description", "new_probability"]
            },
        ),
        Tool(
            name="get_prediction_details",
            description="Get detailed information about a specific prediction",
            inputSchema={
                "type": "object",
                "properties": {
                    "question_id": {
                        "type": "string",
                        "description": "The question ID to get details for"
                    }
                },
                "required": ["question_id"]
            },
        ),
        Tool(
            name="list_predictions_filtered",
            description="List predictions with advanced filtering options",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of predictions to return (default: 20)",
                        "default": 20
                    },
                    "resolved": {
                        "type": "boolean",
                        "description": "Filter to only resolved predictions"
                    },
                    "unresolved": {
                        "type": "boolean", 
                        "description": "Filter to only unresolved predictions"
                    },
                    "show_all_public": {
                        "type": "boolean",
                        "description": "Show all public predictions (not just yours)",
                        "default": False
                    },
                    "search_string": {
                        "type": "string",
                        "description": "Search for predictions containing this text"
                    }
                },
                "required": []
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""
    
    if name == "list_predictions":
        limit = arguments.get("limit", 20)
        questions = await fatebook_client.get_questions(limit=limit)
        
        if not questions:
            return [TextContent(type="text", text="No predictions found.")]
        
        result = f"Found {len(questions)} predictions:\n\n"
        for i, q in enumerate(questions, 1):
            title = q.get("title", "No title")
            question_id = q.get("id", "No ID")
            created_date = q.get("createdDate", "Unknown date")
            resolve_by = q.get("resolveBy", "No resolution date")
            
            # Get latest forecast
            forecasts = q.get("forecasts", [])
            latest_forecast = "No forecast"
            if forecasts:
                latest_forecast = f"{forecasts[-1].get('forecast', 0) * 100:.1f}%"
            
            result += f"{i}. **{title}**\n"
            result += f"   ID: {question_id}\n"
            result += f"   Current forecast: {latest_forecast}\n"
            result += f"   Resolves by: {resolve_by}\n"
            result += f"   Created: {created_date}\n\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "search_predictions":
        description = arguments.get("description", "")
        threshold = arguments.get("threshold", 60)
        
        if not description:
            return [TextContent(type="text", text="Please provide a description to search for.")]
        
        questions = await fatebook_client.get_questions(limit=100)
        matches = prediction_matcher.find_matching_predictions(description, questions, threshold)
        
        if not matches:
            return [TextContent(type="text", text=f"No predictions found matching '{description}'.")]
        
        result = f"Found {len(matches)} predictions matching '{description}':\n\n"
        for i, match in enumerate(matches, 1):
            title = match.get("title", "No title")
            question_id = match.get("id", "No ID")
            score = match.get("_match_score", 0)
            
            # Get latest forecast
            forecasts = match.get("forecasts", [])
            latest_forecast = "No forecast"
            if forecasts:
                latest_forecast = f"{forecasts[-1].get('forecast', 0) * 100:.1f}%"
            
            result += f"{i}. **{title}** (Match: {score}%)\n"
            result += f"   ID: {question_id}\n"
            result += f"   Current forecast: {latest_forecast}\n\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "update_prediction":
        description = arguments.get("description", "")
        new_probability = arguments.get("new_probability", 0)
        comment = arguments.get("comment", "")
        
        if not description:
            return [TextContent(type="text", text="Please provide a description of the prediction to update.")]
        
        if not (0 <= new_probability <= 1):
            return [TextContent(type="text", text="Probability must be between 0.0 and 1.0.")]
        
        # Find matching predictions
        questions = await fatebook_client.get_questions(limit=100)
        matches = prediction_matcher.find_matching_predictions(description, questions, threshold=60)
        
        if not matches:
            return [TextContent(type="text", text=f"No predictions found matching '{description}'.")]
        
        if len(matches) > 2:
            matches = matches[:2]  # Limit to top 2 matches
        
        updated_predictions = []
        for match in matches:
            question_id = match.get("id")
            title = match.get("title", "No title")
            
            success = await fatebook_client.add_forecast(question_id, new_probability, comment)
            if success:
                updated_predictions.append(f"- **{title}** (ID: {question_id}) → {new_probability * 100:.1f}%")
            else:
                updated_predictions.append(f"- **{title}** (ID: {question_id}) → FAILED to update")
        
        result = f"Updated {len([p for p in updated_predictions if 'FAILED' not in p])} prediction(s):\n\n"
        result += "\n".join(updated_predictions)
        
        if comment:
            result += f"\n\nComment: {comment}"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_prediction_details":
        question_id = arguments.get("question_id", "")
        
        if not question_id:
            return [TextContent(type="text", text="Please provide a question ID.")]
        
        question = await fatebook_client.get_question_by_id(question_id)
        
        if not question:
            return [TextContent(type="text", text=f"Question with ID '{question_id}' not found.")]
        
        title = question.get("title", "No title")
        created_date = question.get("createdDate", "Unknown")
        resolve_by = question.get("resolveBy", "No resolution date")
        resolved = question.get("resolved", False)
        resolution = question.get("resolution", "")
        
        result = f"**{title}**\n\n"
        result += f"ID: {question_id}\n"
        result += f"Created: {created_date}\n"
        result += f"Resolves by: {resolve_by}\n"
        result += f"Status: {'Resolved' if resolved else 'Open'}\n"
        
        if resolved and resolution:
            result += f"Resolution: {resolution}\n"
        
        # Show forecast history
        forecasts = question.get("forecasts", [])
        if forecasts:
            result += f"\nForecast history ({len(forecasts)} forecasts):\n"
            for i, forecast in enumerate(forecasts[-5:], 1):  # Show last 5 forecasts
                forecast_value = forecast.get("forecast", 0) * 100
                forecast_date = forecast.get("createdDate", "Unknown date")
                result += f"  {i}. {forecast_value:.1f}% on {forecast_date}\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "list_predictions_filtered":
        limit = arguments.get("limit", 20)
        resolved = arguments.get("resolved")
        unresolved = arguments.get("unresolved")
        show_all_public = arguments.get("show_all_public", False)
        search_string = arguments.get("search_string")
        
        questions = await fatebook_client.get_questions_with_params(
            limit=limit,
            resolved=resolved,
            unresolved=unresolved,
            show_all_public=show_all_public,
            search_string=search_string
        )
        
        if not questions:
            filters_used = []
            if resolved: filters_used.append("resolved")
            if unresolved: filters_used.append("unresolved")
            if show_all_public: filters_used.append("public")
            if search_string: filters_used.append(f"search='{search_string}'")
            filter_text = f" with filters: {', '.join(filters_used)}" if filters_used else ""
            return [TextContent(type="text", text=f"No predictions found{filter_text}.")]
        
        result = f"Found {len(questions)} predictions:\n\n"
        for i, q in enumerate(questions, 1):
            title = q.get("title", "No title")
            question_id = q.get("id", "No ID")
            created_date = q.get("createdDate", "Unknown date")
            resolve_by = q.get("resolveBy", "No resolution date")
            resolved_status = q.get("resolved", False)
            
            # Get latest forecast
            forecasts = q.get("forecasts", [])
            latest_forecast = "No forecast"
            if forecasts:
                latest_forecast = f"{forecasts[-1].get('forecast', 0) * 100:.1f}%"
            
            result += f"{i}. **{title}**\n"
            result += f"   ID: {question_id}\n"
            result += f"   Current forecast: {latest_forecast}\n"
            result += f"   Status: {'Resolved' if resolved_status else 'Open'}\n"
            result += f"   Resolves by: {resolve_by}\n"
            result += f"   Created: {created_date}\n\n"
        
        return [TextContent(type="text", text=result)]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    # Run the server using stdin/stdout streams
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fatebook-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())