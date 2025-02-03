import asyncio
from services.research_planner import ResearchPlanner
import structlog

logger = structlog.get_logger()

def main():
    # Initialize the research planner
    planner = ResearchPlanner()
    
    # Get user input
    print("\nWelcome to the Research Planner Test!")
    print("=====================================")
    print("\nThis tool will break down your research query into specific search queries")
    print("that will be used to gather comprehensive information.\n")
    
    while True:
        # Get the research query from user
        query = input("\nEnter your research query (or 'quit' to exit): ")
        
        if query.lower() == 'quit':
            break
            
        try:
            # Generate the research plan
            print("\nGenerating research plan...")
            search_queries = planner.generate_research_plan(query)
            
            # Display results
            print("\nResearch Plan:")
            print("==============")
            for i, search_query in enumerate(search_queries, 1):
                print(f"{i}. {search_query}")
                
        except Exception as e:
            logger.error("test_script_error", error=str(e))
            print(f"\nError: {str(e)}")
            
        print("\n" + "="*50)

if __name__ == "__main__":
    main() 