import streamlit as st
import streamlit.components.v1 as components
import json
import os
from pyvis.network import Network

# Import the scraper class from your existing file
from redditScrape import RedditScraper

# Site shell — Reddit feed / header energy (graph uses its own dark canvas below)
_R_ORANGE = "#FF4500"
_R_ORANGE_HOT = "#FF6B35"
_R_BLUE = "#0079D3"
_R_BG = "#FFFFFF"
_R_FEED = "#DAE0E6"
_R_BORDER = "#CCC"
_R_TEXT = "#1A1A1B"
_R_META = "#787C7E"

# Pyvis graph — unchanged dark board (Streamlit chrome is Reddit-themed separately)
_GRAPH_BG = "#0e1117"
_GRAPH_FONT = "white"
_GRAPH_POST = "#ff4500"
_GRAPH_COMMENT = "#1e90ff"
_GRAPH_EDGE = "#555555"


#Daniel section test
#ff4500 orange
#1e90ff blue



# --- Configuration ---
# Makes the layout wide so the graph has plenty of room
st.set_page_config(page_title="DigEdit", layout="wide", page_icon="🔶")
DATA_FILE = "reddit_data.json"


def _inject_reddit_theme():
    st.markdown(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
        <style>
            .stApp {{
                font-family: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background-color: {_R_FEED};
                background-image:
                    radial-gradient(ellipse 120% 80% at 100% -20%, rgba(255, 69, 0, 0.14), transparent 50%),
                    radial-gradient(ellipse 80% 60% at 0% 100%, rgba(0, 121, 211, 0.08), transparent 45%);
            }}
            .stApp::before {{
                content: "";
                display: block;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 5px;
                z-index: 1000000;
                background: linear-gradient(90deg, {_R_ORANGE} 0%, {_R_ORANGE_HOT} 35%, #FFB000 100%);
                box-shadow: 0 2px 8px rgba(255, 69, 0, 0.35);
            }}
            [data-testid="stHeader"] {{
                background: linear-gradient(180deg, {_R_BG} 0%, {_R_BG} 70%, rgba(218, 224, 230, 0.5) 100%);
                border-bottom: 1px solid {_R_BORDER};
                box-shadow: 0 1px 0 rgba(255, 255, 255, 0.8) inset;
            }}
            [data-testid="stSidebar"] {{
                background: {_R_BG};
                border-right: 1px solid {_R_BORDER};
                box-shadow: 4px 0 24px rgba(0, 0, 0, 0.06);
            }}
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] .stMarkdown h1,
            [data-testid="stSidebar"] .stMarkdown h2,
            [data-testid="stSidebar"] .stMarkdown h3 {{
                color: {_R_TEXT};
                font-weight: 700;
            }}
            [data-testid="stSidebar"] h1 {{
                border-bottom: none;
                padding-bottom: 0;
                font-size: 1.35rem;
            }}
            .main .block-container {{
                padding-top: 1.35rem;
                padding-bottom: 2rem;
                background-color: {_R_BG};
                border: 1px solid {_R_BORDER};
                border-radius: 4px;
                box-shadow:
                    0 1px 3px rgba(0, 0, 0, 0.12),
                    0 4px 20px rgba(255, 69, 0, 0.08),
                    0 0 0 1px rgba(255, 255, 255, 0.6) inset;
            }}
            h1 {{
                color: {_R_TEXT};
                font-weight: 700;
                font-size: 1.65rem;
                letter-spacing: -0.03em;
                line-height: 1.2;
                border-bottom: none;
                border-left: 4px solid {_R_ORANGE};
                padding: 0.15rem 0 0.15rem 0.85rem;
                margin-bottom: 0.35rem;
                background: linear-gradient(90deg, rgba(255, 69, 0, 0.06), transparent 55%);
            }}
            .stMarkdown h3 {{
                color: {_R_TEXT};
                font-weight: 700;
                font-size: 1rem;
                margin-top: 1rem;
                padding-left: 0.5rem;
                border-left: 3px solid {_R_BLUE};
            }}
            .stTextInput label {{
                font-weight: 600 !important;
                color: {_R_META} !important;
                font-size: 0.8rem !important;
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }}
            .stTextInput input {{
                border-radius: 22px;
                border: 2px solid {_R_BORDER};
                background-color: {_R_BG};
                transition: border-color 0.15s ease, box-shadow 0.15s ease;
            }}
            .stTextInput input:focus {{
                border-color: {_R_ORANGE};
                box-shadow: 0 0 0 3px rgba(255, 69, 0, 0.2);
            }}
            div[data-testid="stExpander"] {{
                border: 1px solid {_R_BORDER};
                border-radius: 4px;
                background: linear-gradient(180deg, {_R_BG}, rgba(218, 224, 230, 0.25));
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
                transition: border-color 0.15s ease, box-shadow 0.15s ease;
            }}
            div[data-testid="stExpander"]:hover {{
                border-color: rgba(255, 69, 0, 0.45);
                box-shadow: 0 2px 8px rgba(255, 69, 0, 0.12);
            }}
            div[data-testid="stExpander"] summary {{
                font-weight: 600;
            }}
            div.stButton > button[kind="primary"] {{
                font-weight: 700 !important;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                font-size: 0.8rem !important;
                border-radius: 24px !important;
                padding: 0.5rem 1.25rem !important;
                border: none !important;
                background: linear-gradient(180deg, {_R_ORANGE_HOT}, {_R_ORANGE}) !important;
                box-shadow: 0 2px 8px rgba(255, 69, 0, 0.45) !important;
                transition: transform 0.12s ease, box-shadow 0.12s ease !important;
            }}
            div.stButton > button[kind="primary"]:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 14px rgba(255, 69, 0, 0.5) !important;
            }}
            .stSpinner > div {{
                border-top-color: {_R_ORANGE} !important;
            }}
            div[data-testid="stAlert"] {{
                border-radius: 4px;
                border-left-width: 4px;
            }}
            /* Dark pyvis canvas pops against the feed; outer frame only */
            .main iframe {{
                border-radius: 8px !important;
                border: 1px solid #1c1c1c !important;
                box-shadow:
                    0 16px 48px rgba(0, 0, 0, 0.35),
                    0 0 0 2px rgba(255, 69, 0, 0.45),
                    0 0 24px rgba(255, 107, 53, 0.15) !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


_inject_reddit_theme()

# --- Main App Layout ---
# Streamlit automatically creates a hamburger menu for the sidebar on smaller screens
with st.sidebar:
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {_R_ORANGE} 0%, {_R_ORANGE_HOT} 55%, #C62828 100%);
            margin: -1rem -1rem 1rem -1rem;
            padding: 1rem 1.1rem 1.1rem;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 6px 20px rgba(255, 69, 0, 0.35);
        ">
            <div style="display:flex;align-items:center;gap:10px;">
                <span style="font-size:1.6rem;line-height:1;" aria-hidden="true">▲</span>
                <div>
                    <div style="color:#fff;font-weight:800;font-size:1.35rem;letter-spacing:-0.04em;text-shadow:0 1px 2px rgba(0,0,0,.2);">
                        digedit
                    </div>
                    <div style="color:rgba(255,255,255,.92);font-size:0.78rem;font-weight:600;margin-top:2px;">
                        r/DigEdit · thread graph lab
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.title("Controls")
    st.markdown(
        f'<p style="margin-top:-0.4rem;color:{_R_META};font-size:0.92rem;line-height:1.45;">Paste a <strong style="color:{_R_ORANGE};">reddit.com</strong> thread URL, scrape, then pan the network on the right.</p>',
        unsafe_allow_html=True,
    )

    st.markdown("### Data intake")
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
    st.markdown("### Thread outline")
    st.caption("Expand to see the comment tree")
    
    # A basic hierarchical menu for the sidebar 
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            
        post_title = data.get("post", {}).get("title", "Unknown Post")
        with st.expander(f"📦 Root Post: {post_title[:25]}..."):
            st.write(f"**ID:** {data.get('post', {}).get('id')}")
            
            # Example of listing top-level comments under the post
            comments = data.get("comments", [])

            #temp section, daniel code
            id_to_comment = {c["id"]: c for c in comments}
            #temp section, daniel code

            for c in comments[:5]:  # Just showing the first 5 for the skeleton
                st.write(f"↳ 🗣️ {c['author']}: {c['text'][:20]}...")
            if len(comments) > 5:
                st.write("↳ *(...more comments)*")
    else:
        st.info("Run the scraper to generate the hierarchy.")

# --- Main visualization (graph iframe keeps its own dark canvas) ---
st.markdown(
    f"""
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:0 0 6px 0;">
        <span style="background:{_R_ORANGE};color:#fff;padding:5px 14px;border-radius:20px;font-weight:800;font-size:13px;letter-spacing:0.02em;box-shadow:0 2px 8px rgba(255,69,0,.35);">r/DigEdit</span>
        <span style="color:{_R_META};font-size:13px;font-weight:700;">live discussion map</span>
        <span style="margin-left:auto;color:{_R_META};font-size:12px;font-weight:600;">dark canvas · orange OP · blue replies</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.title("Discussion graph")

def build_interactive_graph(data_filepath):
    """Builds a Pyvis network graph from the scraped JSON file."""
    # Initialize the interactive network 
    net = Network(
        height="700px",
        width="100%",
        bgcolor=_GRAPH_BG,
        font_color=_GRAPH_FONT,
        directed=True,
    )
    
    # Add physics for that smooth, interactive settling effect
    net.force_atlas_2based()
    
    if os.path.exists(data_filepath):
        with open(data_filepath, 'r') as f:
            data = json.load(f)
            
        # 1. Add the main Post node
        def get_depth(comment_id, id_to_comment, root_id):
            """Calculate depth (number of hops from root post)."""
            depth = 0
            current_id = comment_id
            while current_id != root_id:
                parent_id = id_to_comment.get(current_id, {}).get("parent_id", root_id)
                if parent_id == current_id:  # safety to prevent infinite loop
                    break
                current_id = parent_id
                depth += 1
            return depth
        
        post = data.get("post", {})
        post_id = post.get("id", "root")
        post_label = "Original Post\n" + (post.get("author", "Unknown"))
        
        # You can customize node colors, sizes, and hover titles here
        net.add_node(post_id, label=post_label, title=post.get("title", ""), color=_GRAPH_POST, size=30)
        
        # 2. Add the Comment nodes with alternating colors based on depth
        for comment in comments:
            c_id = comment["id"]
            p_id = comment["parent_id"]
            c_author = comment.get("author", "[deleted]")
            c_text = comment.get("text", "")
            
            # Calculate depth
            depth = get_depth(c_id, id_to_comment, post_id)
            
            # Alternate colors: even depth = orange, odd depth = blue
            color = _GRAPH_POST if depth % 2 == 0 else _GRAPH_COMMENT
            
            # Add node and edge
            net.add_node(c_id, label=c_author, title=c_text, color=color, size=15)
            net.add_edge(c_id, p_id, color=_GRAPH_EDGE)
            
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
