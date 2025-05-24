#!/usr/bin/env python3
"""
Test script for the Fatebook MCP Server
"""

import asyncio
import os
from dotenv import load_dotenv
from server import FatebookClient

# Load environment variables
load_dotenv()

async def test_fatebook_api():
    """Test the Fatebook API connection"""
    print("Testing Fatebook API connection...")
    
    api_key = os.environ.get("FATEBOOK_API_KEY")
    if not api_key:
        print("Error: FATEBOOK_API_KEY not found in environment variables")
        return
        
    client = FatebookClient(api_key)
    
    try:
        # Test getting questions with different parameters
        print("Testing basic getQuestions...")
        questions = await client.get_questions(limit=5)
        print(f"✓ Basic call retrieved {len(questions)} questions")
        
        # Test with showAllPublic flag
        print("Testing with showAllPublic...")
        questions_public = await client.get_questions_with_params(limit=5, show_all_public=True)
        print(f"✓ Public questions call retrieved {len(questions_public)} questions")
        
        # Test with unresolved filter
        print("Testing with unresolved filter...")
        questions_unresolved = await client.get_questions_with_params(limit=5, unresolved=True)
        print(f"✓ Unresolved questions call retrieved {len(questions_unresolved)} questions")
        
        # Use the best result set for further testing
        all_questions = questions or questions_public or questions_unresolved
        questions = all_questions
        
        if questions:
            # Test getting a specific question
            first_question = questions[0]
            question_id = first_question.get("id")
            if question_id:
                question_details = await client.get_question_by_id(question_id)
                if question_details:
                    print(f"✓ Successfully retrieved question details for ID: {question_id}")
                else:
                    print(f"✗ Failed to retrieve question details for ID: {question_id}")
            
        
        print("\n" + "="*50)
        print("Sample questions from your Fatebook:")
        for i, q in enumerate(questions[:3], 1):
            title = q.get("title", "No title")
            question_id = q.get("id", "No ID")
            forecasts = q.get("forecasts", [])
            latest_forecast = "No forecast"
            if forecasts:
                forecast_val = forecasts[-1].get('forecast', 0)
                if isinstance(forecast_val, (int, float)):
                    latest_forecast = f"{forecast_val * 100:.1f}%"
                else:
                    latest_forecast = str(forecast_val)
            
            print(f"\n{i}. {title}")
            print(f"   ID: {question_id}")
            print(f"   Current forecast: {latest_forecast}")
    
    except Exception as e:
        print(f"✗ Error testing API: {e}")
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_fatebook_api())