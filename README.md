# Fatebook MCP Server

An MCP (Model Context Protocol) server that enables AI assistants to interact with your Fatebook predictions. This allows you to easily list and update your predictions using natural language.

## Features

- **List predictions**: View all your unresolved predictions (not public predictions)
- **Update predictions**: Modify prediction probabilities by question ID
- **Get prediction details**: View detailed information including all forecasts from different users
- **Author information**: Shows who created each prediction and who made each forecast

## Installation

1. Clone or download this repository
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Fatebook API key:
   ```
   FATEBOOK_API_KEY=your_api_key_here
   ```

   Get your API key from https://fatebook.io/api-setup

## Usage

### Running the Server

```bash
python server.py
```

### Available Tools

1. **list_predictions**: List all your unresolved Fatebook predictions
   - Optional parameter: `limit` (default: 1000 - returns all predictions)
   - Automatically filters to show only unresolved predictions
   - Shows only your own predictions (not public ones)

2. **update_prediction**: Update a prediction probability by ID
   - Required parameters: `question_id`, `new_probability` (0.0 to 1.0)
   - Optional parameter: `comment` (explanation for the update)

3. **get_prediction_details**: Get detailed information about a specific prediction
   - Required parameter: `question_id`

### Example Usage

You can use this MCP server with Claude Desktop or other MCP-compatible AI assistants:

- "List my predictions"
- "Update my LID house prediction to 35%"
- "Show me details for my prediction about St Andrews"

**Note**: The AI assistant handles question IDs internally - you don't need to know or mention them!

## How It Works

The server connects to the Fatebook API to manage your predictions:

1. **List**: Fetches all your unresolved predictions for easy review
2. **Update**: Updates a specific prediction by its ID
3. **Details**: Shows full forecast history including who made each prediction
4. **Latest forecast**: Shows the most recent forecast (which may be from any user)

## API Endpoints Used

This server interacts with the following Fatebook API endpoints:

- `GET /v0/getQuestions` - List questions
- `GET /v0/getQuestion` - Get specific question details  
- `POST /v0/addForecast` - Add new forecast to a question

## Requirements

- Python 3.8+
- Internet connection for Fatebook API access
- Valid Fatebook API key
