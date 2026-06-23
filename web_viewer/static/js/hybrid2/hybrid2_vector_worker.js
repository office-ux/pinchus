'use strict';

// -- Spatial Hash Grid (pure JS, flat array offsets) ---------------------------
class SpatialHashGrid {
    constructor(width, height, cellSize = 80) {
        this.cellSize = cellSize;
        this.cols = Math.ceil(width / cellSize);
        this.rows = Math.ceil(height / cellSize);
        this.grid = new Array(this.cols * this.rows).fill(null).map(() => []);
    }

    _getCellIndices(bounds) {
        const startCol = Math.max(0, Math.floor(bounds.minX / this.cellSize));
        const endCol   = Math.min(this.cols - 1, Math.floor(bounds.maxX / this.cellSize));
        const startRow = Math.max(0, Math.floor(bounds.minY / this.cellSize));
        const endRow   = Math.min(this.rows - 1, Math.floor(bounds.maxY / this.cellSize));
        const cells = [];
        for (let r = startRow; r <= endRow; r++)
            for (let c = startCol; c <= endCol; c++)
                cells.push(r * this.cols + c);
        return cells;
    }

    insert(offset, bounds) {
        const cells = this._getCellIndices(bounds);
        for (let i = 0; i < cells.length; i++)
            this.grid[cells[i]].push(offset);
    }

    queryRect(rect) {
        const startCol = Math.max(0, Math.floor(rect.minX / this.cellSize));
        const endCol   = Math.min(this.cols - 1, Math.floor(rect.maxX / this.cellSize));
        const startRow = Math.max(0, Math.floor(rect.minY / this.cellSize));
        const endRow   = Math.min(this.rows - 1, Math.floor(rect.maxY / this.cellSize));
        const results  = new Set();
        for (let r = startRow; r <= endRow; r++) {
            for (let c = startCol; c <= endCol; c++) {
                const cellIdx = r * this.cols + c;
                if (cellIdx >= 0 && cellIdx < this.grid.length) {
                    const items = this.grid[cellIdx];
                    for (let i = 0; i < items.length; i++)
                        results.add(items[i]);
                }
            }
        }
        return Array.from(results);
    }
}

// -- Per-page spatial indexes (keyed by pageNum) ------------------------------
const pageIndexes = new Map();

function buildIndexFromBuffer(pageNum, bounds, buffer) {
    if (pageIndexes.has(pageNum)) return pageIndexes.get(pageNum);
    const idx = new SpatialHashGrid(bounds.width, bounds.height);
    
    let offset = 0;
    while (offset < buffer.length) {
        const typeId = buffer[offset];
        if (typeId === 0) break; // End of valid data
        const currentOffset = offset;
        offset += 3; // skip type, color, thickness
        
        let b = null;
        if (typeId === 1) { // Line
            const x1 = buffer[offset++]; const y1 = buffer[offset++];
            const x2 = buffer[offset++]; const y2 = buffer[offset++];
            offset++; // align 8
            b = { minX: Math.min(x1, x2), maxX: Math.max(x1, x2), minY: Math.min(y1, y2), maxY: Math.max(y1, y2) };
        } else if (typeId === 2) { // Rect
            const x = buffer[offset++]; const y = buffer[offset++];
            const w = buffer[offset++]; const h = buffer[offset++];
            b = { minX: Math.min(x, x+w), maxX: Math.max(x, x+w), minY: Math.min(y, y+h), maxY: Math.max(y, y+h) };
        } else if (typeId === 3 || typeId === 4) { // Polygon / Arc
            const numPts = buffer[offset++];
            let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
            for(let i=0; i<numPts; i++) {
                const px = buffer[offset++];
                const py = buffer[offset++];
                if (px < minX) minX = px; if (px > maxX) maxX = px;
                if (py < minY) minY = py; if (py > maxY) maxY = py;
            }
            b = { minX, maxX, minY, maxY };
        } else {
            break; // invalid type
        }
        
        if (b) idx.insert(currentOffset, b);
    }
    const pageData = { idx, buffer };
    pageIndexes.set(pageNum, pageData);
    return pageData;
}

// -- Main message handler -----------------------------------------------------
self.onmessage = function (e) {
    const msg = e.data;

    if (msg.type === 'INIT_PAGE') {
        const { pageNum, buffer, bounds } = msg;
        try {
            buildIndexFromBuffer(pageNum, bounds, buffer);
        } catch (err) {
            console.warn('[Hybrid2 Worker] Failed to init page:', err);
        }
        return;
    }

    if (msg.type === 'RENDER_VECTOR_TILE') {
        const { transferId, offscreen, pageNum,
                tileX, tileY, tileW, tileH, fetchScale } = msg;
        try {
            const pageData = pageIndexes.get(pageNum);
            const ctx = offscreen.getContext('2d');

            if (!pageData) {
                // If index isn't ready, just clear and return
                ctx.clearRect(0, 0, offscreen.width, offscreen.height);
                self.postMessage({ type: 'TILE_DONE', transferId });
                return;
            }

            const { idx, buffer } = pageData;

            ctx.clearRect(0, 0, offscreen.width, offscreen.height);
            ctx.save();
            ctx.scale(fetchScale, fetchScale);
            ctx.translate(-tileX, -tileY);
            ctx.lineCap  = 'round';
            ctx.lineJoin = 'round';

            const tileRect = {
                minX: tileX, maxX: tileX + tileW,
                minY: tileY, maxY: tileY + tileH
            };
            const offsets = idx.queryRect(tileRect);

            for (let i = 0; i < offsets.length; i++) {
                let offset = offsets[i];
                const typeId = buffer[offset++];
                const colorInt = buffer[offset++];
                const thickness = buffer[offset++];

                let hex = colorInt.toString(16);
                while(hex.length < 6) hex = '0' + hex;

                ctx.lineWidth   = Math.max(thickness || 0.5, 0.5);
                ctx.strokeStyle = '#' + hex;
                ctx.beginPath();

                if (typeId === 1) { // Line
                    ctx.moveTo(buffer[offset++], buffer[offset++]);
                    ctx.lineTo(buffer[offset++], buffer[offset++]);
                    offset++; // align 8
                } else if (typeId === 2) { // Rect
                    ctx.rect(buffer[offset++], buffer[offset++], buffer[offset++], buffer[offset++]);
                } else if (typeId === 3) { // Polygon
                    const numPts = buffer[offset++];
                    if (numPts > 0) {
                        ctx.moveTo(buffer[offset++], buffer[offset++]);
                        for(let j=1; j<numPts; j++) ctx.lineTo(buffer[offset++], buffer[offset++]);
                        ctx.closePath();
                    }
                } else if (typeId === 4) { // Arc/Curve
                    const numPts = buffer[offset++];
                    if (numPts >= 4) {
                        ctx.moveTo(buffer[offset++], buffer[offset++]);
                        ctx.bezierCurveTo(buffer[offset++], buffer[offset++], buffer[offset++], buffer[offset++], buffer[offset++], buffer[offset++]);
                    }
                }
                ctx.stroke();
            }

            ctx.restore();
            self.postMessage({ type: 'TILE_DONE', transferId });
        } catch (err) {
            self.postMessage({ type: 'TILE_ERROR', transferId, error: err.toString() });
        }
        return;
    }

    if (msg.type === 'EVICT_PAGE') {
        pageIndexes.delete(msg.pageNum);
        return;
    }

    if (msg.type === 'CLEAR_INDEXES') {
        pageIndexes.clear();
        return;
    }
};
