import sys
import asyncio
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from urllib.parse import urljoin, urlparse, urldefrag
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ================= CONFIG =================
MAX_DEPTH = 4
TIMEOUT = 15000
SIM_THRESHOLD = 0.35
GOAL_THRESHOLD = 0.85
TOP_K_LINKS = 3
# =========================================

app = Flask(__name__)
CORS(app)

print("🔄 Initializing Semantic Engine...")
model = SentenceTransformer("all-MiniLM-L6-v2")


def normalize_url(url):
    url, _ = urldefrag(url)
    return url.rstrip("/")


class SemanticAgent:
    def __init__(self, start_url, user_query):
        self.start_url = normalize_url(start_url)
        self.domain = urlparse(start_url).netloc
        self.query = user_query
        self.query_emb = model.encode([user_query])
        self.visited = set()
        self.results = []

    def extract_page_data(self, html, current_url):
        soup = BeautifulSoup(html, "html.parser")
        # Extract headings and paragraphs for page scoring
        headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")][:15]
        page_text = " ".join(headings + paragraphs)

        # Extract internal links for navigation scoring
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = normalize_url(urljoin(current_url, a["href"]))
            if text and href.startswith("http") and urlparse(href).netloc == self.domain:
                links.append({"label": text, "url": href})
        return page_text, links

    def get_scores(self, text_list):
        if not text_list: return []
        embeddings = model.encode(text_list)
        return cosine_similarity(self.query_emb, embeddings)[0]

    def run(self):
        # Mandatory Windows fix for Playwright + Asyncio
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # Queue stores: (url, current_depth, path_string)
        queue = [(self.start_url, 0, "Home")]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            while queue:
                url, depth, path = queue.pop(0)
                if url in self.visited or depth > MAX_DEPTH:
                    continue

                print(f"🕷️ Analyzing: {url} (Depth: {depth})")
                self.visited.add(url)
                page = context.new_page()

                try:
                    page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")
                    html = page.content()
                    page_text, links = self.extract_page_data(html, url)

                    # 1. Score the content of the current page
                    content_score = float(self.get_scores([page_text])[0]) if page_text else 0
                    self.results.append({
                        "url": url,
                        "score": round(content_score, 3),
                        "title": page.title(),
                        "steps": path
                    })

                    # 2. Check for the "Eureka" threshold
                    if content_score >= GOAL_THRESHOLD:
                        print(f"🎯 MATCH FOUND! Score: {content_score}")
                        break

                    # 3. Score links to decide where to go next
                    if links:
                        labels = [l["label"] for l in links]
                        link_scores = self.get_scores(labels)

                        scored_links = []
                        for i, link in enumerate(links):
                            link["score"] = float(link_scores[i])
                            scored_links.append(link)

                        scored_links.sort(key=lambda x: x["score"], reverse=True)

                        added = 0
                        for l in scored_links:
                            if added < TOP_K_LINKS and l["score"] > SIM_THRESHOLD:
                                if l["url"] not in self.visited:
                                    # Create new breadcrumb path
                                    new_path = f"{path} ➔ {l['label']}"
                                    queue.append((l["url"], depth + 1, new_path))
                                    added += 1
                except Exception as e:
                    print(f"⚠️ Error on {url}: {e}")
                finally:
                    page.close()
            browser.close()

        return sorted(self.results, key=lambda x: x["score"], reverse=True)


@app.route('/find-best', methods=['POST'])
def find_best():
    data = request.json
    url = data.get('url')
    goal = data.get('goal')

    if not url or not goal:
        return jsonify({"error": "Missing URL or Goal"}), 400

    agent = SemanticAgent(url, goal)
    findings = agent.run()

    if not findings:
        return jsonify({"message": "No relevant content found.", "score": 0})

    # Return the absolute best finding
    best = findings[0]
    return jsonify({
        "best_url": best["url"],
        "title": best["title"],
        "score": best["score"],
        "steps": best["steps"],
        "message": f"Found high-potential match: {best['title']}"
    })


if __name__ == '__main__':
    # Running on port 5000 for the Chrome Extension
    app.run(port=5000) 
