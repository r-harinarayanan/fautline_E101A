"""
end.py  —  Standalone semantic crawler (no Flask, runs from terminal).

Usage:
    python end.py

Prompts you for a start URL and a search goal, then crawls
and prints the best-matching page it finds.
"""

import sys
from collections import deque
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Windows fix — must be at module level
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ================= CONFIG =================
MAX_DEPTH        = 6
MAX_PAGES        = 40
TIMEOUT          = 15_000
TOP_K_LINKS      = 3
SIM_THRESHOLD    = 0.25
INTENT_THRESHOLD = 0.65
# ==========================================

model = SentenceTransformer("all-MiniLM-L6-v2")


def normalize_url(url: str) -> str:
    url, _ = urldefrag(url)
    return url.rstrip("/")


def is_login_page(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("input", {"type": "password"}):
        return True
    text = soup.get_text(" ", strip=True).lower()
    return "sign in" in text or "log in" in text


def extract_page_text(html: str, max_chars: int = 3000) -> str:
    soup      = BeautifulSoup(html, "html.parser")
    headings  = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")][:20]
    return " ".join(headings + paragraphs)[:max_chars]


def extract_links(html: str, base_url: str, domain: str) -> list[dict]:
    """Return deduplicated, same-domain links only."""
    soup  = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links = []
    for a in soup.find_all("a", href=True):
        label = a.get_text(strip=True)
        href  = normalize_url(urljoin(base_url, a["href"]))
        if (
            label
            and href.startswith("http")
            and urlparse(href).netloc == domain
            and href not in seen
        ):
            seen.add(href)
            links.append({"label": label, "url": href})
    return links


def score_links(query_emb, links: list[dict]) -> list[dict]:
    if not links:
        return []
    labels    = [l["label"] for l in links]
    label_emb = model.encode(labels)
    scores    = cosine_similarity(query_emb, label_emb)[0]
    for link, score in zip(links, scores):
        link["score"] = float(score)
    return sorted(links, key=lambda x: x["score"], reverse=True)


def crawl(start_url: str, user_query: str):
    """
    Iterative BFS crawl.
    Returns (graph, best_page) where:
      graph     = {url: [scored_link, ...]}
      best_page = {"url": ..., "score": ..., "path": ...}
    """
    start_url  = normalize_url(start_url)
    domain     = urlparse(start_url).netloc
    query_emb  = model.encode([user_query])

    visited: set[str]  = set()
    graph: dict        = {}
    best_page          = {"url": start_url, "score": 0.0, "path": "Home"}

    # (url, depth, breadcrumb)
    queue: deque = deque([(start_url, 0, "Home")])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        while queue and len(visited) < MAX_PAGES:
            url, depth, path = queue.popleft()
            url = normalize_url(url)

            if depth > MAX_DEPTH or url in visited:
                continue

            visited.add(url)
            print(f"\n[depth={depth}]  {url}")

            page = context.new_page()
            try:
                page.goto(url, timeout=TIMEOUT)
                try:
                    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
                except PlaywrightTimeout:
                    pass   # proceed with whatever loaded
                html = page.content()
            except PlaywrightTimeout:
                print("  Timed out — skipping.")
                page.close()
                continue
            except Exception as e:
                print(f"  Error: {e}")
                page.close()
                continue

            # Handle login walls
            if is_login_page(html):
                print("  Login wall detected. Please log in manually.")
                input("  Press Enter after logging in...")
                html = page.content()

            page_text     = extract_page_text(html)
            content_score = 0.0
            if page_text.strip():
                text_emb      = model.encode([page_text])
                content_score = float(cosine_similarity(query_emb, text_emb)[0][0])

            print(f"  Content score: {content_score:.3f}")

            if content_score > best_page["score"]:
                best_page = {"url": url, "score": content_score, "path": path}

            links  = extract_links(html, url, domain)
            scored = score_links(query_emb, links)
            graph[url] = scored
            page.close()

            # Stop early if we're confident enough
            if content_score >= INTENT_THRESHOLD:
                print("\n  Intent satisfied — stopping crawl.")
                break

            # Enqueue top-K links
            added = 0
            for link in scored:
                if added >= TOP_K_LINKS:
                    break
                if link["score"] >= SIM_THRESHOLD and link["url"] not in visited:
                    queue.append((link["url"], depth + 1, f"{path} -> {link['label']}"))
                    added += 1

        print("\nCrawl complete. Browser kept open — press Enter to close.")
        input()
        browser.close()

    return graph, best_page


def print_graph(graph: dict) -> None:
    print("\n========= NAVIGATION GRAPH =========")
    for page_url, links in graph.items():
        print(f"\nPAGE: {page_url}")
        for link in links[:5]:
            print(f"  └─ {link['label']:<40} score={link['score']:.2f}  ->  {link['url']}")


if __name__ == "__main__":
    start = input("Start URL (press Enter for Wikipedia): ").strip()
    if not start:
        start = "https://en.wikipedia.org/wiki/Main_Page"

    query = input("What are you looking for? ").strip()
    if not query:
        print("No query entered. Exiting.")
        sys.exit(1)

    graph, best = crawl(start, query)
    print_graph(graph)

    print("\n========= BEST MATCH =========")
    print(f"URL  :  {best['url']}")
    print(f"Score:  {best['score']:.3f}")
    print(f"Path :  {best['path']}")