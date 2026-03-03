import requests
import logging
import json
from typing import Dict, Optional, Any
from requests.exceptions import RequestException, Timeout, ConnectionError


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DigEdit.Fetcher")

class GraphDataFetcher:
    """
     code for fetching discussion graph data from the Neo4j API.
        api_url (str): The endpoint URL for the graph data.
        timeout (int): Request timeout in seconds (crucial for perceived latency).
    """
    
    def __init__(self, api_url: str, timeout: int = 10):
        self.api_url = api_url
        self.timeout = timeout
        self._last_response: Optional[Dict[str, Any]] = None

    def fetch_graph_data(self) -> Dict[str, Any]:
        """
        Executes the HTTP GET request to retrieve the data.
        """
        try:
            logger.info(f"getting data from: {self.api_url}")
            
            # need to use a timeout
            response = requests.get(self.api_url, timeout=self.timeout)
            response.raise_for_status()
            
            # clean up JSON content
            data = response.json()
            self._last_response = data
            
            logger.info("Successfully retrieved graph data.")
            return data
            
        except Timeout:
            logger.error(f"Request timed out after {self.timeout} seconds.")
            raise RuntimeError("Data fetch timed out. Please check your connection.")
            
        except ConnectionError:
            logger.error("Failed to establish connection to the graph API.")
            raise RuntimeError("Unable to connect to discussion graph server.")
            
        except json.JSONDecodeError:
            logger.error("Received response was not valid JSON.")
            raise RuntimeError("Invalid data format received from API.")
            
        except RequestException as e:
            logger.error(f"An unexpected network error occurred: {e}")
            raise RuntimeError(f"Network error during data ingestion: {e}")

    def get_data_summary(self) -> None:
        """
        cleans up the last fetched data and prints a summary and the first 10 nodes
               """
        if not self._last_response:
            logger.warning("No data fetched yet. Call fetch_graph_data() first.")
            return

        data = self._last_response
        
        nodes = data.get('nodes', data.get('elements', []))
        edges = data.get('edges', data.get('relationships', []))
        
        print("\n" + "="*50)
        print("--- Data Summary ---")
        print(f"Total Nodes: {len(nodes) if isinstance(nodes, list) else 'N/A'}")
        print(f"Total Edges: {len(edges) if isinstance(edges, list) else 'N/A'}")
        
        # --- Display the first 10 Nodes ---
        if isinstance(nodes, list) and len(nodes) > 0:
            display_count = min(10, len(nodes)) # Prevents crashing if there are < 10 nodes
            print(f"\nExample Node Structure (First {display_count} Nodes):")
            
            for i in range(display_count):
                node = nodes[i]
                node_type = node.get("type", "Unknown")
                print(f"\n{i + 1}. [{node_type}] Node Data:")
                print(json.dumps(node, indent=2))
        else:
            print("\nWarning: No nodes found in the response.")
            
        print("\n" + "="*50 + "\n")

def main():
    API_ENDPOINT = "http://api.gonzalezerik.com/get-graph"
    
    # Start the fetcher
    fetcher = GraphDataFetcher(api_url=API_ENDPOINT, timeout=15)
    
    try:
        # 1. Fetch Data
        graph_data = fetcher.fetch_graph_data()
        
        # 2. Verify Data 
        fetcher.get_data_summary()
        
        # 3. Integration Point
        print("Data ready for front end")
        
    except RuntimeError as e:
        print(f"[CRITICAL] Data Intake Failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
