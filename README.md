# Semantic AI Navigation Agent

An AI-powered web navigation system that understands **what you're looking for**, crawls a website's structure using a headless browser, and automatically redirects you to the most relevant page — without keyword matching.

Built for [Hacktide](https://github.com/sreenand-tm/fautline_E101A) hackathon.

---

## The Problem

Traditional search boxes rely on exact keyword matching. If you visit an unfamiliar site and type *"python basics"*, you might get zero results or end up on the wrong page. Navigation menus require you to already know the site's structure.

**This project solves that.** Just tell it what you want in plain English — the AI figures out where to go.

---

## How It Works

```
Browser (any website)
       │
       │  You type: "python basic problems"
       ▼
Chrome Extension Widget  (content.js)
       │
       │  POST { url, goal }
       ▼
Flask API  (backend/app.py)
       │
       ▼
SemanticAgent
  ├── Loads the page with Playwright (headless Chromium)
  ├── Extracts headings, paragraphs, and all internal links
  ├── Encodes page content + link labels using SentenceTransformers
  ├── Scores each candidate using cosine similarity vs your goal
  ├── Follows the top-K most relevant links (BFS)
  └── Returns the best-matching URL
       │
       ▼
Widget auto-redirects you there
```

---

## Project Structure

```
fautline_E101A/
├── backend/
│   ├── app.py          # Flask API + SemanticAgent (server mode)
│   └── end.py          # Standalone CLI crawler (testing / demo)
├── extension/
│   ├── manifest.json   # Chrome Extension config
│   ├── content.js      # Floating widget injected on every page
│   └── style.css       # Widget styling
└── README.md
```

---

## Features

- **Semantic intent matching** — uses sentence embeddings, not keyword search
- **BFS crawl with scoring** — explores the site intelligently, not randomly
- **Goal threshold** — stops as soon as a high-confidence match is found
- **Domain-restricted** — never crawls outside the current site
- **Duplicate URL deduplication** — avoids re-scoring the same link dozens of times
- **Thread-safe API** — Playwright lock prevents crashes on concurrent requests
- **Minimizable widget** — close or collapse the UI without losing your session
- **XSS protection** — page titles are escaped before rendering in the widget
- **Configurable** — all thresholds adjustable via constants at the top of each file

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI / NLP | `sentence-transformers` (all-MiniLM-L6-v2) |
| Similarity | `scikit-learn` cosine similarity |
| Browser automation | `Playwright` (headless Chromium) |
| HTML parsing | `BeautifulSoup4` |
| Backend API | `Flask` + `flask-cors` |
| Frontend | Chrome Extension (Manifest V3) |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/r-harinarayanan/fautline_E101A.git
cd fautline_E101A
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install flask flask-cors playwright sentence-transformers scikit-learn beautifulsoup4
```

### 4. Install Playwright browsers

```bash
playwright install
```

> First run downloads the NLP model (~90 MB). This only happens once.

### 5. Start the backend

```bash
cd backend
python app.py
```

You should see:
```
Initializing Semantic Engine...
 * Running on http://127.0.0.1:5000
```

### 6. Load the Chrome Extension

1. Open Chrome and go to `chrome://extensions`
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder
5. Done — the widget appears on every website

---

## API

### `POST /find-best`

**Request**
```json
{
  "url": "https://www.hackerrank.com",
  "goal": "python basic problems"
}
```

**Response**
```json
{
  "best_url": "https://www.hackerrank.com/domains/python",
  "title":    "Python | HackerRank",
  "score":    0.847,
  "steps":    "Home -> Domains -> Python",
  "message":  "Found: Python | HackerRank"
}
```

**Error responses**

| Status | Meaning |
|---|---|
| 400 | Missing URL / goal, or invalid URL format |
| 503 | Server busy (another crawl in progress) |

---

## Standalone CLI (no extension needed)

```bash
cd backend
python end.py
```

Prompts you for a start URL and goal, opens a visible browser, and prints the navigation graph + best match.

---

## Known Limitations

- Requires the local backend to be running
- JavaScript-heavy SPAs may hide links until interaction
- Login-protected pages reduce accuracy
- One crawl at a time (sequential by design for stability)

---

## Future Improvements

- [ ] Background service worker (remove Flask dependency)
- [ ] Persistent embedding cache across sessions
- [ ] Priority queue BFS (score-weighted traversal)
- [ ] Dynamic interaction (click dropdowns to reveal hidden links)
- [ ] Firefox / Edge extension support
- [ ] Graph visualization of explored site structure

---

## Use Cases

- Quickly navigate unfamiliar documentation sites
- Automation agents that need to find specific content
- Accessibility tool for users who struggle with site navigation
- Research assistance on large knowledge bases

---

## License

MIT — free to use, modify, and extend.