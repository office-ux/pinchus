/**
 * canvas_vector_renderer.js
 * 
 * Interactive Canvas-Spatial Vector Engine (ICSVE) helper classes.
 * High-performance vector drawing and indexing for PDF Web Viewers.
 */

class SpatialHashGrid {
    constructor(width, height, cellSize = 80) {
        this.cellSize = cellSize;
        this.cols = Math.ceil(width / cellSize);
        this.rows = Math.ceil(height / cellSize);
        this.grid = new Array(this.cols * this.rows).fill(null).map(() => []);
    }

    _getCellIndices(bounds) {
        const startCol = Math.max(0, Math.floor(bounds.minX / this.cellSize));
        const endCol = Math.min(this.cols - 1, Math.floor(bounds.maxX / this.cellSize));
        const startRow = Math.max(0, Math.floor(bounds.minY / this.cellSize));
        const endRow = Math.min(this.rows - 1, Math.floor(bounds.maxY / this.cellSize));

        const cells = [];
        for (let r = startRow; r <= endRow; r++) {
            for (let c = startCol; c <= endCol; c++) {
                cells.push(r * this.cols + c);
            }
        }
        return cells;
    }

    insert(item, bounds) {
        const cells = this._getCellIndices(bounds);
        for (let i = 0; i < cells.length; i++) {
            this.grid[cells[i]].push({ item, bounds });
        }
    }

    queryPoint(x, y, radius = 5) {
        const bounds = {
            minX: x - radius,
            maxX: x + radius,
            minY: y - radius,
            maxY: y + radius
        };
        const candidates = this.queryRect(bounds);
        
        let bestItem = null;
        let minDistance = radius;
        let bestArea = Infinity;

        // Perfect geometric point-to-primitive distance check
        candidates.forEach(cand => {
            const dist = this._getDistanceToItem(x, y, cand);
            if (dist < minDistance) {
                minDistance = dist;
                bestItem = cand;
                bestArea = this._getItemArea(cand);
            } else if (dist === minDistance && dist === 0) {
                // If both are inside (distance 0), prefer the one with smaller area (more specific shape)
                const area = this._getItemArea(cand);
                if (area < bestArea) {
                    bestItem = cand;
                    bestArea = area;
                }
            }
        });

        return bestItem;
    }

    queryPointAll(x, y, radius = 5) {
        const bounds = {
            minX: x - radius,
            maxX: x + radius,
            minY: y - radius,
            maxY: y + radius
        };
        const candidates = this.queryRect(bounds);
        
        const results = [];
        candidates.forEach(cand => {
            const dist = this._getDistanceToItem(x, y, cand);
            if (dist <= radius) {
                results.push({ item: cand, distance: dist });
            }
        });

        results.sort((a, b) => a.distance - b.distance);
        return results.map(r => r.item);
    }

    queryRect(rect) {
        const startCol = Math.max(0, Math.floor(rect.minX / this.cellSize));
        const endCol = Math.min(this.cols - 1, Math.floor(rect.maxX / this.cellSize));
        const startRow = Math.max(0, Math.floor(rect.minY / this.cellSize));
        const endRow = Math.min(this.rows - 1, Math.floor(rect.maxY / this.cellSize));

        const results = new Set();
        for (let r = startRow; r <= endRow; r++) {
            for (let c = startCol; c <= endCol; c++) {
                const cellIdx = r * this.cols + c;
                if (cellIdx >= 0 && cellIdx < this.grid.length) {
                    const items = this.grid[cellIdx];
                    for (let i = 0; i < items.length; i++) {
                        results.add(items[i].item);
                    }
                }
            }
        }
        return Array.from(results);
    }

    _isPointInPolygon(px, py, points) {
        let inside = false;
        for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
            const xi = points[i][0], yi = points[i][1];
            const xj = points[j][0], yj = points[j][1];
            
            const intersect = ((yi > py) !== (yj > py))
                && (px < (xj - xi) * (py - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    }

    _getDistanceToItem(px, py, item) {
        if (item.type === 'Line') {
            return this._pointToSegmentDistance(px, py, item.start[0], item.start[1], item.end[0], item.end[1]);
        } else if (item.type === 'Rect') {
            // Check distance to four boundaries
            const d1 = this._pointToSegmentDistance(px, py, item.x, item.y, item.x + item.width, item.y);
            const d2 = this._pointToSegmentDistance(px, py, item.x + item.width, item.y, item.x + item.width, item.y + item.height);
            const d3 = this._pointToSegmentDistance(px, py, item.x + item.width, item.y + item.height, item.x, item.y + item.height);
            const d4 = this._pointToSegmentDistance(px, py, item.x, item.y + item.height, item.x, item.y);
            return Math.min(d1, d2, d3, d4);
        } else if (item.type === 'Polygon') {
            let minDist = Infinity;
            const pts = item.points;
            const len = pts.length;
            for (let i = 0; i < len; i++) {
                const d = this._pointToSegmentDistance(px, py, pts[i][0], pts[i][1], pts[(i + 1) % len][0], pts[(i + 1) % len][1]);
                if (d < minDist) minDist = d;
            }
            return minDist;
        } else if (item.type === 'Arc/Curve') {
            // Approximate bezier curve distance using control points or simple distance to polygon segments
            const pts = item.points;
            let minDist = Infinity;
            // Sample 8 segments along bezier
            let prevX = pts[0][0];
            let prevY = pts[0][1];
            for (let t = 0.125; t <= 1.0; t += 0.125) {
                const omt = 1 - t;
                const omt2 = omt * omt;
                const omt3 = omt2 * omt;
                const t2 = t * t;
                const t3 = t2 * t;
                
                const curX = omt3 * pts[0][0] + 3 * omt2 * t * pts[1][0] + 3 * omt * t2 * pts[2][0] + t3 * pts[3][0];
                const curY = omt3 * pts[0][1] + 3 * omt2 * t * pts[1][1] + 3 * omt * t2 * pts[2][1] + t3 * pts[3][1];
                
                const d = this._pointToSegmentDistance(px, py, prevX, prevY, curX, curY);
                if (d < minDist) minDist = d;
                prevX = curX;
                prevY = curY;
            }
            return minDist;
        }
        return Infinity;
    }

    _pointToSegmentDistance(px, py, x1, y1, x2, y2) {
        const dx = x2 - x1;
        const dy = y2 - y1;
        if (dx === 0 && dy === 0) {
            return Math.hypot(px - x1, py - y1);
        }
        let t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy);
        t = Math.max(0, Math.min(1, t));
        const nearestX = x1 + t * dx;
        const nearestY = y1 + t * dy;
        return Math.hypot(px - nearestX, py - nearestY);
    }

    _getItemArea(item) {
        if (item.type === 'Line') {
            return 0;
        } else if (item.type === 'Rect') {
            return Math.abs(item.width * item.height);
        } else if (item.type === 'Polygon') {
            const xs = item.points.map(p => p[0]);
            const ys = item.points.map(p => p[1]);
            const w = Math.max(...xs) - Math.min(...xs);
            const h = Math.max(...ys) - Math.min(...ys);
            return w * h;
        } else if (item.type === 'Arc/Curve') {
            const xs = item.points.map(p => p[0]);
            const ys = item.points.map(p => p[1]);
            const w = Math.max(...xs) - Math.min(...xs);
            const h = Math.max(...ys) - Math.min(...ys);
            return w * h;
        }
        return Infinity;
    }
}

class CanvasVectorRenderer {
    constructor(pageWrapper, bounds, drawings, pageNum) {
        this.wrapper = pageWrapper;
        this.bounds = bounds;
        this.drawings = drawings;
        this.pageNum = pageNum;
        
        // Use existing SVG overlay for dynamic highlights
        this.svgOverlay = this.wrapper.querySelector('.vector-overlay');
        
        this.spatialIndex = new SpatialHashGrid(bounds.width, bounds.height);
        
        console.time(`buildIndex_page_${pageNum}`);
        this.buildIndex();
        console.timeEnd(`buildIndex_page_${pageNum}`);
    }

    buildIndex() {
        this.drawings.forEach(item => {
            const bounds = this.getItemBounds(item);
            if (bounds) {
                this.spatialIndex.insert(item, bounds);
            }
        });
    }

    getItemBounds(item) {
        if (item.type === 'Line') {
            return {
                minX: Math.min(item.start[0], item.end[0]),
                maxX: Math.max(item.start[0], item.end[0]),
                minY: Math.min(item.start[1], item.end[1]),
                maxY: Math.max(item.start[1], item.end[1])
            };
        } else if (item.type === 'Rect') {
            return {
                minX: Math.min(item.x, item.x + item.width),
                maxX: Math.max(item.x, item.x + item.width),
                minY: Math.min(item.y, item.y + item.height),
                maxY: Math.max(item.y, item.y + item.height)
            };
        } else if (item.type === 'Polygon') {
            const xs = item.points.map(p => p[0]);
            const ys = item.points.map(p => p[1]);
            return {
                minX: Math.min(...xs),
                maxX: Math.max(...xs),
                minY: Math.min(...ys),
                maxY: Math.max(...ys)
            };
        } else if (item.type === 'Arc/Curve') {
            const xs = item.points.map(p => p[0]);
            const ys = item.points.map(p => p[1]);
            return {
                minX: Math.min(...xs),
                maxX: Math.max(...xs),
                minY: Math.min(...ys),
                maxY: Math.max(...ys)
            };
        }
        return null;
    }

    updateVectorTiles(fetchScale, startCol, endCol, startRow, endRow, unscaledTileSize, maxW, maxH) {
        const activeTileKeys = new Set();
        
        for (let row = startRow; row <= endRow; row++) {
            for (let col = startCol; col <= endCol; col++) {
                const tileX = col * unscaledTileSize;
                const tileY = row * unscaledTileSize;
                const tileW = Math.min(unscaledTileSize, maxW - tileX);
                const tileH = Math.min(unscaledTileSize, maxH - tileY);

                if (tileW <= 0 || tileH <= 0) continue;

                const tileKey = `vec_${this.pageNum}_${fetchScale}_${col}_${row}`;
                activeTileKeys.add(tileKey);

                if (this.wrapper.querySelector(`.vector-tile[data-tile-key="${tileKey}"]`)) {
                    continue;
                }

                const canvas = document.createElement('canvas');
                canvas.className = 'vector-tile';
                canvas.dataset.tileKey = tileKey;
                canvas.dataset.fetchScale = fetchScale;

                const nativeW = tileW * fetchScale;
                const nativeH = tileH * fetchScale;

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

                const ctx = canvas.getContext('2d');
                ctx.scale(fetchScale, fetchScale);
                ctx.translate(-tileX, -tileY);

                const tileRect = {
                    minX: tileX,
                    maxX: tileX + tileW,
                    minY: tileY,
                    maxY: tileY + tileH
                };

                const itemsToDraw = this.spatialIndex.queryRect(tileRect);

                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                itemsToDraw.forEach(item => {
                    ctx.lineWidth = Math.max(item.thickness, 0.5);
                    ctx.strokeStyle = item.color_hex || '#000000';
                    ctx.beginPath();
                    
                    if (item.type === 'Line') {
                        ctx.moveTo(item.start[0], item.start[1]);
                        ctx.lineTo(item.end[0], item.end[1]);
                    } else if (item.type === 'Rect') {
                        ctx.rect(item.x, item.y, item.width, item.height);
                    } else if (item.type === 'Polygon') {
                        const pts = item.points;
                        ctx.moveTo(pts[0][0], pts[0][1]);
                        ctx.lineTo(pts[1][0], pts[1][1]);
                        ctx.lineTo(pts[2][0], pts[2][1]);
                        ctx.lineTo(pts[3][0], pts[3][1]);
                        ctx.closePath();
                    } else if (item.type === 'Arc/Curve') {
                        const pts = item.points;
                        ctx.moveTo(pts[0][0], pts[0][1]);
                        ctx.bezierCurveTo(pts[1][0], pts[1][1], pts[2][0], pts[2][1], pts[3][0], pts[3][1]);
                    }
                    ctx.stroke();
                });

                if (this.svgOverlay) {
                    this.wrapper.insertBefore(canvas, this.svgOverlay);
                } else {
                    this.wrapper.appendChild(canvas);
                }
            }
        }

        // Prune off-screen tiles
        this.wrapper.querySelectorAll('.vector-tile').forEach(t => {
            if (!activeTileKeys.has(t.dataset.tileKey)) {
                t.remove();
            }
        });
    }

    clearHighlights() {
        if (!this.svgOverlay) return;
        this.svgOverlay.querySelectorAll('.dynamic-vector-highlight').forEach(el => el.remove());
    }

    drawHighlight(item, state = 'hover') {
        if (!this.svgOverlay) return;
        
        let el;
        if (item.type === 'Line') {
            el = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            el.setAttribute('x1', item.start[0]);
            el.setAttribute('y1', item.start[1]);
            el.setAttribute('x2', item.end[0]);
            el.setAttribute('y2', item.end[1]);
        } else if (item.type === 'Rect') {
            el = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            el.setAttribute('x', item.x);
            el.setAttribute('y', item.y);
            el.setAttribute('width', item.width);
            el.setAttribute('height', item.height);
        } else if (item.type === 'Polygon') {
            el = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
            const ptsStr = item.points.map(p => `${p[0]},${p[1]}`).join(' ');
            el.setAttribute('points', ptsStr);
        } else if (item.type === 'Arc/Curve') {
            el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            const pts = item.points;
            el.setAttribute('d', `M ${pts[0][0]} ${pts[0][1]} C ${pts[1][0]} ${pts[1][1]}, ${pts[2][0]} ${pts[2][1]}, ${pts[3][0]} ${pts[3][1]}`);
        }
        
        if (!el) return;

        el.classList.add('dynamic-vector-highlight');
        
        el.style.strokeWidth = Math.max(item.thickness || 0, 0.5) + 'px';
        el.style.stroke = state === 'selected' ? '#ff00ff' : '#00ffff';
        el.style.strokeLinecap = 'round';
        el.style.strokeLinejoin = 'round';
        el.style.fill = 'none';
        el.style.pointerEvents = 'none';
        
        this.svgOverlay.appendChild(el);
    }

    queryPoint(x, y, radius = 5) {
        return this.spatialIndex.queryPoint(x, y, radius);
    }

    queryPointAll(x, y, radius = 5) {
        return this.spatialIndex.queryPointAll(x, y, radius);
    }

    queryRect(rect) {
        return this.spatialIndex.queryRect(rect);
    }

    destroy() {
        this.wrapper.querySelectorAll('.vector-tile').forEach(t => t.remove());
        this.clearHighlights();
    }
}

window.SpatialHashGrid = SpatialHashGrid;
window.CanvasVectorRenderer = CanvasVectorRenderer;
