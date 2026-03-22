import streamlit as st
import streamlit.components.v1 as components
import json
import os
from pyvis.network import Network

# Import the scraper class from your existing file
from redditScrape import RedditScraper

# --- Configuration ---
# Makes the layout wide so the graph has plenty of room
st.set_page_config(page_title="DigEdit UI Skeleton", layout="wide")
DATA_FILE = "reddit_data.json"

# --- Main App Layout ---
# Streamlit automatically creates a hamburger menu for the sidebar on smaller screens
with st.sidebar:
    st.title("DigEdit Controls")
    
    st.markdown("### 1. Data Intake")
    target_url = st.text_input("Reddit Thread URL:", value="https://www.reddit.com/r/learnpython/comments/...")
    
    # Run the scraper when clicked
    if st.button("Scrape & Save Data"):
        with st.spinner("Scraping Reddit API..."):
            try:
                # Instantiate your existing scraper
                scraper = RedditScraper()
                
                # Fetch data and save it directly to a file as requested
                reddit_data = scraper.fetch_submission_data(target_url)
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(reddit_data, f, indent=2)
                    
                st.success(f"Data successfully pulled and saved to {DATA_FILE}!")
            except Exception as e:
                st.error(f"Scraping failed: {e}")

    st.markdown("---")
    st.markdown("### Node Hierarchy")
    st.caption("Expand to see relationship structure")
    
    # A basic hierarchical menu for the sidebar 
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            
        post_title = data.get("post", {}).get("title", "Unknown Post")
        with st.expander(f"📦 Root Post: {post_title[:25]}..."):
            st.write(f"**ID:** {data.get('post', {}).get('id')}")
            
            # Example of listing top-level comments under the post
            comments = data.get("comments", [])
            for c in comments[:5]:  # Just showing the first 5 for the skeleton
                st.write(f"↳ 🗣️ {c['author']}: {c['text'][:20]}...")
            if len(comments) > 5:
                st.write("↳ *(...more comments)*")
    else:
        st.info("Run the scraper to generate the hierarchy.")

# --- Main Visualization Area (Right Side) ---
st.title("Discussion Graph Visualization")

def build_interactive_graph(data_filepath):
    """Builds a Pyvis network graph from the scraped JSON file."""
    # Initialize the interactive network 
    net = Network(height="700px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
    
    # Add physics for that smooth, interactive settling effect
    net.force_atlas_2based()
    
    if os.path.exists(data_filepath):
        with open(data_filepath, 'r') as f:
            data = json.load(f)
            
        # 1. Add the main Post node
        post = data.get("post", {})
        post_id = post.get("id", "root")
        post_label = "Original Post\n" + (post.get("author", "Unknown"))
        
        # You can customize node colors, sizes, and hover titles here
        net.add_node(post_id, label=post_label, title=post.get("title", ""), color="#ff4500", size=30)
        
        # 2. Add the Comment nodes and link them
        comments = data.get("comments", [])
        for comment in comments:
            c_id = comment["id"]
            p_id = comment["parent_id"]
            c_author = comment.get("author", "[deleted]")
            c_text = comment.get("text", "")
            
            # Add node (User)
            net.add_node(c_id, label=c_author, title=c_text, color="#1e90ff", size=15)
            
            # Add edge (Connection to parent comment or post)
            net.add_edge(c_id, p_id, color="#555555")
            
    else:
        # Placeholder if no data has been scraped yet
        net.add_node("0", label="Awaiting Data...", color="grey")

    # Save the physics graph to a temporary HTML file
    net.save_graph("temp_graph.html")
    return "temp_graph.html"

# Render the graph in the UI
graph_html_file = build_interactive_graph(DATA_FILE)

# Read the generated HTML and display it within the Streamlit app
with open(graph_html_file, 'r', encoding='utf-8') as f:
    components.html(f.read(), height=710)
