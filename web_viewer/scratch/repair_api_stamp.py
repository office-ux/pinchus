import sys

with open(r'c:\pinchus\web_viewer\static\js\api_stamp.js', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('const addTd = (text, title, colName) => {')
if idx == -1:
    print('Not found')
    sys.exit(1)

correct_end = """const addTd = (text, title, colName) => {
                const td = document.createElement("td");
                td.textContent = text;
                if (title) td.title = title;
                
                if (savedWidths[colName]) {
                    td.style.maxWidth = savedWidths[colName];
                    td.style.overflow = "hidden";
                    td.style.textOverflow = "ellipsis";
                }
                tr.appendChild(td);
            };
            
            sortedFields.forEach(field => {
                if (field === "UUID") addTd(item.id, null, field);
                else if (field === "Pattern") addTd(item.pattern_name ? "Pattern: " + item.pattern_name : "", null, field);
                else if (field === "PDF File") addTd(item.pdf_path ? item.pdf_path.split('/').pop().replace(/\\\\/g, '/').split('/').pop() : 'Unknown', item.pdf_path, field);
                else if (field === "Page") addTd(item.page, null, field);
                else addTd(item.fields ? (item.fields[field] || "") : "", null, field);
            });
            
            const tdAction = document.createElement("td");
            const btnDelete = document.createElement("button");
            btnDelete.textContent = "Delete";
            btnDelete.className = "btn secondary-btn";
            btnDelete.style.padding = "4px 8px";
            btnDelete.style.color = "#ff4d4d";
            btnDelete.onclick = async (e) => {
                e.stopPropagation();
                if (!confirm("Are you sure you want to delete this stamp?")) return;
                try {
                    const res = await fetch(`/api/pdf/${encodeURIComponent(item.pdf_path)}/stamps/${item.xref}`, { method: "DELETE" });
                    const data = await res.json();
                    if (!res.ok) {
                        if (confirm(`Failed to delete stamp from PDF (${data.error}). Force-delete database record?`)) {
                            const forceRes = await fetch(`/api/pdf/${encodeURIComponent(item.pdf_path)}/stamps/${item.xref}?force=true`, { method: "DELETE" });
                            if (forceRes.ok) {
                                tr.remove();
                                selectedRows.delete(item.id);
                                allProjectAirOutlets = allProjectAirOutlets.filter(x => x.id !== item.id);
                                allProjectSystems = allProjectSystems.filter(x => x.id !== item.id);
                                window.dispatchEvent(new CustomEvent('stamp-deleted', { detail: { xref: item.xref } }));
                            }
                        }
                    } else {
                        tr.remove();
                        selectedRows.delete(item.id);
                        allProjectAirOutlets = allProjectAirOutlets.filter(x => x.id !== item.id);
                        allProjectSystems = allProjectSystems.filter(x => x.id !== item.id);
                        window.dispatchEvent(new CustomEvent('stamp-deleted', { detail: { xref: item.xref } }));
                    }
                } catch (err) { alert("Error deleting stamp: " + err.message); }
            };
            tdAction.appendChild(btnDelete);
            tr.appendChild(tdAction);
            
            tbody.appendChild(tr);
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initStampAPI);
} else {
    initStampAPI();
}

document.addEventListener('DOMContentLoaded', () => {
    const btnAddStampManually = document.getElementById('btn-add-stamp-manually');
    const addStampModal = document.getElementById('add-stamp-manually-modal');
    const btnCloseAddStampModal = document.getElementById('btn-close-add-stamp-manually-modal');
    const btnCancelAddStamp = document.getElementById('btn-cancel-add-stamp-manually');
    const btnConfirmAddStamp = document.getElementById('btn-confirm-add-stamp-manually');
    const selectStampShape = document.getElementById('select-stamp-shape');

    if (btnAddStampManually) {
        btnAddStampManually.addEventListener('click', () => {
            if (!window.currentPdfStamps || window.currentPdfStamps.length === 0) {
                alert("No stamps available to copy on this page.");
                return;
            }
            
            const shapes = {};
            window.currentPdfStamps.forEach(s => {
                const name = s.pattern_name || s.name || s.title || "";
                if (!name || name === "Unknown") return;
                const match = name.match(/^(.*?)[ _]?\\d+$/);
                const baseName = match ? match[1].trim() : name.trim();
                if (baseName) {
                    if (!shapes[baseName]) shapes[baseName] = [];
                    shapes[baseName].push(s);
                }
            });
            
            selectStampShape.innerHTML = '<option value="">-- Select a Shape --</option>';
            for (const baseName in shapes) {
                const opt = document.createElement('option');
                opt.value = baseName;
                opt.textContent = baseName + ` (${shapes[baseName].length} available)`;
                selectStampShape.appendChild(opt);
            }
            
            addStampModal.style.display = 'flex';
        });
    }
    
    if (btnCloseAddStampModal) btnCloseAddStampModal.addEventListener('click', () => addStampModal.style.display = 'none');
    if (btnCancelAddStamp) btnCancelAddStamp.addEventListener('click', () => addStampModal.style.display = 'none');
    
    if (btnConfirmAddStamp) {
        btnConfirmAddStamp.addEventListener('click', async () => {
            const baseName = selectStampShape.value;
            if (!baseName) {
                alert("Please select a shape.");
                return;
            }
            
            const stamps = window.currentPdfStamps.filter(s => {
                const name = s.pattern_name || s.name || s.title || "";
                const match = name.match(/^(.*?)[ _]?\\d+$/);
                const bn = match ? match[1].trim() : name.trim();
                return bn === baseName;
            });
            
            if (stamps.length === 0) return;
            
            let maxNum = 0;
            stamps.forEach(s => {
                const name = s.pattern_name || s.name || s.title || "";
                const match = name.match(/\\d+$/);
                if (match) {
                    const num = parseInt(match[0], 10);
                    if (num > maxNum) maxNum = num;
                }
            });
            const nextNum = maxNum + 1;
            const newName = `${baseName}_${nextNum}`;
            const srcStamp = stamps[0];
            const newUuid = crypto.randomUUID ? crypto.randomUUID() : 'uuid-' + Date.now();
            
            addStampModal.style.display = 'none';
            startStampPlacementMode(srcStamp, newName, newUuid);
        });
    }

    function getClosestPointOnSegment(px, py, x1, y1, x2, y2) {
        const dx = x2 - x1;
        const dy = y2 - y1;
        if (dx === 0 && dy === 0) return { x: x1, y: y1 };
        let t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy);
        t = Math.max(0, Math.min(1, t));
        return { x: x1 + t * dx, y: y1 + t * dy };
    }

    function startStampPlacementMode(srcStamp, newName, newUuid) {
        const viewerContainer = document.getElementById('viewer-container');
        if (!viewerContainer) return;

        // Visual ghost marker
        const ghost = document.createElement('div');
        ghost.className = 'stamp-ghost';
        let width = 40, height = 40;
        if (srcStamp.rect && srcStamp.rect.length === 4) {
            // Rough size based on PDF points, will be scaled visually
            width = srcStamp.rect[2] - srcStamp.rect[0];
            height = srcStamp.rect[3] - srcStamp.rect[1];
        }
        
        // Ensure minimum size
        width = Math.max(width, 20);
        height = Math.max(height, 20);

        ghost.style.position = 'fixed';
        ghost.style.width = width + 'px';
        ghost.style.height = height + 'px';
        ghost.style.border = '2px dashed #ff0000';
        ghost.style.backgroundColor = 'rgba(255, 0, 0, 0.2)';
        ghost.style.borderRadius = '50%';
        ghost.style.pointerEvents = 'none';
        ghost.style.zIndex = '99999';
        ghost.style.transform = 'translate(-50%, -50%)';
        ghost.style.display = 'none';
        document.body.appendChild(ghost);

        let currentPdfX = null;
        let currentPdfY = null;
        let currentPageNum = null;
        let isActive = true;

        const onMouseMove = (e) => {
            if (!isActive) return;
            
            ghost.style.display = 'block';

            // Find underlying page wrapper
            const hitTarget = document.elementFromPoint(e.clientX, e.clientY);
            const wrapper = hitTarget ? hitTarget.closest('.page-wrapper') : null;
            
            let snappedX = e.clientX;
            let snappedY = e.clientY;

            if (wrapper) {
                currentPageNum = parseInt(wrapper.dataset.page);
                const rect = wrapper.getBoundingClientRect();
                const scale = rect.width / wrapper.offsetWidth;
                
                let pdfX = (e.clientX - rect.left) / scale;
                let pdfY = (e.clientY - rect.top) / scale;

                // Attempt to snap to vector line
                if (window.canvasRenderers) {
                    const renderer = window.canvasRenderers.get(currentPageNum);
                    if (renderer) {
                        const snapItem = renderer.queryPoint(pdfX, pdfY, 20); // 20pt snap radius
                        if (snapItem && snapItem.type === 'Line') {
                            const nearest = getClosestPointOnSegment(pdfX, pdfY, snapItem.start[0], snapItem.start[1], snapItem.end[0], snapItem.end[1]);
                            pdfX = nearest.x;
                            pdfY = nearest.y;
                            
                            // Convert back to screen coords for ghost
                            snappedX = rect.left + pdfX * scale;
                            snappedY = rect.top + pdfY * scale;
                        }
                    }
                }

                currentPdfX = pdfX;
                currentPdfY = pdfY;
            }

            ghost.style.left = snappedX + 'px';
            ghost.style.top = snappedY + 'px';
        };

        const onClick = async (e) => {
            if (!isActive) return;
            e.preventDefault();
            e.stopPropagation();

            if (currentPdfX === null || currentPdfY === null || currentPageNum === null) {
                cleanup();
                return;
            }

            // Disable further interactions
            isActive = false;
            ghost.style.backgroundColor = 'rgba(0, 255, 0, 0.4)';
            ghost.style.border = '2px solid #00ff00';

            try {
                const res = await fetch(`/api/pdf/${encodeURIComponent(window.currentPdf)}/stamps/copy`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source_xref: srcStamp.xref,
                        new_name: newName,
                        new_uuid: newUuid,
                        page_num: currentPageNum,
                        center_x: currentPdfX,
                        center_y: currentPdfY
                    })
                });
                
                const data = await res.json();
                if (!data.success) throw new Error(data.error || "Failed to copy stamp");
                
                window.location.reload(); 
            } catch (err) {
                alert("Error placing stamp: " + err.message);
                cleanup();
            }
        };

        const onKeyDown = (e) => {
            if (e.key === 'Escape' && isActive) {
                cleanup();
            }
        };

        const cleanup = () => {
            isActive = false;
            if (ghost.parentNode) ghost.parentNode.removeChild(ghost);
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('click', onClick, true);
            window.removeEventListener('keydown', onKeyDown);
        };

        // Delay the click attachment slightly so the current click doesn't trigger it immediately
        setTimeout(() => {
            window.addEventListener('click', onClick, true);
        }, 100);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('keydown', onKeyDown);
    }
});
"""

with open(r'c:\pinchus\web_viewer\static\js\api_stamp.js', 'w', encoding='utf-8') as f:
    f.write(text[:idx] + correct_end)

print('Successfully repaired api_stamp.js')
