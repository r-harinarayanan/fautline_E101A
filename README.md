🧠 Semantic AI Navigation Widget

An AI-powered semantic navigation agent that understands a user’s goal, analyzes a website’s structure using Playwright + Sentence Transformers, and automatically redirects the user to the most relevant page — all via a floating browser widget.

This project combines:

🐍 Python (semantic crawling + reasoning)

🌐 Flask API (local backend)

🧩 JavaScript browser widget / Chrome extension

🤖 NLP-based intent matching (Sentence Transformers)

✨ What This Does

Instead of manually clicking through menus, users can simply say what they want, and the AI agent will:

Analyze the current website structure

Score pages and navigation links semantically

Find the best-matching page

Automatically redirect the user there

Example:

User goal: “Python basic problems”
Result: AI navigates HackerRank → Domains → Python → Basic Data Types

🏗️ Project Architecture
Browser (Any Website)
   │
   │  Widget (content.js + CSS)
   ▼
Flask API (localhost:5000)
   │
   │  Semantic reasoning
   ▼
Playwright Headless Browser
   │
   │  HTML + links
   ▼
SentenceTransformer (NLP scoring)

📂 Repository Structure
├── app.py                # Flask + Playwright semantic agent
│
├── widget/
│   ├── content.js            # Floating AI widget
│   ├── style.css             # Widget styling
│   └── manifest.json         # Chrome extension config
│
└── README.md

🚀 Features

🔍 Goal-based semantic crawling (not keyword matching)

🧭 Intelligent navigation path discovery

🧠 SentenceTransformer-based intent scoring

🕷️ Headless browser analysis with Playwright

🧩 Floating widget UI (injectable on any site)

🔁 Auto-redirect to best page

🔒 Domain-restricted crawling (safe)

⚙️ Requirements
Python

Python 3.10+ (recommended: 3.11)

Internet access (for first-time model download)

Python Packages

flask

flask-cors

playwright

sentence-transformers

scikit-learn

beautifulsoup4

📦 Backend Setup (Python)
1️⃣ Create a virtual environment (recommended)
python -m venv venv


Activate:

Windows

venv\Scripts\activate


Linux / macOS

source venv/bin/activate

2️⃣ Install dependencies
pip install flask flask-cors playwright sentence-transformers scikit-learn beautifulsoup4

3️⃣ Install Playwright browsers (IMPORTANT)
playwright install

4️⃣ Run the backend server
python app.py


You should see:

Initializing Semantic Engine...
Running on http://127.0.0.1:5000


⚠️ First run may take 1–2 minutes to download the NLP model.

🧩 Chrome Extension Setup
1️⃣ Open Chrome Extensions
chrome://extensions


Enable:

Developer mode (top right)

2️⃣ Load the extension

Click Load unpacked

Select the extension/ folder

3️⃣ Done 🎉

The widget will now appear on every website you visit.

🧪 How to Use

Open any website

Look at the bottom-right corner

Enter your goal (e.g., “python basics”)

Click Find & Auto-Open

The AI agent:

analyzes the site

finds the best page

redirects you automatically

🔐 API Endpoint
POST /find-best

Request

{
  "url": "https://example.com",
  "goal": "your intent here"
}


Response

{
  "best_url": "https://example.com/page",
  "title": "Page Title",
  "score": 0.91,
  "steps": "Home ➔ Section ➔ Target",
  "message": "Found high-potential match"
}

🧠 Why This Is Different

❌ Traditional crawlers → depth-first / brute-force
❌ Search boxes → keyword-based

✅ This system reasons semantically, like a human navigating a site.

⚠️ Known Limitations

Requires local backend running

First-time model download is slow

JS-heavy sites may limit link visibility

Login-required pages may reduce accuracy

🛠️ Future Improvements

Background service worker (no Flask dependency)

UI history + undo navigation

Graph visualization of site structure

Lightweight embedding model for faster startup

Firefox / Edge extension support

📜 License

MIT License
Free to use, modify, and extend.

🙌 Credits

Built using:

Playwright

Sentence Transformers

Flask

Chrome Extensions API
