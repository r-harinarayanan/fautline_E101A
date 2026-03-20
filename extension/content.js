// Prevent duplicate injection on SPA navigations or extension reloads
if (document.getElementById("semantic-ai-widget")) {
    // Widget already on this page — do nothing
} else {

    const BACKEND_URL = "http://127.0.0.1:5000";

    // ── Build widget HTML ─────────────────────────────────────────
    const widget = document.createElement("div");
    widget.id = "semantic-ai-widget";
    widget.innerHTML = `
        <div id="saw-header">
            <span id="saw-title">AI Scout Agent</span>
            <div id="saw-controls">
                <button id="saw-minimize" title="Minimize">—</button>
                <button id="saw-close"    title="Close">✕</button>
            </div>
        </div>
        <div id="saw-body">
            <input
                type="text"
                id="saw-goal"
                placeholder="What are you looking for?"
                autocomplete="off"
                aria-label="Search goal"
            />
            <button id="saw-find">Find &amp; Auto-Open</button>
            <div id="saw-result" aria-live="polite">Enter a goal to start scouting...</div>
        </div>
    `;
    document.body.appendChild(widget);

    // ── Element refs ──────────────────────────────────────────────
    const body      = document.getElementById("saw-body");
    const goalInput = document.getElementById("saw-goal");
    const findBtn   = document.getElementById("saw-find");
    const resultBox = document.getElementById("saw-result");
    const minBtn    = document.getElementById("saw-minimize");
    const closeBtn  = document.getElementById("saw-close");

    // ── Minimize / Close ──────────────────────────────────────────
    let minimized = false;
    minBtn.addEventListener("click", () => {
        minimized = !minimized;
        body.style.display   = minimized ? "none" : "block";
        minBtn.textContent   = minimized ? "+" : "—";
        minBtn.title         = minimized ? "Expand" : "Minimize";
    });

    closeBtn.addEventListener("click", () => widget.remove());

    // ── Enter key triggers search ─────────────────────────────────
    goalInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") findBtn.click();
    });

    // ── Sanitize output to prevent XSS ───────────────────────────
    function escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    // ── Main search logic ─────────────────────────────────────────
    findBtn.addEventListener("click", async () => {
        const goal = goalInput.value.trim();
        if (!goal) {
            resultBox.innerHTML = "⚠️ Please enter a goal first.";
            return;
        }

        // Prevent double-submit while a crawl is running
        findBtn.disabled    = true;
        findBtn.textContent = "Searching...";
        resultBox.innerHTML = "Scouting... analysing site structure.";

        try {
            const response = await fetch(`${BACKEND_URL}/find-best`, {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ url: window.location.href, goal }),
                signal:  AbortSignal.timeout(120_000),   // 2-min client timeout
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                resultBox.innerHTML = `❌ Error: ${err.error || response.statusText}`;
                return;
            }

            const data = await response.json();

            if (data.best_url) {
                resultBox.innerHTML =
                    `<span class="saw-success">Found: ${escapeHtml(data.title)}</span>` +
                    `<br><small>Score: ${data.score} — redirecting in 1s...</small>`;

                setTimeout(() => { window.location.href = data.best_url; }, 1200);
            } else {
                resultBox.innerHTML = "❌ No relevant pages found.";
            }

        } catch (err) {
            if (err.name === "TimeoutError") {
                resultBox.innerHTML = "❌ Timed out. Backend may still be crawling.";
            } else {
                resultBox.innerHTML =
                    "❌ Cannot reach backend.<br>" +
                    "<small>Make sure <code>app.py</code> is running on port 5000.</small>";
            }
        } finally {
            findBtn.disabled    = false;
            findBtn.textContent = "Find & Auto-Open";
        }
    });
}