import streamlit as st
import requests
import json
import google.generativeai as genai

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

st.set_page_config(page_title="AI Academic Search", layout="wide", page_icon="🔍")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
PAPER_FIELDS = "title,abstract,year,authors,venue,url,citationCount"

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* --- Main container spacing --- */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* --- Hero header --- */
    .hero {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
    }
    .hero h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .hero p {
        color: #6b7280;
        font-size: 1.05rem;
        margin-top: 0;
    }

    /* --- Query variant cards --- */
    .query-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 0.5rem;
        transition: box-shadow 0.2s, border-color 0.2s;
    }
    .query-card:hover {
        border-color: #94a3b8;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .query-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    .query-label.broad { color: #2563eb; }
    .query-label.focused { color: #059669; }
    .query-label.method { color: #9333ea; }
    .query-text {
        color: #1e293b;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* --- Paper card --- */
    .paper-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: box-shadow 0.2s, border-color 0.2s;
    }
    .paper-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.07);
    }
    .paper-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 0.4rem;
    }
    .paper-title a {
        color: #1e40af;
        text-decoration: none;
    }
    .paper-title a:hover {
        text-decoration: underline;
    }
    .paper-meta {
        font-size: 0.88rem;
        color: #64748b;
        margin-bottom: 0.5rem;
    }
    .paper-badges {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-bottom: 0.6rem;
    }
    .badge {
        display: inline-block;
        font-size: 0.78rem;
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        font-weight: 500;
    }
    .badge-year {
        background: #eff6ff;
        color: #2563eb;
    }
    .badge-venue {
        background: #f0fdf4;
        color: #15803d;
    }
    .badge-cite {
        background: #faf5ff;
        color: #7c3aed;
    }
    .paper-abstract {
        font-size: 0.92rem;
        color: #475569;
        line-height: 1.65;
    }

    /* --- Sidebar polish --- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }
    [data-testid="stSidebar"] hr {
        border-color: #e2e8f0;
    }

    /* --- Results header --- */
    .results-header {
        display: flex;
        align-items: baseline;
        gap: 0.6rem;
        margin-bottom: 0.25rem;
    }
    .results-count {
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 400;
    }

    /* --- Selected query chip --- */
    .selected-query {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin-bottom: 1.25rem;
        font-size: 0.9rem;
        color: #1e40af;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "queries" not in st.session_state:
    st.session_state.queries = None
if "papers" not in st.session_state:
    st.session_state.papers = None
if "selected_query" not in st.session_state:
    st.session_state.selected_query = None

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def generate_queries(topic: str) -> dict:
    """Ask Gemini to produce three academic query variants."""
    prompt = (
        "Given a research topic, generate 3 academic search query variants.\n"
        "Return ONLY valid JSON in this exact format:\n"
        "{\n"
        '  "broad": "general academic query covering the topic widely",\n'
        '  "focused": "specific query targeting core concepts",\n'
        '  "method": "query emphasizing methodologies and techniques"\n'
        "}\n\n"
        f"Topic: {topic}"
    )
    response = model.generate_content(prompt)
    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def search_papers(query: str) -> list:
    """Fetch papers from Semantic Scholar."""
    params = {"query": query, "limit": 10, "fields": PAPER_FIELDS}
    headers = {}
    if "SEMANTIC_SCHOLAR_API_KEY" in st.secrets:
        headers["x-api-key"] = st.secrets["SEMANTIC_SCHOLAR_API_KEY"]

    resp = requests.get(SEMANTIC_SCHOLAR_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    # Keep only papers with all required fields
    filtered = []
    for p in data:
        if (
            p.get("paperId")
            and p.get("title")
            and p.get("abstract")
            and p.get("year")
            and p.get("authors")
            and p.get("url")
        ):
            filtered.append(p)
    return filtered


def render_paper_card(paper: dict):
    """Render a styled paper card using HTML."""
    title = paper["title"]
    url = paper["url"]
    authors = ", ".join(a["name"] for a in paper["authors"])
    year = paper["year"]
    abstract = paper["abstract"]
    if len(abstract) > 300:
        abstract = abstract[:300] + "..."

    badges_html = f'<span class="badge badge-year">{year}</span>'
    if paper.get("venue"):
        badges_html += f'<span class="badge badge-venue">{paper["venue"]}</span>'
    if paper.get("citationCount") is not None:
        cite = paper["citationCount"]
        badges_html += f'<span class="badge badge-cite">{cite} citations</span>'

    st.markdown(f"""
    <div class="paper-card">
        <div class="paper-title"><a href="{url}" target="_blank">{title}</a></div>
        <div class="paper-meta">{authors}</div>
        <div class="paper-badges">{badges_html}</div>
        <div class="paper-abstract">{abstract}</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Research Topic")
    ai_enabled = st.toggle("AI query recommendations", value=True)
    if ai_enabled:
        st.caption("Enter a topic and let AI generate optimized academic queries.")
    else:
        st.caption("Your query will be sent directly to Semantic Scholar.")
    topic = st.text_input(
        "Topic",
        placeholder="e.g. ai systems people can trust",
        label_visibility="collapsed",
    )
    if ai_enabled:
        action_btn = st.button("Generate Academic Queries", use_container_width=True, type="primary")
    else:
        action_btn = st.button("Search Papers", use_container_width=True, type="primary")
    st.divider()
    st.markdown(
        '<p style="font-size:0.8rem;color:#94a3b8;">'
        "Powered by Gemini + Semantic Scholar"
        "</p>",
        unsafe_allow_html=True,
    )

if action_btn and topic:
    if ai_enabled:
        with st.spinner("Generating queries with Gemini..."):
            try:
                st.session_state.queries = generate_queries(topic)
                st.session_state.papers = None
                st.session_state.selected_query = None
            except Exception as e:
                st.error(f"Failed to generate queries: {e}")
    else:
        st.session_state.queries = None
        st.session_state.selected_query = topic
        with st.spinner("Searching Semantic Scholar..."):
            try:
                st.session_state.papers = search_papers(topic)
            except Exception as e:
                st.error(f"Search failed: {e}")
                st.session_state.papers = None

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="hero">'
    "<h1>AI-Assisted Academic Search</h1>"
    "<p>Transform your research ideas into precise academic queries</p>"
    "</div>",
    unsafe_allow_html=True,
)

if st.session_state.queries:
    st.markdown("")  # spacer
    cols = st.columns(3, gap="medium")
    variant_meta = {
        "broad": ("Broad", "broad"),
        "focused": ("Focused", "focused"),
        "method": ("Method", "method"),
    }

    for idx, (key, (label, css_class)) in enumerate(variant_meta.items()):
        with cols[idx]:
            query_text = st.session_state.queries[key]
            st.markdown(
                f'<div class="query-card">'
                f'<div class="query-label {css_class}">{label}</div>'
                f'<div class="query-text">{query_text}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"Search with {label}", key=f"btn_{key}", use_container_width=True):
                st.session_state.selected_query = query_text
                with st.spinner("Searching Semantic Scholar..."):
                    try:
                        st.session_state.papers = search_papers(query_text)
                    except Exception as e:
                        st.error(f"Search failed: {e}")
                        st.session_state.papers = None

if st.session_state.selected_query:
    st.markdown(
        f'<div class="selected-query">Showing results for: <strong>{st.session_state.selected_query}</strong></div>',
        unsafe_allow_html=True,
    )

if st.session_state.papers is not None:
    if len(st.session_state.papers) == 0:
        st.warning("No papers matched the required fields. Try another query.")
    else:
        st.markdown(
            f'<div class="results-header">'
            f"<h3>Papers</h3>"
            f'<span class="results-count">{len(st.session_state.papers)} results</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
        for paper in st.session_state.papers:
            render_paper_card(paper)
