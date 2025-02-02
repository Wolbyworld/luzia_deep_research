import httpx
import asyncio
import json
from dotenv import load_dotenv
import os
import sys

"""
Test script for the Luzia Deep Research API.
For detailed documentation about the system architecture, flow, and configuration parameters,
please refer to the README.md file in this directory.
"""

# Load environment variables
load_dotenv()

async def test_research(query: str = None):
    """
    Test the research API endpoint
    """
    base_url = "http://localhost:8000"
    
    # If no query provided, ask for user input
    if not query:
        query = input("Enter your research question: ")
    
    async with httpx.AsyncClient() as client:
        try:
            # Test health check
            response = await client.get(f"{base_url}/")
            print("\nHealth Check Response:", response.json())
            
            # Test research endpoint
            payload = {
                "query": query,
                "max_results": 5,
                "time_filter": "month"
            }
            
            print("\nSending Research Request...")
            print("Query:", query)
            
            response = await client.post(
                f"{base_url}/api/research",
                json=payload,
                timeout=120.0  # Increased timeout for longer processing
            )
            
            print("\nResponse Status:", response.status_code)
            
            if response.status_code == 200:
                result = response.json()
                print("\nResearch Completed Successfully!")
                print("\nReport:")
                print("=" * 80)
                print(result["content"])
                print("=" * 80)
                print("\nSources:")
                for source in result["sources"]:
                    print(f"- {source}")
            else:
                print("\nError Response:", response.status_code)
                try:
                    error_detail = response.json()
                    print("Error Details:", json.dumps(error_detail, indent=2))
                except:
                    print("Raw Error Response:", response.text)
                    
        except httpx.TimeoutException:
            print("\nError: Request timed out. The operation took too long to complete.")
        except httpx.RequestError as e:
            print(f"\nError: Failed to connect to the server: {str(e)}")
        except Exception as e:
            print(f"\nUnexpected error occurred: {str(e)}")

if __name__ == "__main__":
    # Get query from command line argument if provided
    query = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(test_research(query)) 