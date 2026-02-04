
# AI-Assisted Academic Search (Streamlit + Semantic Scholar + Gemini)

This document summarizes all implementation decisions and technical knowledge needed to build the project.

---

## Core Idea

Build a minimal Streamlit app where:

1. User enters a human research topic.
2. Gemini generates 3 academically optimized query variants.
3. User clicks one variant.
4. App fetches 10 most relevant papers from Semantic Scholar.
5. Papers are displayed on the main page.

No re-ranking, no caching, no PDF parsing.

---

## Pipeline

### Step 1 – Human Input
User provides a single free-text topic, e.g.

"ai systems people can trust"

---

### Step 2 – Gemini Query Generation

Gemini receives only the human query and returns JSON:

```json
{
  "broad": "...",
  "focused": "...",
  "method": "..."
}
```

Each value is a plain keyword-rich academic query string.

---

### Step 3 – User Selection

UI shows 3 clickable options.
Clicking one automatically triggers search.

---

### Step 4 – Semantic Scholar Search

Endpoint:

GET https://api.semanticscholar.org/graph/v1/paper/search

Parameters:
- query=<string>
- limit=10
- fields=title,abstract,year,authors,venue,url,citationCount

Response shape:

{
  "total": int,
  "offset": int,
  "next": int,
  "data": [paper objects]
}

---

## Required Paper Fields

Only include papers that contain:

- paperId
- title
- abstract
- year
- authors (non-empty)
- url

Optional (display if present):
- venue
- citationCount

---

## Frontend Layout

### Sidebar
- Human topic input
- Button: Generate academic queries

### Main
- 3 clickable query variants
- Below: 10 paper cards

Each paper card shows:
- Title (clickable)
- Authors
- Year
- Venue (optional)
- Citation count (optional)
- Abstract snippet
- External link

---

## Streamlit Secrets

All API keys must be stored in Streamlit Secrets:

In Streamlit Cloud UI:
- GEMINI_API_KEY="..."
- SEMANTIC_SCHOLAR_API_KEY="..." (optional)

In code:
st.secrets["GEMINI_API_KEY"]

Never commit keys to GitHub.

---

## No Caching

No st.cache.
Each click makes a fresh API call.

Guard against multiple accidental calls using session_state flags.

---

## Why This Is Not Redundant

Semantic Scholar = discovery.
This app = semantic query formulation using LLM.

Core value:
Human intent → AI academic translation → classical search engine.

---

## Minimal Tech Stack

- Streamlit
- requests
- Gemini API
- Semantic Scholar Graph API

Single file implementation possible.

---

## Justification Sentence (for report)

"We use a large language model to transform human research intentions into academically optimized search queries, which are then executed via the Semantic Scholar API to retrieve relevant literature."

---
