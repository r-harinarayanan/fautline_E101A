import sys
import os
import threading
from collections import deque
from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from urllib.parse import urljoin, urlparse, urldefrag
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Windows asyncio fix — must be at module level
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ================= CONFIG =================
MAX_DEPTH        = 4
TIMEOUT          = 15000
SIM_THRESHOLD    = 0.20
GOAL_THRESHOLD   = 0.70
TOP_K_LINKS      = 3
MAX_PAGES        = 30
ALLOWED_SCHEMES  = {"http", "https"}
# ==========================================

app = Flask(__name__)
CORS(app)

print("Initializing Semantic Engine...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Playwright sync API is NOT thread-safe.
# This lock ensures only one crawl runs at a time.
_playwright_lock = threading.Lock()


def normalize_url(url: str) -> str:
    url, _ = urldefrag(url)
    return url.rstrip("/")


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ALLOWED_SCHEMES and bool(parsed.netloc)
    except Exception:
        return False


class SemanticAgent:
    def __init__(self, start_url: str, user_query: str):
        self.start_url  = normalize_url(start_url)
        self.domain     = urlparse(start_url).netloc
        self.query      = user_query
        self.query_emb  = model.encode([user_query])   # encode once, reuse everywhere
        self.visited: set[str]  = set()
        self.results:  list[dict] = []

    def extract_page_data(self, html: str, current_url: str):
        soup = BeautifulSoup(html, "html.parser")

        headings   = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")][:15]
        page_text  = " ".join(headings + paragraphs)

        # Deduplicate links before scoring
        seen_hrefs: set[str] = set()
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = normalize_url(urljoin(current_url, a["href"]))
            if (
                text
                and href.startswith("http")
                and urlparse(href).netloc == self.domain
                and href not in seen_hrefs
            ):
                seen_hrefs.add(href)
                links.append({"label": text, "url": href})

        return page_text, links

    def get_scores(self, text_list: list[str]) -> list[float]:
        if not text_list:
            return []
        clean      = [t if t.strip() else " " for t in text_list]
        embeddings = model.encode(clean)
        return cosine_similarity(self.query_emb, embeddings)[0]

    def run(self) -> list[dict]:
        # deque gives O(1) popleft vs O(n) list.pop(0)
        queue: deque = deque([(self.start_url, 0, "Home")])

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            try:
                while queue and len(self.visited) < MAX_PAGES:
                    url, depth, path = queue.popleft()

                    if url in self.visited or depth > MAX_DEPTH:
                        continue

                    print(f"  Analyzing: {url} (depth={depth})")
                    self.visited.add(url)
                    page = context.new_page()

                    try:
                        page.goto(url, timeout=TIMEOUT, wait_until="networkidle")
                        html = page.content()
                        page_text, links = self.extract_page_data(html, url)

                        content_score = (
                            float(self.get_scores([page_text])[0])
                            if page_text.strip() else 0.0
                        )
                        self.results.append({
                            "url":   url,
                            "score": round(content_score, 3),
                            "title": page.title(),
                            "steps": path,
                        })

                        if content_score >= GOAL_THRESHOLD:
                            print(f"  Match found! Score: {content_score:.3f}")
                            break

                        if links:
                            labels     = [l["label"] for l in links]
                            scores     = self.get_scores(labels)
                            for i, link in enumerate(links):
                                link["score"] = float(scores[i])
                            top_links  = sorted(links, key=lambda x: x["score"], reverse=True)

                            added = 0
                            for link in top_links:
                                if added >= TOP_K_LINKS:
                                    break
                                if (
                                    link["score"] > SIM_THRESHOLD
                                    and link["url"] not in self.visited
                                ):
                                    queue.append((
                                        link["url"],
                                        depth + 1,
                                        f"{path} -> {link['label']}",
                                    ))
                                    added += 1

                    except Exception as e:
                        print(f"  Error on {url}: {e}")
                    finally:
                        page.close()

            finally:
                context.close()
                browser.close()

        return sorted(self.results, key=lambda x: x["score"], reverse=True)


@app.route("/find-best", methods=["POST"])
def find_best():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    url  = data.get("url",  "").strip()
    goal = data.get("goal", "").strip()

    if not url or not goal:
        return jsonify({"error": "Both 'url' and 'goal' are required"}), 400

    if not is_valid_url(url):
        return jsonify({"error": "Invalid URL — must start with http:// or https://"}), 400

    if len(goal) > 500:
        return jsonify({"error": "'goal' must be 500 characters or fewer"}), 400

    # Serialize all Playwright calls — not thread-safe
    acquired = _playwright_lock.acquire(timeout=60)
    if not acquired:
        return jsonify({"error": "Server busy. Please try again shortly."}), 503

    try:
        agent    = SemanticAgent(url, goal)
        findings = agent.run()
    finally:
        _playwright_lock.release()

    if not findings:
        return jsonify({"message": "No relevant content found.", "score": 0})

    best = findings[0]
    return jsonify({
        "best_url": best["url"],
        "title":    best["title"],
        "score":    best["score"],
        "steps":    best["steps"],
        "message":  f"Found: {best['title']}",
    })


if __name__ == "__main__":
    app.run(port=5000, debug=False, threaded=False)