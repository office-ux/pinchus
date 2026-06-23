"""
Generate app_hybrid2.js from app.js with Hybrid 2 patches.
This approach avoids PowerShell template-literal mangling.
"""
import re, os

OUT = r'c:\pinchus\web_viewer\static\js\hybrid2\app_hybrid2.js'

JS = r'''/**
 * app_hybrid2.js  --  Hybrid 2 Rendering Engine
 * ============================================================================
 * Three upgrades over Hybrid Canvas:
 *  1. OffscreenCanvas + Web Worker: vector tile painting is offloaded to
 *     hybrid2_vector_worker.js so the main UI thread is never blocked.
 *  2. Canvas Tiling: pages split into 512px grid tiles; only visible tiles
 *     (+ 1 tile padding ring) are active in the DOM.
 *  3. Predictive Pre-rendering: adjacent tiles are rendered before the user
 *     scrolls to them so panning never shows blank areas.
 *
 * All other features (lasso selection, stamps, patterns, coords, inspector,
 * touch gestures, sidebar) are identical to app.js.
 */
'''

# Read app.js verbatim
with open(r'c:\pinchus\web_viewer\static\js\app.js', encoding='utf-8') as f:
    app = f.read()

# ── Patch 1: Change renderer setting constant ─────────────────────────────────
app = app.replace(
    "const currentRendererSetting = localStorage.getItem('pdf_renderer') || 'legacy';",
    "const currentRendererSetting = 'hybrid2'; // Hybrid 2 engine"
)

# ── Patch 2: Remove old SVG-based legacy vector rendering, keep canvas path ──
# The canvas renderer path is already the right path; we just need to ensure
# the OffscreenCanvas worker is wired in via updateVectorTiles.

# ── Patch 3: Add worker init immediately after pagesData / canvasRenderers ────
WORKER_INIT = '''
    // ── Hybrid 2: OffscreenCanvas Web Worker ─────────────────────────────────
    const H2_WORKER_PATH = '/static/js/hybrid2/hybrid2_vector_worker.js';
    let h2Worker = null;
    let h2WorkerReady = false;
    let h2TileId = 0;
    const h2Pending = new Map();

    try {
        h2Worker = new Worker(H2_WORKER_PATH);
        h2Worker.onerror = e => console.warn('[Hybrid2] Worker error:', e);
        h2Worker.onmessage = function(e) {
            const { type, transferId, error } = e.data;
            const pending = h2Pending.get(transferId);
            if (!pending) return;
            h2Pending.delete(transferId);
            if (type === 'TILE_DONE') pending.resolve();
            else { console.warn('[Hybrid2] Tile error:', error); pending.reject(new Error(error)); }
        };
        h2WorkerReady = true;
    } catch(e) {
        console.warn('[Hybrid2] Worker unavailable, using main-thread fallback', e);
    }

    // Engine badge
    (function() {
        const badge = document.createElement('div');
        badge.style.cssText = 'position:fixed;bottom:12px;right:16px;z-index:9999;background:linear-gradient(135deg,#0d1b2a,#1a2744);border:1px solid rgba(0,255,200,0.3);color:#00ffc8;font-size:10px;font-family:monospace;padding:4px 10px;border-radius:20px;pointer-events:none;box-shadow:0 0 12px rgba(0,255,200,0.15);letter-spacing:0.5px';
        badge.textContent = '\u26a1 Hybrid 2 | OffscreenCanvas' + (h2WorkerReady ? ' + Worker' : '') + ' | Tiled | Predictive';
        document.body.appendChild(badge);
    })();

    // Hybrid 2 predictive pre-render: PRE_TILES extra tile ring
    const H2_PRE_TILES = 1;
'''

# Insert worker init right after the canvasRenderers lines
app = app.replace(
    "    window.canvasRenderers = canvasRenderers;\n    const currentRendererSetting",
    "    window.canvasRenderers = canvasRenderers;\n" + WORKER_INIT + "\n    const currentRendererSetting"
)

# ── Patch 4: Replace updateVectorTiles call to use OffscreenCanvas worker ─────
OLD_VEC = "                if (showVectors && currentRendererSetting === 'canvas') {\n                    const renderer = canvasRenderers.get(parseInt(pageNum));\n                    if (renderer) {\n                        renderer.updateVectorTiles(fetchScale, startCol, endCol, startRow, endRow, unscaledTileSize, maxW, maxH);\n                    }\n                }"

NEW_VEC = """                // Hybrid 2: always use canvas renderer for hit-testing index,
                // but dispatch tile painting to OffscreenCanvas worker
                if (showVectors) {
                    const renderer = canvasRenderers.get(parseInt(pageNum));
                    if (renderer) {
                        // Offscreen worker path
                        h2UpdateWorkerVectorTiles(wrapper, parseInt(pageNum), renderer,
                            fetchScale, startCol, endCol, startRow, endRow,
                            unscaledTileSize, maxW, maxH);
                    }
                }"""

app = app.replace(OLD_VEC, NEW_VEC)

# ── Patch 5: Expand tile range by PRE_TILES for predictive pre-rendering ──────
# The padding variable already exists; we just extend it
app = app.replace(
    "        const padding = unscaledTileSize * 0.5;",
    "        const padding = unscaledTileSize * (0.5 + H2_PRE_TILES); // Hybrid2 predictive"
)

# ── Patch 6: Add h2UpdateWorkerVectorTiles function before the closing brace ──
H2_FUNC = '''
    // ── Hybrid 2: OffscreenCanvas Worker Vector Tile Manager ─────────────────
    function h2UpdateWorkerVectorTiles(wrapper, pageNum, renderer, fetchScale,
                                       startCol, endCol, startRow, endRow,
                                       unscaledTileSize, maxW, maxH) {
        const activeTileKeys = new Set();
        const svgOverlay = wrapper.querySelector('.vector-overlay');
        const pageData = pagesData.get(pageNum);
        if (!pageData) return;

        for (let row = startRow; row <= endRow; row++) {
            for (let col = startCol; col <= endCol; col++) {
                const tileX = col * unscaledTileSize;
                const tileY = row * unscaledTileSize;
                const tileW = Math.min(unscaledTileSize, maxW - tileX);
                const tileH = Math.min(unscaledTileSize, maxH - tileY);
                if (tileW <= 0 || tileH <= 0) continue;

                const tileKey = `h2vec_${pageNum}_${fetchScale}_${col}_${row}`;
                activeTileKeys.add(tileKey);

                if (wrapper.querySelector(`.h2-vector-tile[data-tile-key="${tileKey}"]`)) continue;

                const nativeW = Math.round(tileW * fetchScale);
                const nativeH = Math.round(tileH * fetchScale);

                const canvas = document.createElement('canvas');
                canvas.className = 'h2-vector-tile';
                canvas.dataset.tileKey = tileKey;
                canvas.dataset.fetchScale = fetchScale;
                canvas.width = nativeW;
                canvas.height = nativeH;
                canvas.style.position = 'absolute';
                canvas.style.left = `${tileX}px`;
                canvas.style.top = `${tileY}px`;
                canvas.style.width = `${nativeW}px`;
                canvas.style.height = `${nativeH}px`;
                canvas.style.transformOrigin = '0 0';
                canvas.style.transform = `scale(${1 / fetchScale})`;
                canvas.style.pointerEvents = 'none';
                canvas.style.zIndex = '3';

                if (svgOverlay) wrapper.insertBefore(canvas, svgOverlay);
                else wrapper.appendChild(canvas);

                // Dispatch to worker (OffscreenCanvas) or fallback to main thread
                if (h2WorkerReady && typeof canvas.transferControlToOffscreen === 'function') {
                    const id = ++h2TileId;
                    h2Pending.set(id, {
                        resolve: () => {},
                        reject: (e) => console.warn('[Hybrid2]', e)
                    });
                    const offscreen = canvas.transferControlToOffscreen();
                    offscreen.width = nativeW;
                    offscreen.height = nativeH;
                    h2Worker.postMessage({
                        type: 'RENDER_VECTOR_TILE',
                        transferId: id,
                        offscreen,
                        drawings: pageData.drawings,
                        bounds: pageData.page_bounds,
                        pageNum,
                        tileX, tileY, tileW, tileH, fetchScale
                    }, [offscreen]);
                } else {
                    // Main-thread fallback using CanvasVectorRenderer
                    renderer.updateVectorTiles(fetchScale, col, col, row, row, unscaledTileSize, maxW, maxH);
                }
            }
        }

        // Prune stale worker vector tiles
        wrapper.querySelectorAll('.h2-vector-tile').forEach(t => {
            if (!activeTileKeys.has(t.dataset.tileKey)) t.remove();
        });
    }

    // Evict worker page index when navigating away
    function h2EvictPage(pageNum) {
        if (h2Worker) h2Worker.postMessage({ type: 'EVICT_PAGE', pageNum });
    }
'''

# Insert before the very last closing brace of initApp
# Find the last line "}" in the file that ends initApp
last_brace_pos = app.rfind('\n}')
if last_brace_pos != -1:
    app = app[:last_brace_pos] + H2_FUNC + app[last_brace_pos:]

# Write output
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(JS + app)

size = os.path.getsize(OUT)
print(f"Written {size} bytes to {OUT}")
'''

with open(r'c:\pinchus\gen_hybrid2.py', 'w', encoding='utf-8') as f:
    f.write(script_content)

print("Generator script written")
