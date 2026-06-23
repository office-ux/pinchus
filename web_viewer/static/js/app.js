function initApp() {
    // UI Elements
    const fileList = document.getElementById('file-list');
    const btnRefresh = document.getElementById('btn-refresh-files');
    const viewerContainer = document.getElementById('viewer-container');
    const panZoomContainer = document.getElementById('pan-zoom-container');
    const selectionLasso = document.getElementById('selection-lasso');
    
    // Toolbar Elements
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');
    const pageCurrent = document.getElementById('page-current');
    const pageTotal = document.getElementById('page-total');
    const btnLayoutToggle = document.getElementById('btn-layout-toggle');
    const btnZoomOut = document.getElementById('btn-zoom-out');
    const btnZoomIn = document.getElementById('btn-zoom-in');
    const btnZoomReset = document.getElementById('btn-zoom-reset');
    const btnUndoPdf = document.getElementById('btn-undo-pdf');
    const zoomLevelDisplay = document.getElementById('zoom-level');
    
    // Inspector Elements
    const selectionCount = document.getElementById('selection-count');
    const selectionSpinner = document.getElementById('selection-spinner');
    const inspectorBody = document.getElementById('inspector-body');
    const rawOutput = document.getElementById('raw-output');
    const btnCopyInfo = document.getElementById('btn-copy-info');
    const btnClearSelection = document.getElementById('btn-clear-selection');
    
    // Coordinates Elements
    const btnToggleCoords = document.getElementById('btn-toggle-coords');
    const btnToggleThinLines = document.getElementById('btn-toggle-thin-lines');
    const coordsOverlay = document.getElementById('coords-overlay');
    const coordsVal = document.getElementById('coords-val');
    const coordsPage = document.getElementById('coords-page');
    const coordsTooltip = document.getElementById('coords-tooltip');
    
    const btnToggleSvgLayer = document.getElementById('btn-toggle-svg-layer');
 
    // Sidebar Drawer Elements (Tablets/Mobile)
    const btnToggleSidebarLeft = document.getElementById('btn-toggle-sidebar-left');
    const btnToggleSidebarRight = document.getElementById('btn-toggle-sidebar-right');
    const sidebarLeft = document.querySelector('.sidebar-left');
    const sidebarRight = document.querySelector('.sidebar-right');
    const sidebarBackdrop = document.getElementById('sidebar-backdrop');
 
    // State
    let currentPdf = null;
    let totalPages = 0;
    let currentPage = 1;
    let layoutMode = 'continuous'; // Default to continuous mode for better experience
    let pagesData = new Map(); // pageNum -> { bounds, drawings }
    let canvasRenderers = new Map();
    window.canvasRenderers = canvasRenderers;
    const currentRendererSetting = localStorage.getItem('pdf_renderer') || 'legacy';
    const imageCache = new Map(); // cacheKey -> image data url / cached url
    let renderId = 0;
    
    // View State
    let scale = 1.0;
    let translateX = 0;
    let translateY = 0;
    let isPanning = false;
    let startPanX = 0;
    let startPanY = 0;
    
    // Feature Toggles
    let showVectors = true;
    
    // Selection State
    let selectionMode = false;
    let selectedItems = new Map(); // id -> item data
    let isLassoing = false;
    let lassoStartX = 0;
    let lassoStartY = 0;
    let isSpacePressed = false;
    let highlightedItemId = null; // Currently highlighted item ID from inspector row click
    let lassoHighlightedItems = [];
    let currentProject = null; // Currently active project name

    // Coordinates State
    let showCoordsMode = false;
    let coordsUnit = 'pt'; // pt, in, mm
    let lastMouseEvent = null;

    // Touch Gestures State
    let touchStartDist = 0;
    let touchStartScale = 1;
    let touchStartTranslateX = 0;
    let touchStartTranslateY = 0;
    let touchStartMidX = 0;
    let touchStartMidY = 0;
    let lastTouchTime = 0;
    let lastTouchX = 0;
    let lastTouchY = 0;
    let isTouchZooming = false;
    let isDoubleTapLasso = false;

    // Touch Inertia State
    let touchVelocityX = 0;
    let touchVelocityY = 0;
    let touchLastMoveTime = 0;
    let touchLastMoveX = 0;
    let touchLastMoveY = 0;
    let touchInertiaFrameId = null;

    function updatePageDisplay(pageNum) {
        if (!pageCurrent) return;
        if (pageCurrent.tagName === 'INPUT') {
            pageCurrent.value = pageNum;
        } else {
            pageCurrent.textContent = pageNum;
        }
    }

    // ── Loading Overlay Helpers ───────────────────────────────────────────────
    function showLoadingOverlay(filename, status) {
        const overlay = document.getElementById('pdf-loading-overlay');
        const fnEl = document.getElementById('pdf-loading-filename');
        const stEl = document.getElementById('pdf-loading-status');
        const fill = document.getElementById('pdf-progress-fill');
        if (!overlay) return;
        if (fnEl) fnEl.textContent = filename || 'Loading PDF…';
        if (stEl) stEl.textContent = status || 'Please wait…';
        if (fill) fill.style.width = '0%';
        overlay.classList.remove('hidden', 'fade-out');
    }

    function setLoadingProgress(pct, status) {
        const fill = document.getElementById('pdf-progress-fill');
        const stEl = document.getElementById('pdf-loading-status');
        if (fill) fill.style.width = `${Math.min(100, pct)}%`;
        if (stEl && status) stEl.textContent = status;
    }

    function hideLoadingOverlay() {
        const overlay = document.getElementById('pdf-loading-overlay');
        if (!overlay) return;
        setLoadingProgress(100);
        setTimeout(() => {
            overlay.classList.add('fade-out');
            setTimeout(() => overlay.classList.add('hidden'), 420);
        }, 120);
    }

    // Project / Upload Elements
    const btnUploadTrigger = document.getElementById('btn-upload-trigger');
    const fileUploadInput = document.getElementById('file-upload-input');
    const currentProjectBar = document.getElementById('current-project-bar');
    const currentProjectLabel = document.getElementById('current-project-label');

    // Add Item Buttons & Modals
    const btnAddGrill = document.getElementById('btn-add-grill');
    const btnAddAac = document.getElementById('btn-add-aac');
    const btnSaveSelection = document.getElementById('btn-save-selection');
    const addItemModal = document.getElementById('add-item-modal');
    const addItemModalTitle = document.getElementById('add-item-title');
    const btnCloseItemModal = document.getElementById('btn-close-item-modal');
    const btnCancelItem = document.getElementById('btn-cancel-item');
    const btnSubmitItem = document.getElementById('btn-submit-item');
    const itemTypeSelect = document.getElementById('item-type-select');
    const newItemInputName = document.getElementById('new-item-input-name');
    const itemModalErrorMessage = document.getElementById('item-modal-error-message');
    const btnAddPatternPlus = document.getElementById('btn-add-pattern-plus');
    const btnAddGrillPlus = document.getElementById('btn-add-grill-plus');
    const btnAddAacPlus = document.getElementById('btn-add-aac-plus');
    let patternFilter = null;
    
    // Pattern Scanner Elements
    const btnRunMatching = document.getElementById('btn-run-matching');
    const btnRunPatterns = document.getElementById('btn-run-patterns');
    const btnRunStamps = document.getElementById('btn-run-stamps');
    const scannerSpinner = document.getElementById('scanner-spinner');
    const scannerStatus = document.getElementById('scanner-status');
    const scannerLogPanel = document.getElementById('scanner-log-panel');
    const scannerLogPreview = document.getElementById('scanner-log-preview');
    const scannerLogFull = document.getElementById('scanner-log-full');
    const btnScannerLogMore = document.getElementById('btn-scanner-log-more');

    // Stamps Tab Elements
    const panelStamps = document.getElementById('panel-stamps');
    const tabStamps = document.getElementById('tab-stamps');
    const stampTabBadge = document.getElementById('stamp-tab-badge');
    const stampsCountLabel = document.getElementById('stamps-count-label');
    const stampsList = document.getElementById('stamps-list');
    
    // Patterns Tab Elements
    const panelPatterns = document.getElementById('panel-patterns');
    const tabPatterns = document.getElementById('tab-patterns');
    const patternsCountLabel = document.getElementById('patterns-count-label');
    const patternsList = document.getElementById('patterns-list');

    // Add Item State
    let activeAddState = null;
    let projectAnnotations = [];
    let currentAddType = null;
    let isSavingDirectly = false;
    let currentPdfStamps = [];
    let selectedStamps = new Set();
    let lastSelectedStampIndex = -1;
    let pdfCacheBuster = Date.now();

    let currentPdfPatterns = [];
    let selectedPatterns = new Set();
    let lastSelectedPatternIndex = -1;
    let scannerLogLines = [];
    let scannerLogExpanded = false;
    let canUndoPatternScan = false;

    // --- Sidebar Tab Switching ---
    function switchSidebarTab(tab) {
        // Reset all tabs
        tabStamps.classList.remove('active');
        tabPatterns.classList.remove('active');
        panelStamps.classList.remove('active');
        panelPatterns.classList.remove('active');
        
        if (tab === 'stamps') {
            tabStamps.classList.add('active');
            panelStamps.classList.add('active');
            tabPatterns.style.display = 'none';
        } else if (tab === 'patterns') {
            tabPatterns.classList.add('active');
            panelPatterns.classList.add('active');
            tabPatterns.style.display = 'inline-flex';
        }
        updateStampsModeVisibility();
    }
    tabStamps.addEventListener('click', () => switchSidebarTab('stamps'));
    tabPatterns.addEventListener('click', () => switchSidebarTab('patterns'));

    function resetScannerLog() {
        scannerLogLines = [];
        scannerLogExpanded = false;
        if (scannerLogPanel) scannerLogPanel.style.display = 'none';
        if (scannerLogFull) {
            scannerLogFull.textContent = '';
        }
        if (btnScannerLogMore) {
            btnScannerLogMore.style.display = 'none';
            btnScannerLogMore.textContent = 'More...';
        }
    }

    function renderScannerLog() {
        if (!scannerLogPanel || !scannerLogFull || !btnScannerLogMore) return;
        if (scannerLogLines.length === 0) {
            scannerLogPanel.style.display = 'none';
            scannerLogFull.textContent = '';
            btnScannerLogMore.style.display = 'none';
            return;
        }

        scannerLogFull.textContent = scannerLogLines.join('\n');
        btnScannerLogMore.style.display = 'block';

        if (scannerLogExpanded) {
            scannerLogPanel.style.display = 'flex';
            btnScannerLogMore.textContent = 'Hide output';
            scannerLogFull.scrollTop = scannerLogFull.scrollHeight;
        } else {
            scannerLogPanel.style.display = 'none';
            btnScannerLogMore.textContent = 'More...';
        }
    }

    window.appendScannerLog = function(message) {
        if (!message) return;
        scannerLogLines.push(message);
        if (scannerLogLines.length > 400) {
            scannerLogLines = scannerLogLines.slice(-400);
        }
        renderScannerLog();
    };
    const appendScannerLog = window.appendScannerLog;

    if (btnScannerLogMore) {
        btnScannerLogMore.addEventListener('click', () => {
            scannerLogExpanded = !scannerLogExpanded;
            renderScannerLog();
        });
    }

    const btnCloseScannerLog = document.getElementById('btn-close-scanner-log');
    if (btnCloseScannerLog) {
        btnCloseScannerLog.addEventListener('click', () => {
            scannerLogExpanded = false;
            renderScannerLog();
        });
    }

    if (scannerLogPanel) {
        const header = scannerLogPanel.querySelector('.scanner-log-header');
        if (header) {
            let isDragging = false;
            let currentX;
            let currentY;
            let initialX;
            let initialY;

            header.addEventListener('mousedown', dragStart);
            document.addEventListener('mouseup', dragEnd);
            document.addEventListener('mousemove', drag);

            function dragStart(e) {
                const rect = scannerLogPanel.getBoundingClientRect();
                initialX = e.clientX - rect.left;
                initialY = e.clientY - rect.top;

                if (e.target === header || header.contains(e.target) && e.target !== btnCloseScannerLog) {
                    isDragging = true;
                }
            }

            function dragEnd(e) {
                isDragging = false;
            }

            function drag(e) {
                if (isDragging) {
                    e.preventDefault();
                    currentX = e.clientX - initialX;
                    currentY = e.clientY - initialY;
                    scannerLogPanel.style.left = currentX + 'px';
                    scannerLogPanel.style.top = currentY + 'px';
                    scannerLogPanel.style.bottom = 'auto'; 
                }
            }
        }
    }

    function normalizePatternType(type) {
        const normalized = (type || '').trim().toLowerCase();
        if (normalized === 'grill' || normalized === 'air outlet' || normalized === 'air_outlet' || normalized === 'vent') return 'grill';
        if (['aac', 'aac_unit', 'hvac', 'hvac_unit', 'system', 'box'].includes(normalized)) return 'aac_unit';
        return normalized || 'pattern';
    }

    function updateUndoButtonState() {
        if (!btnUndoPdf) return;
        btnUndoPdf.disabled = !currentPdf || !canUndoPatternScan;
    }

    function getPatternFilterType(type) {
        return normalizePatternType(type) === 'aac_unit' ? 'aac' : normalizePatternType(type);
    }

    function getPatternTypeLabel(type) {
        return normalizePatternType(type) === 'grill' ? 'Air Outlet' : 'System';
    }

    function isGeneratedOutputPath(path) {
        return typeof path === 'string' && path.startsWith('Output/');
    }

    function removeGeneratedFileEntries() {
        Array.from(fileList.querySelectorAll('li')).forEach(li => {
            if (isGeneratedOutputPath(li.title || '')) {
                li.remove();
            }
        });
    }

    function normalizePath(p) {
        if (!p) return '';
        return p.toLowerCase().replace(/\\/g, '/').replace(/^.*\/projects\//, 'projects/');
    }

    // --- Project Initialisation (from URL ?project= param) ---
    function initProject() {
        const params = new URLSearchParams(window.location.search);
        let projectName = params.get('project') || '';
        const pdfPath = params.get('pdf') || '';

        // Fallback: extract project name from pdf path if it starts with/contains Projects/XYZ
        if (!projectName && pdfPath) {
            const match = pdfPath.match(/projects[\\\/]([^\\\/]+)/i);
            if (match) {
                projectName = match[1];
            }
        }

        if (projectName) {
            currentProject = projectName;
            window.currentProject = projectName;
            if (currentProjectLabel) currentProjectLabel.textContent = projectName;
            if (currentProjectBar) currentProjectBar.style.display = 'flex';
            const logoEl = document.getElementById('logo-project-name');
            if (logoEl) logoEl.textContent = projectName;
            btnRefresh.disabled = false;
            btnUploadTrigger.disabled = false;
            
            // Load templates
            if (window.loadTemplates) {
                window.loadTemplates();
            } else {
                setTimeout(() => { if (window.loadTemplates) window.loadTemplates(); }, 500);
            }

            fetchAnnotations();
            fetchPdfs().then(() => {
                if (pdfPath) {
                    const listItems = Array.from(document.querySelectorAll('.file-list li'));
                    const normalizedTarget = normalizePath(pdfPath);
                    const li = listItems.find(el => normalizePath(el.title) === normalizedTarget);
                    if (li) {
                        loadPdf(li.title, li);
                    }
                }
            });
        } else {
            // No project in URL — redirect to home
            window.location.href = '/home';
        }
    }

    btnUploadTrigger.addEventListener('click', () => {
        if (currentProject) fileUploadInput.click();
    });

    btnRefresh.addEventListener('click', fetchPdfs);

    // Kick off — read project from URL
    initProject();


    fileUploadInput.addEventListener('change', async () => {
        if (fileUploadInput.files.length === 0 || !currentProject) return;
        const file = fileUploadInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        
        fileList.innerHTML = '<li class="empty-state">Uploading PDF...</li>';
        btnUploadTrigger.disabled = true;
        btnRefresh.disabled = true;
        
        try {
            const res = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/upload`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Upload failed');
            await fetchPdfs();
        } catch (e) {
            alert(`Upload error: ${e.message}`);
            await fetchPdfs();
        } finally {
            fileUploadInput.value = '';
        }
    });

    // --- API Interactions ---
    async function fetchAnnotations() {
        if (!currentProject) {
            projectAnnotations = [];
            return;
        }
        try {
            const res = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/annotations`);
            if (res.ok) {
                projectAnnotations = await res.json();
            } else {
                projectAnnotations = [];
            }
        } catch (e) {
            console.error('Failed to fetch annotations:', e);
            projectAnnotations = [];
        }
    }

    function overlayPatternRects(pageNum, svg) {
        // Remove any previous pattern rects for this page
        svg.querySelectorAll('.pattern-highlight-rect').forEach(el => el.remove());

        if (typeof currentPdfPatterns === 'undefined') return;
        
        const patternsForPage = currentPdfPatterns.filter(p => parseInt(p.page_num) === parseInt(pageNum));
        patternsForPage.forEach(pattern => {
            if (!pattern.vectors || pattern.vectors.length === 0) return;
            const patternType = normalizePatternType(pattern.type);
            
            // Calculate bounding box across all vector types
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            function expandBbox(x, y) {
                if (x < minX) minX = x;
                if (x > maxX) maxX = x;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
            }
            pattern.vectors.forEach(v => {
                if (v.start && v.end) {
                    expandBbox(v.start[0], v.start[1]);
                    expandBbox(v.end[0], v.end[1]);
                }
                if (v.points && v.points.length) {
                    v.points.forEach(p => expandBbox(p[0], p[1]));
                }
                if (v.x != null && v.y != null && v.width != null && v.height != null) {
                    expandBbox(v.x, v.y);
                    expandBbox(v.x + v.width, v.y + v.height);
                }
            });
            
            // Add some padding
            const padding = 5;
            minX -= padding;
            minY -= padding;
            maxX += padding;
            maxY += padding;

            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', minX);
            rect.setAttribute('y', minY);
            rect.setAttribute('width', maxX - minX);
            rect.setAttribute('height', maxY - minY);
            rect.setAttribute('rx', 4);
            rect.setAttribute('ry', 4);
            rect.classList.add('pattern-highlight-rect');
            rect.dataset.id = pattern.id;
            
            if (patternType === 'grill') {
                rect.classList.add('pattern-grill');
            } else {
                rect.classList.add('pattern-aac');
            }
            rect.setAttribute('title', `${getPatternTypeLabel(pattern.type)}: ${pattern.name}`);

            if (selectedPatterns.has(pattern.id)) {
                rect.classList.add('selected');
            }

            rect.addEventListener('click', (e) => {
                if (selectionMode) return; // Allow selection underneath if adding new pattern
                e.stopPropagation();
                handlePatternSelection(pattern, e);
                if (selectedPatterns.has(pattern.id)) {
                    flashPattern(pattern);
                    showPatternInInspector(pattern);
                }
            });

            svg.appendChild(rect);
        });
    }

    function overlayStampRects(pageNum, svg) {
        // Remove any previous stamp rects for this page
        svg.querySelectorAll('.stamp-highlight-rect').forEach(el => el.remove());
        svg.querySelectorAll('.stamp-hover-text').forEach(el => el.remove());

        const stampsForPage = currentPdfStamps.filter(s => parseInt(s.page_num) === parseInt(pageNum));
        stampsForPage.forEach(stamp => {
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', stamp.rect[0]);
            rect.setAttribute('y', stamp.rect[1]);
            rect.setAttribute('width', stamp.rect[2] - stamp.rect[0]);
            rect.setAttribute('height', stamp.rect[3] - stamp.rect[1]);
            rect.setAttribute('rx', 4);
            rect.setAttribute('ry', 4);
            rect.classList.add('stamp-highlight-rect');
            rect.setAttribute('title', stamp.name || stamp.title || 'Stamp');
            rect.dataset.xref = stamp.xref;

            if (selectedStamps.has(stamp.xref)) {
                rect.classList.add('selected');
            }

            rect.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                handleStampSelection(stamp, e);
                if (selectedStamps.has(stamp.xref)) {
                    // Switch to Stamps tab and show sidebar
                    switchSidebarTab('stamps');
                    toggleSidebarRight(true);
                    
                    // Scroll to it in stamps list
                    const targetLi = stampsList.querySelector(`li[data-xref="${stamp.xref}"]`);
                    if (targetLi) {
                        targetLi.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                }
            });

            rect.addEventListener('dblclick', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const hyperlink = getStampHyperlink(stamp);
                if (hyperlink) {
                    if (hyperlink.includes('/stamp/') || hyperlink.includes('#stamp-')) {
                        const match = hyperlink.match(/#stamp-([a-zA-Z0-9\-]+)/) || hyperlink.match(/\/stamp\/([a-zA-Z0-9\-]+)/);
                        if (match) {
                            const hashVal = match[1];
                            window.location.hash = `stamp-${hashVal}`;
                            const project = currentProject || window.currentProject || '';
                            if (window.openStampMetaEditor) {
                                const targetStamp = currentPdfStamps.find(s => s.xref.toString() === hashVal || s.name === hashVal || s.stamp_uuid === hashVal) || stamp;
                                const title = targetStamp.pattern_name || targetStamp.name || targetStamp.title || 'Stamp ' + targetStamp.xref;
                                window.openStampMetaEditor(project, currentPdf, pageNum, targetStamp.xref, title, targetStamp.pattern_name || targetStamp.name);
                            }
                        }
                    } else if (hyperlink.startsWith('http')) {
                        window.open(hyperlink, '_blank');
                    }
                }
            });

            svg.appendChild(rect);

            // Add hover text if configured
            if (window.globalTagsConfig && window.globalTagsConfig.hoverFields && window.globalTagsConfig.hoverFields.length > 0 && stamp.fields) {
                const hoverTexts = [];
                const allFieldsObj = {};
                stamp.fields.forEach(f => { allFieldsObj[f.name] = f.value; });
                
                window.globalTagsConfig.hoverFields.forEach(hf => {
                    const field = stamp.fields.find(f => f.name === hf);
                    if (field && field.value) {
                        let fieldColor = null;
                        if (field.conditional_formatting && window.evaluateConditionalFormattingRaw) {
                            try {
                                const rules = JSON.parse(field.conditional_formatting);
                                fieldColor = window.evaluateConditionalFormattingRaw(field.value, rules, allFieldsObj);
                            } catch(e) {}
                        }
                        hoverTexts.push({ text: `${hf}: ${field.value}`, color: fieldColor });
                    }
                });
                
                if (hoverTexts.length > 0) {
                    const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    textEl.setAttribute('x', stamp.rect[2] + 4);
                    textEl.setAttribute('y', stamp.rect[1] + 10);
                    textEl.setAttribute('fill', 'var(--text-primary, #e2e8f0)');
                    textEl.style.fontSize = 'calc(14px / var(--pdf-scale, 1))';
                    textEl.setAttribute('font-family', 'Inter, sans-serif');
                    textEl.classList.add('stamp-hover-text');
                    textEl.style.pointerEvents = 'none';
                    
                    hoverTexts.forEach((ht, idx) => {
                        const tspan = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
                        tspan.setAttribute('x', stamp.rect[2] + 4);
                        if (idx > 0) {
                            tspan.setAttribute('dy', '1.2em');
                        }
                        if (ht.color) {
                            tspan.setAttribute('fill', ht.color);
                            tspan.style.fontWeight = 'bold';
                        }
                        tspan.textContent = ht.text;
                        textEl.appendChild(tspan);
                    });
                    
                    svg.appendChild(textEl);
                }
            }
        });
    }

    window.redrawStampVisuals = function() {
        if (!currentPdf || !currentPdfStamps) return;
        document.querySelectorAll('.page-wrapper').forEach(wrapper => {
            const pageNum = parseInt(wrapper.dataset.page);
            const svg = wrapper.querySelector('.vector-overlay') || wrapper.querySelector('.selection-overlay');
            if (svg) overlayStampRects(pageNum, svg);
        });
    };

    function handleStampSelection(stamp, e) {
        const index = currentPdfStamps.findIndex(s => s.xref === stamp.xref);
        if (index === -1) return;

        if (e && (e.ctrlKey || e.metaKey)) {
            if (selectedStamps.has(stamp.xref)) {
                selectedStamps.delete(stamp.xref);
            } else {
                selectedStamps.add(stamp.xref);
                lastSelectedStampIndex = index;
            }
        } else if (e && e.shiftKey && lastSelectedStampIndex !== -1) {
            const start = Math.min(lastSelectedStampIndex, index);
            const end = Math.max(lastSelectedStampIndex, index);
            selectedStamps.clear();
            for (let i = start; i <= end; i++) {
                selectedStamps.add(currentPdfStamps[i].xref);
            }
        } else {
            selectedStamps.clear();
            selectedStamps.add(stamp.xref);
            lastSelectedStampIndex = index;
        }

        updateStampSelections();
    }

    function updateStampSelections() {
        document.querySelectorAll('.stamp-highlight-rect').forEach(el => {
            el.classList.toggle('selected', selectedStamps.has(parseInt(el.dataset.xref)));
        });
        document.querySelectorAll('#stamps-list .stamp-row').forEach(row => {
            row.classList.toggle('selected', selectedStamps.has(parseInt(row.dataset.xref)));
        });
    }

    function selectStamp(stamp) {
        handleStampSelection(stamp, null);
        switchSidebarTab('stamps');
        toggleSidebarRight(true);
    }

    function handlePatternSelection(pattern, e) {
        const list = patternFilter ? currentPdfPatterns.filter(p => getPatternFilterType(p.type) === patternFilter) : currentPdfPatterns;
        const index = list.findIndex(p => p.id === pattern.id);
        if (index === -1) return;

        if (e && (e.ctrlKey || e.metaKey)) {
            if (selectedPatterns.has(pattern.id)) {
                selectedPatterns.delete(pattern.id);
            } else {
                selectedPatterns.add(pattern.id);
                lastSelectedPatternIndex = index;
            }
        } else if (e && e.shiftKey && lastSelectedPatternIndex !== -1) {
            const start = Math.min(lastSelectedPatternIndex, index);
            const end = Math.max(lastSelectedPatternIndex, index);
            selectedPatterns.clear();
            for (let i = start; i <= end; i++) {
                selectedPatterns.add(list[i].id);
            }
        } else {
            selectedPatterns.clear();
            selectedPatterns.add(pattern.id);
            lastSelectedPatternIndex = index;
        }

        updatePatternSelections();
    }

    function updatePatternSelections() {
        document.querySelectorAll('.pattern-highlight-rect').forEach(el => {
            el.classList.toggle('selected', selectedPatterns.has(el.dataset.id));
        });
        document.querySelectorAll('#patterns-list .stamp-row').forEach(row => {
            row.classList.toggle('selected', selectedPatterns.has(row.dataset.id));
        });
    }

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
            const panelStampsActive = panelStamps && panelStamps.classList.contains('active');
            const panelPatternsActive = panelPatterns && panelPatterns.classList.contains('active');
            
            if (panelStampsActive) {
                e.preventDefault();
                selectedStamps.clear();
                currentPdfStamps.forEach(s => selectedStamps.add(s.xref));
                updateStampSelections();
            } else if (panelPatternsActive) {
                e.preventDefault();
                selectedPatterns.clear();
                const filteredPatterns = patternFilter
                    ? currentPdfPatterns.filter(p => getPatternFilterType(p.type) === patternFilter)
                    : currentPdfPatterns;
                filteredPatterns.forEach(p => selectedPatterns.add(p.id));
                updatePatternSelections();
            }
        }
    });

    async function fetchPdfs() {
        if (!currentProject) {
            fileList.innerHTML = '<li class="empty-state">Select a project to view files.</li>';
            btnRefresh.disabled = true;
            btnUploadTrigger.disabled = true;
            btnRunMatching.disabled = true;
            btnRunPatterns.disabled = true;
            if (btnRunStamps) btnRunStamps.disabled = true;
            return;
        }
        
        btnRefresh.disabled = true;
        btnUploadTrigger.disabled = true;
        btnRunMatching.disabled = true;
        btnRunPatterns.disabled = true;
        if (btnRunStamps) btnRunStamps.disabled = true;
        fileList.innerHTML = '<li class="empty-state">Loading project files...</li>';
        try {
            const res = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/pdfs`);
            if (!res.ok) throw new Error(await res.text() || 'Failed to fetch project files');
            const pdfs = await res.json();
            
            btnRefresh.disabled = false;
            btnUploadTrigger.disabled = false;
            
            if (pdfs.length === 0) {
                fileList.innerHTML = '<li class="empty-state">No PDFs found in project. Click the upload button (↑) to add one!</li>';
                return;
            }
            
            fileList.innerHTML = '';
            pdfs.forEach(pdf => {
                const li = document.createElement('li');
                li.title = pdf.path;
                
                const nameSpan = document.createElement('span');
                nameSpan.className = 'file-name';
                nameSpan.textContent = pdf.name;
                li.appendChild(nameSpan);
                
                const actionsContainer = document.createElement('div');
                actionsContainer.className = 'file-actions-container';
                
                const menuBtn = document.createElement('button');
                menuBtn.className = 'file-menu-btn';
                menuBtn.innerHTML = '⋮';
                menuBtn.title = 'File actions';
                actionsContainer.appendChild(menuBtn);
                
                const dropdown = document.createElement('div');
                dropdown.className = 'file-menu-dropdown';
                
                const downloadLink = document.createElement('button');
                downloadLink.className = 'file-menu-item';
                downloadLink.innerHTML = '📥 Download';
                downloadLink.addEventListener('click', (e) => {
                    e.stopPropagation();
                    dropdown.classList.remove('show');
                    
                    const a = document.createElement('a');
                    a.href = `/api/pdf/${encodeURIComponent(pdf.path)}/raw`;
                    a.download = pdf.name;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                });
                
                const deleteLink = document.createElement('button');
                deleteLink.className = 'file-menu-item delete-item';
                deleteLink.innerHTML = '🗑 Delete';
                deleteLink.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    dropdown.classList.remove('show');
                    if (!confirm(`Delete ${pdf.name}?\nThis permanently deletes the file and all its database annotations.`)) return;
                    
                    try {
                        const res = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/pdf/${encodeURIComponent(pdf.path)}`, {
                            method: 'DELETE'
                        });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.error || 'Delete failed');
                        
                        // If the currently loaded PDF is this one, clear viewport
                        if (currentPdf === pdf.path) {
                            currentPdf = null;
                            window.currentPdf = null;
                            currentPage = 1;
                            if (typeof currentPdfJsDoc !== 'undefined') {
                                currentPdfJsDoc = null;
                            }
                            if (typeof pagesData !== 'undefined') {
                                pagesData.clear();
                            }
                            if (typeof canvasRenderers !== 'undefined') {
                                canvasRenderers.forEach(r => r.destroy());
                                canvasRenderers.clear();
                            }
                            
                            // Reset URL parameter
                            const urlObj = new URL(window.location);
                            urlObj.searchParams.delete('pdf');
                            window.history.pushState({}, '', urlObj);
                            
                            // Clear viewer container
                            panZoomContainer.innerHTML = '';
                            currentPdfStamps = [];
                            currentPdfPatterns = [];
                            renderStampsList();
                            renderPatternsList();
                            // Disable scanner buttons
                            btnRunMatching.disabled = true;
                            btnRunPatterns.disabled = true;
                            if (btnRunStamps) btnRunStamps.disabled = true;
                            if (btnUndoPdf) btnUndoPdf.disabled = true;
                            scannerStatus.textContent = '';
                        }
                        
                        // Reload pdf list
                        await fetchPdfs();
                    } catch (err) {
                        alert('Error deleting PDF: ' + err.message);
                    }
                });
                
                dropdown.appendChild(downloadLink);
                dropdown.appendChild(deleteLink);
                actionsContainer.appendChild(dropdown);
                li.appendChild(actionsContainer);
                
                // Toggle dropdown menu
                menuBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    // Close any other open dropdowns first
                    document.querySelectorAll('.file-menu-dropdown').forEach(d => {
                        if (d !== dropdown) d.classList.remove('show');
                    });
                    dropdown.classList.toggle('show');
                });
                
                // Clicking outside dropdown closes it
                document.addEventListener('click', () => {
                    dropdown.classList.remove('show');
                });
                
                li.addEventListener('click', (e) => {
                    if (e.target.closest('.file-actions-container')) return;
                    if (window.location.hash) {
                        const url = new URL(window.location.href);
                        url.hash = "";
                        window.history.replaceState({}, document.title, url.pathname + url.search);
                    }
                    loadPdf(pdf.path, li);
                });
                fileList.appendChild(li);
            });
            removeGeneratedFileEntries();
        } catch (e) {
            fileList.innerHTML = `<li class="empty-state" style="color:red">Error: ${e.message}</li>`;
            btnRefresh.disabled = false;
            btnUploadTrigger.disabled = false;
        }
    }

    async function loadPdf(path, liElement) {
        // Show loading overlay immediately
        const shortName = path.split('/').pop();
        if (window.appendScannerLog) window.appendScannerLog("> Loading new PDF in canvas: " + shortName);
        showLoadingOverlay(shortName, 'Initialising…');
        setLoadingProgress(5);

        // Update UI
        document.querySelectorAll('.file-list li').forEach(li => li.classList.remove('active'));
        liElement.classList.add('active');
        
        currentPdf = path;
        window.currentPdf = path;
        currentPage = 1;
        
        // Update browser URL to reflect the opened PDF
        const _urlObj = new URL(window.location);
        _urlObj.searchParams.set('pdf', path);
        window.history.pushState({}, '', _urlObj);
        canUndoPatternScan = false;
        updateUndoButtonState();
        clearSelection();
        
        // Enable scanner buttons
        btnRunMatching.disabled = false;
        btnRunPatterns.disabled = false;
        if (btnRunStamps) btnRunStamps.disabled = false;
        updateUndoButtonState();
        scannerStatus.textContent = '';
        scannerSpinner.style.display = 'none';

        let stampToOpen = null;
        let stampsFetched = false;

        // If URL hash contains a stamp reference, load stamps early and open popup first
        if (window.location.hash.startsWith('#stamp-')) {
            const hashVal = window.location.hash.replace('#stamp-', '');
            try {
                const stampsRes = await fetch(`/api/pdf/${encodeURIComponent(path)}/stamps`);
                if (stampsRes.ok) {
                    currentPdfStamps = await stampsRes.json();
                    stampsFetched = true;
                    stampToOpen = currentPdfStamps.find(s => s.xref.toString() === hashVal || s.name === hashVal || s.stamp_uuid === hashVal);
                    if (stampToOpen) {
                        currentPage = parseInt(stampToOpen.page_num) || 1;
                        
                        // Select the stamp in UI and state immediately
                        selectedStamps.clear();
                        selectedStamps.add(stampToOpen.xref);
                        lastSelectedStampIndex = currentPdfStamps.indexOf(stampToOpen);
                        updateStampSelections();
                        switchSidebarTab('stamps');
                        toggleSidebarRight(true);

                        // Open metadata editor popup immediately
                        const project = currentProject || window.currentProject || '';
                        const title = stampToOpen.pattern_name || stampToOpen.name || stampToOpen.title || 'Stamp ' + stampToOpen.xref;
                        if (window.openStampMetaEditor) {
                            window.openStampMetaEditor(project, path, currentPage, stampToOpen.xref, title, stampToOpen.pattern_name || stampToOpen.name);
                        }
                    }
                }
            } catch (e) {
                console.error('Failed to load stamps early:', e);
            }
        }
        
        try {
            console.time('fetchAnnotations');
            setLoadingProgress(10, 'Loading annotations…');
            await fetchAnnotations();
            console.timeEnd('fetchAnnotations');
            
            // Fetch stamps if not already fetched
            console.time('fetchStamps');
            setLoadingProgress(20, 'Loading stamps…');
            selectedStamp = null;
            if (!stampsFetched) {
                currentPdfStamps = [];
                try {
                    const stampsRes = await fetch(`/api/pdf/${encodeURIComponent(path)}/stamps`);
                    if (stampsRes.ok) {
                        currentPdfStamps = await stampsRes.json();
                    }
                } catch (e) {
                    console.error('Failed to load stamps:', e);
                }
            }
            console.timeEnd('fetchStamps');
            renderStampsList();

            // Fetch patterns
            console.time('fetchPatterns');
            setLoadingProgress(30, 'Loading patterns…');
            currentPdfPatterns = [];
            try {
                if (currentProject) {
                    const patternsRes = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/pdf/${encodeURIComponent(path)}/patterns`);
                    if (patternsRes.ok) {
                        currentPdfPatterns = await patternsRes.json();
                    }
                }
            } catch (e) {
                console.error('Failed to load patterns:', e);
            }
            console.timeEnd('fetchPatterns');
            renderPatternsList();

            console.time('fetchPageInfo');
            setLoadingProgress(40, 'Fetching page info…');
            const res = await fetch(`/api/pdf/${encodeURIComponent(path)}/info`);
            const info = await res.json();
            console.timeEnd('fetchPageInfo');
            totalPages = info.page_count;
            pageTotal.textContent = totalPages;
            
            console.time('reloadView');
            setLoadingProgress(60, 'Initializing renderer…');
            await reloadView();
            console.timeEnd('reloadView');
            if (stampToOpen) {
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        zoomToStamp(stampToOpen);
                    });
                });
            }
        } catch (e) {
            hideLoadingOverlay();
            alert('Failed to load PDF info: ' + e.message);
        }
    }

    // Intersection Observer for lazy loading pages
    const loadQueue = [];
    let activeLoads = 0;
    const MAX_CONCURRENT_LOADS = 2; // Prevent locking up the Python backend

    function queuePageLoad(wrapper, pageNum, rid) {
        loadQueue.push({ wrapper, pageNum, rid });
        processLoadQueue();
    }

    function processLoadQueue() {
        if (activeLoads >= MAX_CONCURRENT_LOADS || loadQueue.length === 0) return;
        
        // Sort queue by distance to current view so the visible pages load first
        loadQueue.sort((a, b) => Math.abs(a.pageNum - currentPage) - Math.abs(b.pageNum - currentPage));
        
        const task = loadQueue.shift();
        activeLoads++;
        
        loadPageContent(task.wrapper, task.pageNum, task.rid).finally(() => {
            activeLoads--;
            processLoadQueue();
        });
    }

    const pageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const wrapper = entry.target;
                if (!wrapper.dataset.loaded) {
                    wrapper.dataset.loaded = 'true';
                    const pageNum = parseInt(wrapper.dataset.page);
                    const rid = parseInt(wrapper.dataset.renderId);
                    queuePageLoad(wrapper, pageNum, rid);
                }
            }
        });
    }, {
        root: viewerContainer,
        rootMargin: '200px' // Reduced pre-load margin to prevent massive parallel requests
    });

    async function reloadView() {
        const currentRenderId = ++renderId;
        pageObserver.disconnect();
        
        // Clear all pages from DOM
        Array.from(panZoomContainer.children).forEach(child => {
            if (child.id !== 'selection-lasso') {
                panZoomContainer.removeChild(child);
            }
        });
        pagesData.clear();
        canvasRenderers.forEach(r => r.destroy());
        canvasRenderers.clear();
        
        // Reset transform to 0 before rendering
        scale = 1.0;
        translateX = 0;
        translateY = 0;
        updateTransform();
        
        if (layoutMode === 'single') {
            await createAndLoadPage(currentPage, currentRenderId);
            if (renderId === currentRenderId) {
                // Double rAF: ensures browser has computed layout (offsetLeft/offsetTop)
                // before resetTransform reads them. Without this the page opens sideways.
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        resetTransform(true);
                        hideLoadingOverlay();
                    });
                });
            }
        } else if (layoutMode === 'continuous') {
            // Load page 1 first to get accurate default dimensions
            const p1 = await createAndLoadPage(1, currentRenderId);
            if (renderId !== currentRenderId) return;
            
            // Double rAF for correct layout before transform
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    resetTransform(true);
                    hideLoadingOverlay();
                });
            });
            
            const defW = p1 ? p1.bounds.width : 800;
            const defH = p1 ? p1.bounds.height : 1100;
            
            // Create placeholders for the rest of the pages instantly
            for (let i = 2; i <= totalPages; i++) {
                if (renderId !== currentRenderId) return;
                const wrapper = createPagePlaceholder(i, defW, defH, currentRenderId);
                panZoomContainer.appendChild(wrapper);
                invalidatePageRects();
                pageObserver.observe(wrapper);
            }
        }
    }

    async function createAndLoadPage(pageNum, currentRenderId) {
        const wrapper = createPagePlaceholder(pageNum, 800, 1100, currentRenderId);
        panZoomContainer.appendChild(wrapper);
        invalidatePageRects();
        wrapper.dataset.loaded = 'true';
        return await loadPageContent(wrapper, pageNum, currentRenderId);
    }

    function createPagePlaceholder(pageNum, w, h, currentRenderId) {
        const pageWrapper = document.createElement('div');
        pageWrapper.className = 'page-wrapper';
        pageWrapper.id = `page-wrapper-${pageNum}`;
        pageWrapper.dataset.page = pageNum;
        pageWrapper.dataset.renderId = currentRenderId;
        pageWrapper.style.width = `${w}px`;
        pageWrapper.style.height = `${h}px`;
        pageWrapper.innerHTML = `<div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); color:#94a3b8; font-family:sans-serif;">Loading Page ${pageNum}...</div>`;
        return pageWrapper;
    }

    async function loadPageContent(wrapper, pageNum, currentRenderId) {
        if (!currentPdf || pageNum < 1 || pageNum > totalPages) return null;
        
        // Always update UI
        updatePageDisplay(currentPage);
        btnPrev.disabled = currentPage <= 1;
        btnNext.disabled = currentPage >= totalPages;
        
        const encPath = encodeURIComponent(currentPdf);
        
        try {
            console.time(`fetchDrawings_page_${pageNum}`);
            if (pageNum === 1) setLoadingProgress(70, 'Fetching drawing data… (Connecting)');
            const res = await fetch(`/api/pdf/${encPath}/page/${pageNum}/drawings`);
            
            // Read response stream to report real-time download progress
            const contentLength = res.headers.get('content-length');
            const total = contentLength ? parseInt(contentLength, 10) : 0;
            let loaded = 0;
            
            const reader = res.body.getReader();
            const chunks = [];
            
            while(true) {
                const {done, value} = await reader.read();
                if (done) break;
                chunks.push(value);
                loaded += value.length;
                
                if (pageNum === 1) {
                    const mbLoaded = (loaded / 1024 / 1024).toFixed(1);
                    if (total) {
                        const mbTotal = (total / 1024 / 1024).toFixed(1);
                        const pct = Math.round((loaded / total) * 100);
                        // Map 0-100% download to 70-80% overall progress
                        setLoadingProgress(70 + (pct * 0.1), `Fetching drawing data… ${mbLoaded}MB / ${mbTotal}MB (${pct}%)`);
                    } else {
                        setLoadingProgress(75, `Fetching drawing data… ${mbLoaded}MB downloaded`);
                    }
                }
            }
            
            // Reconstruct JSON from stream chunks
            if (pageNum === 1) setLoadingProgress(80, 'Parsing drawing data…');
            const allChunks = new Uint8Array(loaded);
            let position = 0;
            for(let chunk of chunks) {
                allChunks.set(chunk, position);
                position += chunk.length;
            }
            const text = new TextDecoder("utf-8").decode(allChunks);
            const data = JSON.parse(text);
            console.timeEnd(`fetchDrawings_page_${pageNum}`);
            
            if (renderId !== currentRenderId) return null; // Abort
            if (data.error) throw new Error(data.error);
            
            pagesData.set(pageNum, data);
            wrapper.innerHTML = ''; // clear loading text
            
            // Set dimensions
            wrapper.style.width = `${data.page_bounds.width}px`;
            wrapper.style.height = `${data.page_bounds.height}px`;
            
            // Create Image
            const img = document.createElement('img');
            img.className = 'pdf-image';
            img.dataset.loadedScale = 2;
            if (pageNum === 1) setLoadingProgress(80, 'Fetching PDF image…');
            img.src = `/api/pdf/${encPath}/page/${pageNum}/image?scale=2&t=${pdfCacheBuster}`;
            
            // Create SVG Overlay
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('class', 'vector-overlay page-svg');
            svg.setAttribute('preserveAspectRatio', 'none');
            svg.setAttribute('viewBox', `0 0 ${data.page_bounds.width} ${data.page_bounds.height}`);
            
            wrapper.appendChild(img);
            wrapper.appendChild(svg);
            
            if (pageNum === 1) setLoadingProgress(90, 'Building overlays…');
            
            // Map globalIds and pre-calculate area to prevent O(N log N) freezing during sort
            data.drawings.forEach(item => {
                const globalId = `p${pageNum}-${item.id}`;
                item.globalId = globalId;
                item.page = pageNum;
                
                // Pre-calculate area for sorting
                if (item.type === 'Line') item._cachedArea = 0;
                else if (item.type === 'Rect') item._cachedArea = Math.abs(item.width * item.height);
                else if (item.type === 'Polygon' || item.type === 'Arc/Curve') {
                    const xs = item.points.map(p => p[0]);
                    const ys = item.points.map(p => p[1]);
                    item._cachedArea = (Math.max(...xs) - Math.min(...xs)) * (Math.max(...ys) - Math.min(...ys));
                } else {
                    item._cachedArea = 0;
                }
            });
            
            // Sort drawings by area in descending order (largest first, smallest last)
            // This ensures smaller hit targets are rendered on top of larger ones (e.g. background rects)
            data.drawings.sort((a, b) => b._cachedArea - a._cachedArea);
            
            // Render SVG vectors
            if (showVectors) {
                if (currentRendererSetting === 'canvas') {
                    console.time(`initCanvasRenderer_page_${pageNum}`);
                    const renderer = new CanvasVectorRenderer(wrapper, data.page_bounds, data.drawings, pageNum);
                    canvasRenderers.set(pageNum, renderer);
                    console.timeEnd(`initCanvasRenderer_page_${pageNum}`);
                    // Draw initial highlights
                    setTimeout(() => refreshCanvasHighlights(), 0);
                } else {
                    data.drawings.forEach(item => {
                        let el;
                        if (item.type === 'Line') {
                            el = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                            el.setAttribute('x1', item.start[0]); el.setAttribute('y1', item.start[1]);
                            el.setAttribute('x2', item.end[0]); el.setAttribute('y2', item.end[1]);
                        } else if (item.type === 'Rect') {
                            el = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                            el.setAttribute('x', item.x); el.setAttribute('y', item.y);
                            el.setAttribute('width', item.width); el.setAttribute('height', item.height);
                        } else if (item.type === 'Polygon') {
                            el = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                            const ptsStr = item.points.map(p => `${p[0]},${p[1]}`).join(' ');
                            el.setAttribute('points', ptsStr);
                        } else if (item.type === 'Arc/Curve') {
                            el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                            const pts = item.points;
                            el.setAttribute('d', `M ${pts[0][0]} ${pts[0][1]} C ${pts[1][0]} ${pts[1][1]}, ${pts[2][0]} ${pts[2][1]}, ${pts[3][0]} ${pts[3][1]}`);
                        }
                        
                        if (el) {
                            el.classList.add('vector-item');
                            const globalId = item.globalId;
                            el.id = `vec-${globalId}`;
                            
                            el.style.setProperty('--base-width', `${Math.max(item.thickness, 0.5)}px`);
                            el.style.strokeWidth = `${Math.max(item.thickness, 0.5)}px`;
                            el.style.stroke = item.color_hex || '#000000';
                            el.style.fill = 'none'; // Must be none, otherwise it obscures text on the base image
                            el.setAttribute('opacity', '0'); // Hidden by default (CSS handles hover visibility)
                            
                            el.dataset.id = globalId;
                            
                            // Create an invisible wider hit target for easier mouse interaction
                            const hitTarget = el.cloneNode(true);
                            hitTarget.removeAttribute('id');
                            hitTarget.removeAttribute('opacity');
                            hitTarget.classList.remove('vector-item');
                            hitTarget.classList.add('vector-item-hit-target');
                            hitTarget.style.stroke = item.color_hex || '#000000';
                            hitTarget.style.strokeOpacity = '0';
                            hitTarget.style.strokeWidth = '10px';
                            hitTarget.style.fill = 'none';
                            
                            // Store item data for event delegation
                            hitTarget._itemData = item;
                            
                            // Append hitTarget FIRST, then visible el SECOND to support CSS sibling selector '+'
                            svg.appendChild(hitTarget);
                            svg.appendChild(el);
                            
                            if (selectedItems.has(globalId)) {
                                el.classList.add('selected');
                            }
                            if (highlightedItemId === globalId) {
                                el.classList.add('highlighted');
                                console.log(`[Load Page Content] Re-applied highlighted class to: vec-${globalId}`, el);
                            }
                        }
                    });
                }
            } // end if (showVectors)
            
            // Render clickable hyperlink zones on SVG overlay
            if (data.links && data.links.length > 0) {
                data.links.forEach(link => {
                    const linkEl = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    linkEl.setAttribute('x', link.x);
                    linkEl.setAttribute('y', link.y);
                    linkEl.setAttribute('width', link.width);
                    linkEl.setAttribute('height', link.height);
                    linkEl.setAttribute('fill', 'transparent');
                    linkEl.setAttribute('stroke', 'none');
                    linkEl.style.cursor = 'pointer';
                    linkEl.style.pointerEvents = 'auto';
                    linkEl.classList.add('pdf-link-zone');
                    linkEl.dataset.uri = link.uri;
                    linkEl.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const uri = link.uri;
                        if (uri.includes('/stamp/') || uri.includes('#stamp-')) {
                            const match = uri.match(/#stamp-([a-zA-Z0-9\-]+)/) || uri.match(/\/stamp\/([a-zA-Z0-9\-]+)/);
                            if (match) {
                                const hashVal = match[1];
                                window.location.hash = `stamp-${hashVal}`;
                                const project = currentProject || window.currentProject || '';
                                if (window.openStampMetaEditor) {
                                    const stamp = currentPdfStamps.find(s => s.xref.toString() === hashVal || s.name === hashVal || s.stamp_uuid === hashVal);
                                    const xref = stamp ? stamp.xref : (Number(hashVal) || hashVal);
                                    const title = stamp ? (stamp.pattern_name || stamp.name || stamp.title || 'Stamp ' + xref) : 'Stamp ' + hashVal;
                                    const stampName = stamp ? (stamp.pattern_name || stamp.name) : undefined;
                                    window.openStampMetaEditor(project, currentPdf, pageNum, xref, title, stampName);
                                }
                            }
                        } else if (uri.startsWith('http') || uri.startsWith('mailto') || uri.startsWith('tel')) {
                            window.open(uri, '_blank');
                        }
                    });
                    svg.appendChild(linkEl);
                });
            }
            
            overlayPatternRects(pageNum, svg);
            overlayStampRects(pageNum, svg);
            return { bounds: data.page_bounds };
            
        } catch (e) {
            console.error(`Failed to load page ${pageNum}:`, e);
            wrapper.innerHTML = `<div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); color:red;">Error loading page ${pageNum}</div>`;
            return null;
        }
    }

    // --- Layout Controls ---
    function applyLayout() {
        const allWrappers = panZoomContainer.querySelectorAll('.page-wrapper');
        if (layoutMode === 'single') {
            // Hide all pages except the current one
            allWrappers.forEach(w => {
                const pg = parseInt(w.dataset.page);
                w.style.display = pg === currentPage ? '' : 'none';
            });
            updateCustomScrollbar();
            resetTransform(true);
        } else {
            // Show all pages; ensure non-rendered placeholders exist for continuous scroll
            allWrappers.forEach(w => { w.style.display = ''; });

            // If pages beyond what's rendered don't exist yet, create placeholders
            const existingPages = new Set([...allWrappers].map(w => parseInt(w.dataset.page)));
            // Get dimensions from first rendered page as reference
            const firstWrapper = panZoomContainer.querySelector('.page-wrapper');
            const defW = firstWrapper ? firstWrapper.offsetWidth : 800;
            const defH = firstWrapper ? firstWrapper.offsetHeight : 1100;
            const currentRenderId = renderId;
            for (let i = 1; i <= totalPages; i++) {
                if (!existingPages.has(i)) {
                    const wrapper = createPagePlaceholder(i, defW, defH, currentRenderId);
                    // Insert in correct page order
                    const after = panZoomContainer.querySelector(`.page-wrapper[data-page="${i - 1}"]`);
                    if (after && after.nextSibling) {
                        panZoomContainer.insertBefore(wrapper, after.nextSibling);
                    } else {
                        panZoomContainer.appendChild(wrapper);
                    }
                    invalidatePageRects();
                    pageObserver.observe(wrapper);
                }
            }
            updateCustomScrollbar();
            // Scroll to the current page position
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    scrollToPage(currentPage);
                });
            });
        }
    }

    if (btnLayoutToggle) {
        btnLayoutToggle.textContent = layoutMode === 'single' ? 'Layout: Single Page' : 'Layout: Continuous';
        btnLayoutToggle.addEventListener('click', () => {
            layoutMode = layoutMode === 'single' ? 'continuous' : 'single';
            btnLayoutToggle.textContent = layoutMode === 'single' ? 'Layout: Single Page' : 'Layout: Continuous';
            applyLayout();
        });
    }

    // --- Viewport & Transform (Zoom/Pan) ---
    let transformUpdatePending = false;
    function updateTransform() {
        if (transformUpdatePending) return;
        transformUpdatePending = true;
        requestAnimationFrame(() => {
            transformUpdatePending = false;
            applyTransform();
        });
    }

    function applyTransform() {
        const cw = panZoomContainer.offsetWidth * scale;
        const ch = panZoomContainer.offsetHeight * scale;
        const vw = viewerContainer.clientWidth;
        const vh = viewerContainer.clientHeight;
        
        const margin = 20; // 20px padding at the edges
        
        // Prevent scrolling into darkness
        if (cw <= vw) {
            translateX = (vw - cw) / 2; // Lock to center horizontally
        } else {
            translateX = Math.max(vw - cw - margin, Math.min(margin, translateX));
        }

        if (ch <= vh) {
            translateY = (vh - ch) / 2; // Lock to center vertically
        } else {
            translateY = Math.max(vh - ch - margin, Math.min(margin, translateY));
        }

        panZoomContainer.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
        panZoomContainer.style.setProperty('--pdf-scale', scale);
        zoomLevelDisplay.textContent = `${Math.round(scale * 100)}%`;

        // Update current page counter in continuous mode based on scroll position
        if (layoutMode === 'continuous' && totalPages > 1) {
            const pageRects = getPageRects();
            const viewCenterY = (viewerContainer.clientHeight / 2 - translateY) / scale;
            
            let bestPage = currentPage;
            let minDistance = Infinity;
            
            for (const pr of pageRects) {
                const pageNum = parseInt(pr.pageNum);
                const wrapperCenterY = pr.offsetTop + pr.offsetHeight / 2;
                const distance = Math.abs(wrapperCenterY - viewCenterY);
                if (distance < minDistance) {
                    minDistance = distance;
                    bestPage = pageNum;
                }
            }
            
            if (bestPage !== currentPage && bestPage >= 1 && bestPage <= totalPages) {
                currentPage = bestPage;
                const pageCurrent = document.getElementById('page-current');
                const btnPrev = document.getElementById('btn-prev');
                const btnNext = document.getElementById('btn-next');
                if (pageCurrent) {
                    if (pageCurrent.tagName === 'INPUT') {
                        if (document.activeElement !== pageCurrent) {
                            pageCurrent.value = currentPage;
                        }
                    } else {
                        pageCurrent.textContent = currentPage;
                    }
                }
                if (btnPrev) btnPrev.disabled = currentPage <= 1;
                if (btnNext) btnNext.disabled = currentPage >= totalPages;
            }
        }
        
        updateCustomScrollbar();
    }

    // --- Custom Scrollbar Logic ---
    const customScrollbar = document.getElementById('custom-scrollbar');
    const customScrollbarThumb = document.getElementById('custom-scrollbar-thumb');
    let isDraggingScrollbar = false;
    let scrollbarDragStartY = 0;
    let scrollbarDragStartTranslateY = 0;

    function updateCustomScrollbar() {
        if (!customScrollbar || !customScrollbarThumb) return;
        
        // Only show scrollbar in continuous mode when content is taller than viewport
        if (layoutMode !== 'continuous') {
            customScrollbar.style.display = 'none';
            return;
        }

        const viewerHeight = viewerContainer.clientHeight;
        const contentHeight = panZoomContainer.getBoundingClientRect().height / scale; // unscaled height
        const scaledContentHeight = contentHeight * scale;

        if (scaledContentHeight <= viewerHeight) {
            customScrollbar.style.display = 'none';
            return;
        }

        customScrollbar.style.display = 'block';

        // Calculate thumb size (min 30px)
        const visibleRatio = viewerHeight / scaledContentHeight;
        let thumbHeight = Math.max(30, viewerHeight * visibleRatio);
        customScrollbarThumb.style.height = `${thumbHeight}px`;

        // Calculate thumb position
        const maxTranslateY = 0;
        const minTranslateY = viewerHeight - scaledContentHeight;
        
        let progress = 0;
        if (maxTranslateY !== minTranslateY) {
            progress = (translateY - maxTranslateY) / (minTranslateY - maxTranslateY);
        }
        
        // Clamp progress
        progress = Math.max(0, Math.min(1, progress));
        
        const maxThumbY = viewerHeight - 10 - thumbHeight; // 10px padding total
        customScrollbarThumb.style.transform = `translateY(${progress * maxThumbY}px)`;
    }

    if (customScrollbarThumb && customScrollbar) {
        customScrollbarThumb.addEventListener('mousedown', (e) => {
            if (layoutMode !== 'continuous') return;
            e.preventDefault();
            e.stopPropagation(); // prevent panning on viewer
            isDraggingScrollbar = true;
            customScrollbarThumb.classList.add('active');
            scrollbarDragStartY = e.clientY;
            scrollbarDragStartTranslateY = translateY;
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDraggingScrollbar) return;
            e.preventDefault();
            
            const viewerHeight = viewerContainer.clientHeight;
            const contentHeight = panZoomContainer.getBoundingClientRect().height / scale;
            const scaledContentHeight = contentHeight * scale;
            
            const thumbHeight = parseFloat(customScrollbarThumb.style.height);
            const maxThumbY = viewerHeight - 10 - thumbHeight;
            
            const minTranslateY = viewerHeight - scaledContentHeight;
            const maxTranslateY = 0;
            
            const deltaY = e.clientY - scrollbarDragStartY;
            const progressDelta = deltaY / maxThumbY;
            
            let currentProgress = (scrollbarDragStartTranslateY - maxTranslateY) / (minTranslateY - maxTranslateY);
            let newProgress = currentProgress + progressDelta;
            newProgress = Math.max(0, Math.min(1, newProgress));
            
            translateY = maxTranslateY + newProgress * (minTranslateY - maxTranslateY);
            updateTransform();
        });

        window.addEventListener('mouseup', () => {
            if (isDraggingScrollbar) {
                isDraggingScrollbar = false;
                customScrollbarThumb.classList.remove('active');
                
                // Trigger high-res crop update after scroll ends
                clearTimeout(zoomEndTimer);
                zoomEndTimer = setTimeout(updateImageResolutions, 200);
            }
        });
        
        // Also allow clicking the track to jump
        customScrollbar.addEventListener('mousedown', (e) => {
            if (e.target === customScrollbarThumb || layoutMode !== 'continuous') return;
            
            const viewerHeight = viewerContainer.clientHeight;
            const contentHeight = panZoomContainer.getBoundingClientRect().height / scale;
            const scaledContentHeight = contentHeight * scale;
            
            const thumbHeight = parseFloat(customScrollbarThumb.style.height);
            const maxThumbY = viewerHeight - 10 - thumbHeight;
            const minTranslateY = viewerHeight - scaledContentHeight;
            const maxTranslateY = 0;
            
            const rect = customScrollbar.getBoundingClientRect();
            const clickY = e.clientY - rect.top;
            
            let targetProgress = (clickY - thumbHeight/2) / maxThumbY;
            targetProgress = Math.max(0, Math.min(1, targetProgress));
            
            translateY = maxTranslateY + targetProgress * (minTranslateY - maxTranslateY);
            updateTransform();
            
            isDraggingScrollbar = true;
            customScrollbarThumb.classList.add('active');
            scrollbarDragStartY = e.clientY;
            scrollbarDragStartTranslateY = translateY;
        });
    }

    function resetTransform(fitToWidth = false) {
        const currentWrapper = document.getElementById(`page-wrapper-${currentPage}`) || panZoomContainer.querySelector('.page-wrapper');
        if (!currentWrapper) return;
        
        const pageW = parseFloat(currentWrapper.style.width);
        const pageH = parseFloat(currentWrapper.style.height);
        
        if (pageW > 0 && pageH > 0) {
            const viewerRect = viewerContainer.getBoundingClientRect();
            
            if (fitToWidth) {
                // Fit to width with some padding
                const scaleFit = (viewerRect.width - 40) / pageW;
                if (scaleFit > 0) scale = scaleFit;
                
                translateX = (viewerRect.width - pageW * scale) / 2 - currentWrapper.offsetLeft * scale;
                translateY = 20 - currentWrapper.offsetTop * scale; // Pin to top
            } else {
                // Fit whole page to container
                const scaleFit = Math.min(
                    (viewerRect.width - 40) / pageW,
                    (viewerRect.height - 40) / pageH
                );
                if (scaleFit > 0) scale = scaleFit;
                
                translateX = (viewerRect.width - pageW * scale) / 2 - currentWrapper.offsetLeft * scale;
                translateY = (viewerRect.height - pageH * scale) / 2 - currentWrapper.offsetTop * scale;
            }
        }
        
        updateTransform();
    }

    let zoomEndTimer = null;

    function zoom(factor, cx, cy) {
        const newScale = Math.max(0.05, Math.min(scale * factor, 40));
        if (newScale === scale) return;
        
        translateX = cx - (cx - translateX) * (newScale / scale);
        translateY = cy - (cy - translateY) * (newScale / scale);
        scale = newScale;
        
        updateTransform();
        
        clearTimeout(zoomEndTimer);
        zoomEndTimer = setTimeout(updateImageResolutions, 200);
    }

    function getItemBoundingBox(item) {
        let minX, maxX, minY, maxY;
        if (item.type === 'Line') {
            minX = Math.min(item.start[0], item.end[0]);
            maxX = Math.max(item.start[0], item.end[0]);
            minY = Math.min(item.start[1], item.end[1]);
            maxY = Math.max(item.start[1], item.end[1]);
        } else if (item.type === 'Rect') {
            minX = Math.min(item.x, item.x + item.width);
            maxX = Math.max(item.x, item.x + item.width);
            minY = Math.min(item.y, item.y + item.height);
            maxY = Math.max(item.y, item.y + item.height);
        } else if (item.type === 'Arc/Curve' || item.type === 'Polygon') {
            const xs = item.points.map(p => p[0]);
            const ys = item.points.map(p => p[1]);
            minX = Math.min(...xs);
            maxX = Math.max(...xs);
            minY = Math.min(...ys);
            maxY = Math.max(...ys);
        } else {
            return null;
        }
        return { minX, maxX, minY, maxY, width: maxX - minX, height: maxY - minY };
    }

    function zoomToItem(item) {
        const bounds = getItemBoundingBox(item);
        if (!bounds) return;
        
        const wrapper = document.getElementById(`page-wrapper-${item.page}`);
        if (!wrapper) return;
        
        // Element center in page space
        const centerX = bounds.minX + bounds.width / 2;
        const centerY = bounds.minY + bounds.height / 2;
        
        // Element center in container space
        const elementCenterXInContainer = wrapper.offsetLeft + centerX;
        const elementCenterYInContainer = wrapper.offsetTop + centerY;
        
        const viewerRect = viewerContainer.getBoundingClientRect();
        
        // Calculate target scale to fit the element nicely
        let targetScale = Math.min(
            (viewerRect.width * 0.6) / Math.max(bounds.width, 20),
            (viewerRect.height * 0.6) / Math.max(bounds.height, 20)
        );
        targetScale = Math.max(1.5, Math.min(targetScale, 8.0));
        
        // Set transition class
        panZoomContainer.classList.add('smooth-transition');
        
        scale = targetScale;
        translateX = viewerRect.width / 2 - elementCenterXInContainer * scale;
        translateY = viewerRect.height / 2 - elementCenterYInContainer * scale;
        
        updateTransform();
        
        clearTimeout(zoomEndTimer);
        zoomEndTimer = setTimeout(() => {
            panZoomContainer.classList.remove('smooth-transition');
            updateImageResolutions();
        }, 400);
    }

    const activeTileFetches = new Map(); // Track ongoing image fetches

    function updateImageResolutions() {
        const dpr = window.devicePixelRatio || 1;
        const reqScale = scale * dpr;
        
        // Ensure vector tiles are at least scale 2, images cap at 48
        const fetchScale = Math.min(Math.max(2, Math.ceil(reqScale)), 48);
        const viewerRect = viewerContainer.getBoundingClientRect();
        
        // TILE_SIZE is the number of pixels the server renders per tile.
        // unscaledTileSize is how big that tile is in PDF-point coordinates.
        const TILE_SIZE = 512;
        const unscaledTileSize = TILE_SIZE / fetchScale;
        // counterScale converts from pixel space back to PDF-point space
        const counterScale = 1 / fetchScale;

        document.querySelectorAll('.page-wrapper').forEach(wrapper => {
            const pageNum = wrapper.dataset.page;
            const pageRect = wrapper.getBoundingClientRect();

            const intersectLeft = Math.max(viewerRect.left, pageRect.left);
            const intersectTop = Math.max(viewerRect.top, pageRect.top);
            const intersectRight = Math.min(viewerRect.right, pageRect.right);
            const intersectBottom = Math.min(viewerRect.bottom, pageRect.bottom);

            const intersectWidth = intersectRight - intersectLeft;
            const intersectHeight = intersectBottom - intersectTop;

            if (intersectWidth <= 0 || intersectHeight <= 0) {
                wrapper.querySelectorAll('.pdf-tile').forEach(t => t.remove());
                wrapper.querySelectorAll('.vector-tile').forEach(t => t.remove());
                return;
            }

            let cx0 = (intersectLeft - pageRect.left) / scale;
            let cy0 = (intersectTop - pageRect.top) / scale;
            let cx1 = cx0 + (intersectWidth / scale);
            let cy1 = cy0 + (intersectHeight / scale);

            const padding = unscaledTileSize * 0.5;
            cx0 = Math.max(0, cx0 - padding);
            cy0 = Math.max(0, cy0 - padding);
            
            const maxW = parseFloat(wrapper.style.width);
            const maxH = parseFloat(wrapper.style.height);
            
            cx1 = Math.min(maxW, cx1 + padding);
            cy1 = Math.min(maxH, cy1 + padding);

            const startCol = Math.floor(cx0 / unscaledTileSize);
            const startRow = Math.floor(cy0 / unscaledTileSize);
            const endCol = Math.floor(cx1 / unscaledTileSize);
            const endRow = Math.floor(cy1 / unscaledTileSize);

            // Always update Vector Tiles if in Canvas Mode
            if (showVectors && currentRendererSetting === 'canvas') {
                const renderer = canvasRenderers.get(parseInt(pageNum));
                if (renderer) {
                    renderer.updateVectorTiles(fetchScale, startCol, endCol, startRow, endRow, unscaledTileSize, maxW, maxH);
                }
            }

            // If we are at a low zoom, we don't need PDF image tiles.
            if (reqScale <= 2.5) {
                wrapper.querySelectorAll('.pdf-tile').forEach(t => t.remove());
                return;
            }

            wrapper.dataset.currentFetchScale = fetchScale;

            // Cancel any in-flight fetches for old zoom levels
            for (const [key, img] of activeTileFetches.entries()) {
                const parts = key.split('_');
                const tPage = parts[0];
                const tScale = parseInt(parts[1]);
                if (tPage === pageNum && tScale !== fetchScale) {
                    img.src = '';
                    activeTileFetches.delete(key);
                }
            }

            const activeTileKeys = new Set();

            for (let row = startRow; row <= endRow; row++) {
                for (let col = startCol; col <= endCol; col++) {
                    const tileX = col * unscaledTileSize;
                    const tileY = row * unscaledTileSize;
                    const tileW = Math.min(unscaledTileSize, maxW - tileX);
                    const tileH = Math.min(unscaledTileSize, maxH - tileY);

                    if (tileW <= 0 || tileH <= 0) continue;

                    const tileKey = `${pageNum}_${fetchScale}_${col}_${row}`;
                    activeTileKeys.add(tileKey);

                    if (wrapper.querySelector(`.pdf-tile[data-tile-key="${tileKey}"]`)) {
                        continue;
                    }

                    const encPath = encodeURIComponent(currentPdf);
                    const clipParam = `${tileX},${tileY},${tileW},${tileH}`;
                    
                    // The server returns an image of (tileW*fetchScale) x (tileH*fetchScale) pixels.
                    // We set the CSS dimensions to those NATIVE pixel dimensions so Chrome
                    // rasterizes the full resolution. Then we use CSS transform: scale(counterScale)
                    // to shrink it back down to fit the unscaled coordinate system.
                    // When the parent panZoomContainer applies scale(zoom), the two scales
                    // combine to produce the correct on-screen size at full resolution.
                    const nativeW = tileW * fetchScale;
                    const nativeH = tileH * fetchScale;
                    
                    const tempImg = new Image();
                    activeTileFetches.set(tileKey, tempImg);

                    tempImg.className = 'pdf-tile';
                    tempImg.dataset.tileKey = tileKey;
                    tempImg.dataset.fetchScale = fetchScale;
                    tempImg.style.left = `${tileX}px`;
                    tempImg.style.top = `${tileY}px`;
                    tempImg.style.width = `${nativeW}px`;
                    tempImg.style.height = `${nativeH}px`;
                    tempImg.style.transformOrigin = '0 0';
                    tempImg.style.transform = `scale(${counterScale})`;
                    
                    tempImg.src = `/api/pdf/${encPath}/page/${pageNum}/image?scale=${fetchScale}&clip=${clipParam}&t=${pdfCacheBuster}`;
                    
                    tempImg.onload = () => {
                        activeTileFetches.delete(tileKey);
                        if (parseInt(wrapper.dataset.currentFetchScale) !== fetchScale) {
                            return;
                        }
                        
                        const overlay = wrapper.querySelector('.vector-overlay');
                        if (overlay) {
                            wrapper.insertBefore(tempImg, overlay);
                        } else {
                            wrapper.appendChild(tempImg);
                        }
                        
                        setTimeout(() => tempImg.classList.add('loaded'), 10);
                    };

                    tempImg.onerror = () => {
                        activeTileFetches.delete(tileKey);
                    };
                }
            }

            // Prune off-screen tiles
            wrapper.querySelectorAll('.pdf-tile').forEach(t => {
                const tx = parseFloat(t.style.left);
                const ty = parseFloat(t.style.top);
                // Use unscaled tile dimensions for bounds checking
                const tScale = parseInt(t.dataset.fetchScale) || fetchScale;
                const tw = parseFloat(t.style.width) / tScale;
                const th = parseFloat(t.style.height) / tScale;
                
                if (tx + tw < cx0 || tx > cx1 || ty + th < cy0 || ty > cy1) {
                    t.remove(); 
                }
            });
        });
    }


    // Double wheel click (middle click) handles Reset Zoom / Fit below in mousedown

    // Zoom Controls
    btnZoomIn.addEventListener('click', () => {
        const rect = viewerContainer.getBoundingClientRect();
        zoom(1.2, rect.width/2, rect.height/2);
    });
    btnZoomOut.addEventListener('click', () => {
        const rect = viewerContainer.getBoundingClientRect();
        zoom(1/1.2, rect.width/2, rect.height/2);
    });
    btnZoomReset.addEventListener('click', () => resetTransform(false));
    
    // Lightweight single-page switcher — shows target page, hides others, no canvas teardown
    async function showSinglePage(pageNum, scrollEdge = null) {
        if (pageNum < 1 || pageNum > totalPages) return;
        const currentRenderId = renderId;

        // Show the target wrapper, hide all others
        const allWrappers = panZoomContainer.querySelectorAll('.page-wrapper');
        allWrappers.forEach(w => {
            w.style.display = parseInt(w.dataset.page) === pageNum ? '' : 'none';
        });

        // If the page wrapper doesn't exist yet, create and load it
        let wrapper = panZoomContainer.querySelector(`.page-wrapper[data-page="${pageNum}"]`);
        if (!wrapper) {
            wrapper = createPagePlaceholder(pageNum, 800, 1100, currentRenderId);
            panZoomContainer.appendChild(wrapper);
            invalidatePageRects();
            await loadPageContent(wrapper, pageNum, currentRenderId);
        } else if (!wrapper.dataset.loaded) {
            // Placeholder exists but not loaded yet
            wrapper.dataset.loaded = 'true';
            await loadPageContent(wrapper, pageNum, currentRenderId);
        }

        updatePageDisplay(pageNum);
        btnPrev.disabled = pageNum <= 1;
        btnNext.disabled = pageNum >= totalPages;
        updateCustomScrollbar();

        if (scrollEdge) {
            // Wait a tick for the new wrapper to establish its dimensions
            requestAnimationFrame(() => {
                const vh = viewerContainer.clientHeight;
                const ch = panZoomContainer.offsetHeight * scale;
                const margin = 20;

                const minTranslateY = ch <= vh ? (vh - ch) / 2 : vh - ch - margin;
                const maxTranslateY = ch <= vh ? (vh - ch) / 2 : margin;

                if (scrollEdge === 'top') {
                    translateY = maxTranslateY;
                } else if (scrollEdge === 'bottom') {
                    translateY = minTranslateY;
                }
                // 'keep' does not modify translateY
                updateTransform();
            });
        } else {
            resetTransform(true);
        }
    }

    // Pagination Controls
    btnPrev.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            if (layoutMode === 'single') {
                showSinglePage(currentPage);
            } else {
                scrollToPage(currentPage);
            }
        }
    });
    btnNext.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            if (layoutMode === 'single') {
                showSinglePage(currentPage);
            } else {
                scrollToPage(currentPage);
            }
        }
    });

    function navigateToPage(pageNum) {
        if (pageNum < 1 || pageNum > totalPages) return;
        currentPage = pageNum;
        if (layoutMode === 'single') {
            showSinglePage(currentPage);
        } else {
            scrollToPage(currentPage);
        }
    }

    if (pageCurrent && pageCurrent.tagName === 'INPUT') {
        pageCurrent.addEventListener('change', () => {
            let val = parseInt(pageCurrent.value);
            if (isNaN(val) || val < 1) {
                pageCurrent.value = currentPage;
                return;
            }
            if (val > totalPages) val = totalPages;
            navigateToPage(val);
        });
        pageCurrent.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                pageCurrent.blur();
            }
        });
    }

    // Temporary Debug Links Button
    const btnTempColorLinks = document.getElementById('btn-temp-color-links');
    if (btnTempColorLinks) {
        btnTempColorLinks.addEventListener('click', () => {
            viewerContainer.classList.toggle('debug-links');
            if (viewerContainer.classList.contains('debug-links')) {
                btnTempColorLinks.style.background = '#0056b3'; // Darker active state
                btnTempColorLinks.textContent = 'Hide Link Zones';
            } else {
                btnTempColorLinks.style.background = 'var(--accent)';
                btnTempColorLinks.textContent = 'Debug Links';
            }
        });
    }

    function scrollToPage(pageNum) {
        const wrapper = document.getElementById(`page-wrapper-${pageNum}`);
        if (wrapper) {
            // Find its Y offset relative to panZoomContainer
            const offsetTop = wrapper.offsetTop;
            
            // Move container up so wrapper is at the top margin (20px)
            translateY = 20 - offsetTop * scale;
            updateTransform();
            
            // Update UI
            updatePageDisplay(pageNum);
            btnPrev.disabled = pageNum <= 1;
            btnNext.disabled = pageNum >= totalPages;
        }
    }

    // Auto-Scroll Navigator State
    let isAutoScrolling = false;
    let autoScrollOrigin = { x: 0, y: 0 };
    let currentMousePos = { x: 0, y: 0 };
    const navigatorEl = document.getElementById('auto-scroll-navigator');

    function startAutoScroll(x, y) {
        isAutoScrolling = true;
        autoScrollOrigin = { x, y };
        currentMousePos = { x, y };
        navigatorEl.style.left = `${x}px`;
        navigatorEl.style.top = `${y}px`;
        navigatorEl.style.display = 'flex';
        requestAnimationFrame(autoScrollLoop);
    }

    function stopAutoScroll() {
        isAutoScrolling = false;
        navigatorEl.style.display = 'none';
        clearTimeout(zoomEndTimer);
        zoomEndTimer = setTimeout(() => updateImageResolutions(), 300);
    }

    function autoScrollLoop() {
        if (!isAutoScrolling) return;
        
        const dx = currentMousePos.x - autoScrollOrigin.x;
        const dy = currentMousePos.y - autoScrollOrigin.y;
        
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist > 15) { // Deadzone radius
            const speedMultiplier = window.APP_CONFIG ? window.APP_CONFIG.auto_scroll_speed : 0.05;
            const rate = (dist - 15) * speedMultiplier;
            translateX -= (dx / dist) * rate;
            translateY -= (dy / dist) * rate;
            updateTransform();
        }
        
        requestAnimationFrame(autoScrollLoop);
    }

    // --- Touch Screen Gestures ---
    
    // Helper to calculate distance between two touches
    function getTouchDist(t1, t2) {
        return Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
    }
    
    // Helper to calculate midpoint of two touches
    function getTouchMid(t1, t2) {
        return {
            x: (t1.clientX + t2.clientX) / 2,
            y: (t1.clientY + t2.clientY) / 2
        };
    }

    // Start touch inertia animation
    function startTouchInertia() {
        if (touchInertiaFrameId) {
            cancelAnimationFrame(touchInertiaFrameId);
        }
        
        let lastFrameTime = Date.now();
        const friction = 0.95;
        
        function stepInertia() {
            const now = Date.now();
            const dt = now - lastFrameTime;
            lastFrameTime = now;
            
            // Limit dt to avoid massive jumps (e.g. if the tab is inactive)
            if (dt > 100) {
                touchInertiaFrameId = null;
                clearTimeout(zoomEndTimer);
                zoomEndTimer = setTimeout(updateImageResolutions, 200);
                return;
            }
            
            // Decay velocity exponentially based on dt in milliseconds
            const frictionFactor = Math.pow(friction, dt / 16.67);
            touchVelocityX *= frictionFactor;
            touchVelocityY *= frictionFactor;
            
            const speed = Math.hypot(touchVelocityX, touchVelocityY);
            if (speed < 0.03) {
                touchInertiaFrameId = null;
                clearTimeout(zoomEndTimer);
                zoomEndTimer = setTimeout(updateImageResolutions, 200);
                return;
            }
            
            translateX += touchVelocityX * dt;
            translateY += touchVelocityY * dt;
            
            updateTransform();
            
            touchInertiaFrameId = requestAnimationFrame(stepInertia);
        }
        
        touchInertiaFrameId = requestAnimationFrame(stepInertia);
    }
    
    viewerContainer.addEventListener('touchstart', (e) => {
        if (isAutoScrolling) {
            stopAutoScroll();
        }
        
        // Stop any active touch inertia animation immediately on touch start
        if (touchInertiaFrameId) {
            cancelAnimationFrame(touchInertiaFrameId);
            touchInertiaFrameId = null;
        }
        
        const now = Date.now();
        
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            const distSinceLastTouch = Math.hypot(touch.clientX - lastTouchX, touch.clientY - lastTouchY);
            
            // Check for double tap (within 300ms, and within 30px distance)
            if (now - lastTouchTime < 300 && distSinceLastTouch < 30) {
                isDoubleTapLasso = true;
            } else {
                isDoubleTapLasso = false;
            }
            
            lastTouchTime = now;
            lastTouchX = touch.clientX;
            lastTouchY = touch.clientY;
            
            // Track start position for inertia
            touchLastMoveTime = now;
            touchLastMoveX = touch.clientX;
            touchLastMoveY = touch.clientY;
            touchVelocityX = 0;
            touchVelocityY = 0;
            
            if (selectionMode) {
                if (isDoubleTapLasso) {
                    // Double tap & drag = lasso selection
                    startLasso(touch);
                } else {
                    // In selection mode, single finger touch can toggle items on tap (handled on touchend)
                    isTouchPanning = false;
                }
            } else {
                // In normal mode, single finger touch is panning
                isTouchPanning = true;
                startPanX = touch.clientX - translateX;
                startPanY = touch.clientY - translateY;
            }
            isTouchZooming = false;
        } else if (e.touches.length === 2) {
            // Cancel any single finger action (panning or lasso)
            if (isLassoing) {
                isLassoing = false;
                selectionLasso.style.display = 'none';
            }
            isDoubleTapLasso = false;
            isTouchPanning = false;
            isTouchZooming = true;
            
            // Initial distance and midpoint
            const t1 = e.touches[0];
            const t2 = e.touches[1];
            touchStartDist = getTouchDist(t1, t2);
            const mid = getTouchMid(t1, t2);
            touchStartMidX = mid.x;
            touchStartMidY = mid.y;
            
            touchStartScale = scale;
            touchStartTranslateX = translateX;
            touchStartTranslateY = translateY;
            
            // Calculate pan starting offset for 2-finger panning
            startPanX = touchStartMidX - translateX;
            startPanY = touchStartMidY - translateY;
        }
        
        // Prevent default viewport behavior (e.g. bounce, scroll)
        if (e.cancelable) e.preventDefault();
    }, { passive: false });
    
    viewerContainer.addEventListener('touchmove', (e) => {
        const now = Date.now();
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            if (selectionMode) {
                if (isDoubleTapLasso && isLassoing) {
                    updateLasso(touch);
                }
            } else if (isTouchPanning) {
                translateX = touch.clientX - startPanX;
                translateY = touch.clientY - startPanY;
                updateTransform();
                
                // Track velocity
                const dt = now - touchLastMoveTime;
                if (dt > 0) {
                    const dx = touch.clientX - touchLastMoveX;
                    const dy = touch.clientY - touchLastMoveY;
                    const instVx = dx / dt;
                    const instVy = dy / dt;
                    // Exponential smoothing for velocity
                    touchVelocityX = touchVelocityX * 0.6 + instVx * 0.4;
                    touchVelocityY = touchVelocityY * 0.6 + instVy * 0.4;
                }
                touchLastMoveTime = now;
                touchLastMoveX = touch.clientX;
                touchLastMoveY = touch.clientY;
            }
        } else if (e.touches.length === 2 && isTouchZooming) {
            const t1 = e.touches[0];
            const t2 = e.touches[1];
            
            const currentDist = getTouchDist(t1, t2);
            const mid = getTouchMid(t1, t2);
            
            // Compute zoom factor
            let factor = 1.0;
            if (touchStartDist > 0) {
                factor = currentDist / touchStartDist;
            }
            
            // Constraints on scale (from 0.05 to 40.0)
            const targetScale = Math.max(0.05, Math.min(touchStartScale * factor, 40));
            
            // Center the zoom on the midpoint of the two fingers while panning
            const rect = viewerContainer.getBoundingClientRect();
            const cx = touchStartMidX - rect.left;
            const cy = touchStartMidY - rect.top;
            
            const deltaX = mid.x - touchStartMidX;
            const deltaY = mid.y - touchStartMidY;
            
            scale = targetScale;
            translateX = touchStartTranslateX * (targetScale / touchStartScale) + cx * (1 - targetScale / touchStartScale) + deltaX;
            translateY = touchStartTranslateY * (targetScale / touchStartScale) + cy * (1 - targetScale / touchStartScale) + deltaY;
            
            updateTransform();
        }
        
        if (e.cancelable) e.preventDefault();
    }, { passive: false });
    
    viewerContainer.addEventListener('touchend', (e) => {
        const now = Date.now();
        
        if (isLassoing && isDoubleTapLasso) {
            // Retrieve ending touch position
            const touch = e.changedTouches[0];
            finishLasso(touch);
            isDoubleTapLasso = false;
        } else if (!isTouchZooming && !isDoubleTapLasso) {
            // Handle single tap click on hyperlink / stamp
            const touch = e.changedTouches[0];
            const duration = now - lastTouchTime;
            const moveDist = Math.hypot(touch.clientX - lastTouchX, touch.clientY - lastTouchY);
            
            if (duration < 300 && moveDist < 10) {
                // Find element under touch point
                const targetEl = document.elementFromPoint(touch.clientX, touch.clientY);
                if (targetEl) {
                    // Check if they tapped a hyperlink zone
                    const linkZone = targetEl.closest('.pdf-link-zone');
                    if (linkZone) {
                        linkZone.dispatchEvent(new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        }));
                    } else {
                        // Check if they tapped a stamp highlight
                        const stampHighlight = targetEl.closest('.stamp-highlight-rect');
                        if (stampHighlight) {
                            stampHighlight.dispatchEvent(new MouseEvent('click', {
                                bubbles: true,
                                cancelable: true,
                                view: window
                            }));
                        } else {
                            // Check if they tapped a pattern highlight
                            const patternHighlight = targetEl.closest('.pattern-highlight-rect');
                            if (patternHighlight) {
                                patternHighlight.dispatchEvent(new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                }));
                            } else if (selectionMode) {
                                if (currentRendererSetting === 'canvas') {
                                    // Hybrid Canvas Mode selection lookup
                                    const containerRect = panZoomContainer.getBoundingClientRect();
                                    const touchX = (touch.clientX - containerRect.left) / scale;
                                    const touchY = (touch.clientY - containerRect.top) / scale;
                                    
                                    const pageRects = getPageRects();
                                    let tappedWrapper = null;
                                    let relativeX = 0;
                                    let relativeY = 0;
                                    
                                    for (const pr of pageRects) {
                                        if (
                                            touchX >= pr.offsetLeft && touchX <= pr.offsetLeft + pr.offsetWidth &&
                                            touchY >= pr.offsetTop && touchY <= pr.offsetTop + pr.offsetHeight
                                        ) {
                                            tappedWrapper = pr.wrapper;
                                            relativeX = touchX - pr.offsetLeft;
                                            relativeY = touchY - pr.offsetTop;
                                            break;
                                        }
                                    }
                                    
                                    if (tappedWrapper) {
                                        const pageNum = parseInt(tappedWrapper.dataset.page);
                                        const renderer = canvasRenderers.get(pageNum);
                                        if (renderer) {
                                            const matchedCandidate = renderer.queryPoint(relativeX, relativeY, 8); // 8px touch radius
                                            if (matchedCandidate) {
                                                handleVectorMousedown(e, matchedCandidate, null);
                                            }
                                        }
                                    }
                                } else {
                                    // Fallback to vector item selection in selection mode
                                    let hitTarget = targetEl.closest('.vector-item-hit-target');
                                    if (!hitTarget && targetEl.classList.contains('vector-item')) {
                                        hitTarget = targetEl.previousElementSibling;
                                    }
                                    if (hitTarget && hitTarget.classList.contains('vector-item-hit-target')) {
                                        const itemData = hitTarget._itemData;
                                        const el = hitTarget.nextElementSibling;
                                        handleVectorMousedown(e, itemData, el);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        if (isTouchPanning || isTouchZooming) {
            const wasPanning = isTouchPanning;
            isTouchPanning = false;
            isTouchZooming = false;
            
            if (wasPanning) {
                // If user held finger still before lifting, reset velocity
                if (now - touchLastMoveTime > 80) {
                    touchVelocityX = 0;
                    touchVelocityY = 0;
                }
                const speed = Math.hypot(touchVelocityX, touchVelocityY);
                if (speed > 0.05) {
                    startTouchInertia();
                } else {
                    clearTimeout(zoomEndTimer);
                    zoomEndTimer = setTimeout(updateImageResolutions, 200);
                }
            } else {
                clearTimeout(zoomEndTimer);
                zoomEndTimer = setTimeout(updateImageResolutions, 200);
            }
        }
        
        if (e.cancelable) e.preventDefault();
    }, { passive: false });
    
    viewerContainer.addEventListener('touchcancel', (e) => {
        isTouchPanning = false;
        isTouchZooming = false;
        isDoubleTapLasso = false;
        if (isLassoing) {
            isLassoing = false;
            selectionLasso.style.display = 'none';
        }
    });

    // Mouse Wheel Zoom & Pan
    // Single-page scroll: track when we're "at the edge" and flip pages
    let singlePageScrollEdgeDir = 0; // -1 = at top, 1 = at bottom, 0 = not at edge
    let singlePageScrollEdgeAccum = 0; // accumulated delta while at edge
    const SINGLE_PAGE_FLIP_THRESHOLD = 120; // px of accumulated scroll needed to flip

    viewerContainer.addEventListener('wheel', (e) => {
        if (isAutoScrolling) {
            stopAutoScroll();
            return;
        }
        e.preventDefault();

        if (e.ctrlKey || e.metaKey) {
            // Zooming — same as before
            const rect = viewerContainer.getBoundingClientRect();
            const cx = e.clientX - rect.left;
            const cy = e.clientY - rect.top;
            const factor = e.deltaY < 0 ? 1.1 : 1/1.1;
            zoom(factor, cx, cy);
            return;
        }

        if (e.shiftKey) {
            // Horizontal scroll with Shift+Wheel
            translateX -= e.deltaY;
            updateTransform();
            return;
        }

        // --- Single-page mode: flip pages when scrolling past boundary ---
        if (layoutMode === 'single' && !e.shiftKey) {
            const vh = viewerContainer.clientHeight;
            const ch = panZoomContainer.offsetHeight * scale;
            const margin = 20;

            const minTranslateY = ch <= vh ? (vh - ch) / 2 : vh - ch - margin;
            const maxTranslateY = ch <= vh ? (vh - ch) / 2 : margin;

            const atBottom = translateY <= minTranslateY + 2;
            const atTop    = translateY >= maxTranslateY - 2;

            const scrollingDown = e.deltaY > 0;
            const scrollingUp   = e.deltaY < 0;

            if (scrollingDown && atBottom && currentPage < totalPages) {
                singlePageScrollEdgeAccum += Math.abs(e.deltaY);
                if (singlePageScrollEdgeAccum >= SINGLE_PAGE_FLIP_THRESHOLD) {
                    singlePageScrollEdgeAccum = 0;
                    currentPage++;
                    showSinglePage(currentPage, 'top');
                }
                return; // Don't pan further — we're at the edge
            } else if (scrollingUp && atTop && currentPage > 1) {
                singlePageScrollEdgeAccum += Math.abs(e.deltaY);
                if (singlePageScrollEdgeAccum >= SINGLE_PAGE_FLIP_THRESHOLD) {
                    singlePageScrollEdgeAccum = 0;
                    currentPage--;
                    showSinglePage(currentPage, 'bottom');
                }
                return;
            } else {
                // Not at an edge — reset accumulator and pan normally
                singlePageScrollEdgeAccum = 0;
            }
        }

        // Normal pan
        translateX -= e.deltaX;
        translateY -= e.deltaY;
        updateTransform();
    }, { passive: false });

    let middleClickStartX = 0;
    let middleClickStartY = 0;
    let lastMiddleClickTime = 0;

    // Panning & Lasso Selection
    viewerContainer.addEventListener('mousedown', (e) => {
        // Let SVG overlay interactive elements handle their own clicks unobstructed
        if (
            e.target.classList.contains('pdf-link-zone') ||
            e.target.classList.contains('stamp-highlight-rect') ||
            e.target.classList.contains('pattern-highlight-rect')
        ) return;
        
        if (e.button === 1) {
            const now = Date.now();
            if (now - lastMiddleClickTime < 500) {
                if (isAutoScrolling) stopAutoScroll();
                e.preventDefault();
                if (!e.target.classList.contains('vector-item')) {
                    resetTransform(layoutMode === 'continuous'); // Fit to width if continuous
                }
                lastMiddleClickTime = 0;
                return; // Prevent panning start on double click
            }
            lastMiddleClickTime = now;
        }

        if (isAutoScrolling) {
            stopAutoScroll();
            return;
        }

        if (e.button === 0 && selectionMode) {
            // Intercept if a Tab candidate is currently previewed
            if (typeof tabCycleCandidates !== 'undefined' && tabCycleCandidates.length > 0 && tabCycleIndex >= 0 && tabCycleIndex < tabCycleCandidates.length) {
                const candidate = tabCycleCandidates[tabCycleIndex];
                const originalType = candidate ? candidate.originalData.type : null;
                if (originalType === 'vector') {
                    if (!e.ctrlKey && !e.shiftKey) {
                        clearSelection();
                    }
                    if (candidate && Array.isArray(candidate.items)) {
                        candidate.items.forEach(node => {
                            if (node) {
                                if (currentRendererSetting === 'canvas') {
                                    // node is raw item data in canvas mode
                                    if (node.globalId) selectedItems.set(node.globalId, node);
                                } else if (node._itemData && node.nextElementSibling) {
                                    selectedItems.set(node._itemData.globalId, node._itemData);
                                    node.nextElementSibling.classList.add('selected');
                                }
                            }
                        });
                    }
                    clearTabState();
                    updateInspector();
                    if (currentRendererSetting === 'canvas') {
                        refreshCanvasHighlights();
                    }
                    return;
                } else if (originalType === 'stamp') {
                    const xref = parseInt(candidate.items[0].dataset.xref);
                    const stamp = currentPdfStamps.find(s => s.xref === xref);
                    if (stamp) selectStamp(stamp);
                    clearTabState();
                    return;
                }
            }

            // Canvas Mode Vector Selection Click Hit-Testing
            if (currentRendererSetting === 'canvas') {
                const containerRect = panZoomContainer.getBoundingClientRect();
                const mouseX = (e.clientX - containerRect.left) / scale;
                const mouseY = (e.clientY - containerRect.top) / scale;
                
                const pageRects = getPageRects();
                let hoveredWrapper = null;
                let relativeX = 0;
                let relativeY = 0;
                
                for (const pr of pageRects) {
                    if (
                        mouseX >= pr.offsetLeft && mouseX <= pr.offsetLeft + pr.offsetWidth &&
                        mouseY >= pr.offsetTop && mouseY <= pr.offsetTop + pr.offsetHeight
                    ) {
                        hoveredWrapper = pr.wrapper;
                        relativeX = mouseX - pr.offsetLeft;
                        relativeY = mouseY - pr.offsetTop;
                        break;
                    }
                }
                
                if (hoveredWrapper) {
                    const pageNum = parseInt(hoveredWrapper.dataset.page);
                    const renderer = canvasRenderers.get(pageNum);
                    if (renderer) {
                        const matchedCandidate = renderer.queryPoint(relativeX, relativeY, 6);
                        if (matchedCandidate) {
                            if (e.stopPropagation) e.stopPropagation();
                            handleVectorMousedown(e, matchedCandidate, null);
                            return;
                        }
                    }
                }
            }

            // Handle event delegation for vector selection clicks
            const hitTarget = e.target.closest('.vector-item-hit-target');
            if (hitTarget) {
                const itemData = hitTarget._itemData;
                const el = hitTarget.nextElementSibling; // The visible vector element
                handleVectorMousedown(e, itemData, el);
                return;
            }

            if (isSpacePressed) {
                // Pan instead of lasso if spacebar is held down
                isPanning = true;
                startPanX = e.clientX - translateX;
                startPanY = e.clientY - translateY;
                viewerContainer.style.cursor = 'grabbing';
                return;
            } else {
                // Default to window selection (lasso) when dragging on empty space
                startLasso(e);
                return;
            }
        }

        if (e.button !== 0 && e.button !== 1) return; // Allow Left or Middle
        if (e.button === 1) {
            e.preventDefault(); // Prevent middle-click auto-scroll natively
            middleClickStartX = e.clientX;
            middleClickStartY = e.clientY;
        }

        isPanning = true;
        startPanX = e.clientX - translateX;
        startPanY = e.clientY - translateY;
        viewerContainer.style.cursor = 'grabbing';
    });

    // Delegated hover logic for hit targets to replace expensive CSS sibling selectors
    viewerContainer.addEventListener('mouseover', (e) => {
        if (!selectionMode || isPanning || isLassoing) return;
        const isTabActive = typeof tabCycleCandidates !== 'undefined' && tabCycleCandidates.length > 0 && tabCycleIndex >= 0;
        if (isTabActive) return;
        const hitTarget = e.target.closest('.vector-item-hit-target');
        if (hitTarget && hitTarget.nextElementSibling) {
            hitTarget.nextElementSibling.classList.add('highlighted');
        }
    });

    viewerContainer.addEventListener('mouseout', (e) => {
        if (!selectionMode || isPanning || isLassoing) return;
        const hitTarget = e.target.closest('.vector-item-hit-target');
        if (hitTarget && hitTarget.nextElementSibling) {
            const el = hitTarget.nextElementSibling;
            const globalId = hitTarget._itemData?.globalId;
            // Only remove highlight if it isn't currently the highlightedItemId (from inspector click)
            if (globalId && globalId !== highlightedItemId) {
                el.classList.remove('highlighted');
            }
        }
    });

    window.addEventListener('mousemove', (e) => {
        lastMouseEvent = e;
        if (showCoordsMode) {
            updateCoordsFromMouseEvent(e);
        }
        if (isAutoScrolling) {
            currentMousePos = { x: e.clientX, y: e.clientY };
            return;
        }
        if (isPanning) {
            translateX = e.clientX - startPanX;
            translateY = e.clientY - startPanY;
            updateTransform();
        } else if (isLassoing) {
            updateLasso(e);
        }
        
        // Canvas hover hit-testing
        if (currentRendererSetting === 'canvas' && selectionMode && !isPanning && !isLassoing) {
            const containerRect = panZoomContainer.getBoundingClientRect();
            const mouseX = (e.clientX - containerRect.left) / scale;
            const mouseY = (e.clientY - containerRect.top) / scale;
            
            const pageRects = getPageRects();
            let hoveredWrapper = null;
            let relativeX = 0;
            let relativeY = 0;
            
            for (const pr of pageRects) {
                if (
                    mouseX >= pr.offsetLeft && mouseX <= pr.offsetLeft + pr.offsetWidth &&
                    mouseY >= pr.offsetTop && mouseY <= pr.offsetTop + pr.offsetHeight
                ) {
                    hoveredWrapper = pr.wrapper;
                    relativeX = mouseX - pr.offsetLeft;
                    relativeY = mouseY - pr.offsetTop;
                    break;
                }
            }
            
            let newHoveredId = null;
            if (hoveredWrapper) {
                const pageNum = parseInt(hoveredWrapper.dataset.page);
                const renderer = canvasRenderers.get(pageNum);
                if (renderer) {
                    const matched = renderer.queryPoint(relativeX, relativeY, 5);
                    if (matched) {
                        newHoveredId = matched.globalId;
                    }
                }
            }
            
            if (newHoveredId !== highlightedItemId) {
                highlightedItemId = newHoveredId;
                refreshCanvasHighlights();
            }
        }
        
        // Override cursor to pointer when hovering interactive SVG overlay elements
        if (!isPanning && !isLassoing) {
            const overInteractive = 
                e.target.classList.contains('pdf-link-zone') ||
                e.target.classList.contains('stamp-highlight-rect') ||
                e.target.classList.contains('pattern-highlight-rect');
            viewerContainer.style.cursor = overInteractive
                ? 'pointer'
                : (selectionMode ? (isSpacePressed ? 'grab' : 'crosshair') : 'grab');
        }
    });

    window.addEventListener('mouseup', (e) => {
        if (isPanning) {
            isPanning = false;
            viewerContainer.style.cursor = selectionMode ? (isSpacePressed ? 'grab' : 'crosshair') : 'grab';
            
            clearTimeout(zoomEndTimer);
            zoomEndTimer = setTimeout(() => updateImageResolutions(), 300);
            
            if (e.button === 1) {
                const dist = Math.hypot(e.clientX - middleClickStartX, e.clientY - middleClickStartY);
                if (dist < 5) {
                    startAutoScroll(e.clientX, e.clientY);
                }
            }
            
            // Trigger high-res crop update after panning ends
            clearTimeout(zoomEndTimer);
            zoomEndTimer = setTimeout(updateImageResolutions, 200);
        } else if (isLassoing) {
            finishLasso(e);
        }
    });

    // Helper: show/hide the split + button based on active add mode
    function updatePatternModeButtons() {
        if (btnAddGrillPlus) {
            btnAddGrillPlus.style.display = (activeAddState && activeAddState.type === 'grill') ? 'inline-flex' : 'none';
        }
        if (btnAddAacPlus) {
            btnAddAacPlus.style.display = (activeAddState && activeAddState.type === 'aac') ? 'inline-flex' : 'none';
        }
        if (btnRunPatterns) {
            // Update Scan Patterns label to reflect context
            const scanLabel = btnRunPatterns.querySelector('span');
            btnRunPatterns.style.display = activeAddState ? 'inline-flex' : 'none';
            if (activeAddState) {
                if (scanLabel) scanLabel.textContent = '\u{1F916}';
                btnRunPatterns.title = 'Save current selection & run pattern scan';
            } else {
                if (scanLabel) scanLabel.textContent = '\u{1F916}';
                btnRunPatterns.title = '';
            }
        }
    }

    // Add Grill / AAC unit Button Actions — now opens dialog immediately
    

    const btnAddGrillDropdownToggle = document.getElementById('btn-add-grill-dropdown-toggle');
    const airOutletDropdownMenu = document.getElementById('air-outlet-dropdown-menu');

    if (btnAddGrillDropdownToggle && airOutletDropdownMenu) {
        btnAddGrillDropdownToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            airOutletDropdownMenu.style.display = airOutletDropdownMenu.style.display === 'flex' ? 'none' : 'flex';
        });

        document.addEventListener('click', (e) => {
            if (!airOutletDropdownMenu.contains(e.target) && e.target !== btnAddGrillDropdownToggle) {
                airOutletDropdownMenu.style.display = 'none';
            }
        });
    }

    document.querySelectorAll('.btn-air-outlet-type').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (!currentPdf) { alert('Please open a PDF first.'); return; }
            if (airOutletDropdownMenu) airOutletDropdownMenu.style.display = 'none';
            
            const typeName = e.target.getAttribute('data-type');
            patternFilter = 'grill';
            isSavingDirectly = false;
            
            // Bypass modal and directly activate add mode
            deactivateAddMode();
            activeAddState = { type: 'grill', name: typeName, editId: null };
            selectionMode = true;
            viewerContainer.classList.add('selection-mode');
            clearSelection();
            toggleSidebarRight(true);
            switchSidebarTab('patterns');
        });
    });

    btnAddGrill.addEventListener('click', () => {
        if (!currentPdf) { alert('Please open a PDF first.'); return; }
        if (airOutletDropdownMenu) airOutletDropdownMenu.style.display = 'none';
        patternFilter = 'grill';
        isSavingDirectly = false;
        openAddItemModal('grill');
    });
    
    const btnAddAacDropdownToggle = document.getElementById('btn-add-aac-dropdown-toggle');
    const systemDropdownMenu = document.getElementById('system-dropdown-menu');

    if (btnAddAacDropdownToggle && systemDropdownMenu) {
        btnAddAacDropdownToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            systemDropdownMenu.style.display = systemDropdownMenu.style.display === 'flex' ? 'none' : 'flex';
        });

        document.addEventListener('click', (e) => {
            if (!systemDropdownMenu.contains(e.target) && e.target !== btnAddAacDropdownToggle) {
                systemDropdownMenu.style.display = 'none';
            }
        });
    }

    document.querySelectorAll('.btn-system-type').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (!currentPdf) { alert('Please open a PDF first.'); return; }
            if (systemDropdownMenu) systemDropdownMenu.style.display = 'none';
            
            const typeName = e.target.getAttribute('data-type');
            patternFilter = 'aac';
            isSavingDirectly = false;
            
            // Bypass modal and directly activate add mode
            deactivateAddMode();
            activeAddState = { type: 'aac', name: typeName, editId: null };
            selectionMode = true;
            viewerContainer.classList.add('selection-mode');
            clearSelection();
            toggleSidebarRight(true);
            switchSidebarTab('patterns');
        });
    });

    btnAddAac.addEventListener('click', () => {
        if (!currentPdf) { alert('Please open a PDF first.'); return; }
        if (systemDropdownMenu) systemDropdownMenu.style.display = 'none';
        patternFilter = 'aac';
        isSavingDirectly = false;
        openAddItemModal('aac');
    });

    if (btnAddPatternPlus) {
        btnAddPatternPlus.addEventListener('click', () => {
            if (!patternFilter) {
                alert("Please select Air Outlet or System from the left panel first.");
                return;
            }
            if (activeAddState && activeAddState.type === patternFilter) {
                deactivateAddMode();
                selectionMode = false;
                viewerContainer.classList.remove('selection-mode');
                clearSelection();
            } else {
                isSavingDirectly = false;
                openAddItemModal(patternFilter);
            }
        });
    }

    // New "+" buttons in the sidebar — saves current selection then opens dialog for another pattern
    const handlePlusButtonClick = async () => {
        if (!activeAddState) return;
        // Save the current selection if any lines are selected
        if (selectedItems.size > 0) {
            await saveCurrentSelectionSilent(activeAddState.type, activeAddState.name, activeAddState.editId);
        }
        // Open dialog for the next pattern of the same type
        const type = patternFilter;
        isSavingDirectly = false;
        openAddItemModal(type);
    };

    if (btnAddGrillPlus) {
        btnAddGrillPlus.addEventListener('click', handlePlusButtonClick);
    }
    if (btnAddAacPlus) {
        btnAddAacPlus.addEventListener('click', handlePlusButtonClick);
    }

    btnSaveSelection.addEventListener('click', async () => {
        if (selectedItems.size === 0) return;
        
        let type, name;
        if (activeAddState) {
            type = activeAddState.type;
            name = activeAddState.name;
        } else {
            isSavingDirectly = true;
            openAddItemModal('grill');
            addItemModalTitle.textContent = 'Save Selection As...';
            return;
        }
        
        await saveCurrentSelection(type, name);
    });

    // Pattern Scanners Event Listeners & Functions
    async function consumeScannerStream(response, labelText) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.trim()) continue;
                const event = JSON.parse(line);
                if (event.type === 'log') {
                    appendScannerLog(event.message);
                    if (event.message) {
                        scannerStatus.textContent = event.message;
                    }
                } else if (event.type === 'error') {
                    throw new Error(event.message || `${labelText} failed`);
                } else if (event.type === 'result') {
                    finalResult = event.data;
                }
            }
        }

        if (buffer.trim()) {
            const event = JSON.parse(buffer);
            if (event.type === 'result') {
                finalResult = event.data;
            } else if (event.type === 'error') {
                throw new Error(event.message || `${labelText} failed`);
            } else if (event.type === 'log') {
                appendScannerLog(event.message);
            }
        }

        return finalResult;
    }

    async function runScanner(endpoint, btnElement, labelText) {
        if (!currentPdf) return;

        btnRunMatching.disabled = true;
        btnRunPatterns.disabled = true;
        if (btnRunStamps) btnRunStamps.disabled = true;
        scannerSpinner.style.display = 'inline-block';
        scannerStatus.textContent = `Running ${labelText}...`;
        scannerStatus.style.color = 'var(--text-secondary)';
        resetScannerLog();
        appendScannerLog(`> Starting ${labelText}`);

        try {
            let data;
            if (endpoint === 'run-patterns') {
                const res = await fetch(`/api/pdf/${encodeURIComponent(currentPdf)}/run-patterns-stream`, {
                    method: 'POST'
                });
                if (!res.ok) {
                    const errorText = await res.text();
                    throw new Error(errorText || 'Execution failed');
                }
                data = await consumeScannerStream(res, labelText);
            } else {
                const res = await fetch(`/api/pdf/${encodeURIComponent(currentPdf)}/${endpoint}`, {
                    method: 'POST'
                });
                const payload = await res.json();
                if (!res.ok) throw new Error(payload.error || 'Execution failed');
                data = payload;
            }

            if (!data) throw new Error('Execution finished without a result.');

            scannerStatus.textContent = 'Scan completed!';
            scannerStatus.style.color = '#10b981'; // Green
            appendScannerLog('> Scan completed successfully');

            if (data.output_file === currentPdf) {
                scannerStatus.textContent = data.message || 'Changes saved to the current PDF.';
                appendScannerLog('> Saved changes into the currently open PDF');
                canUndoPatternScan = true;
                updateUndoButtonState();
                
                // Fetch and display new stamps without full reload
                try {
                    const stampsRes = await fetch(`/api/pdf/${encodeURIComponent(currentPdf)}/stamps`);
                    if (stampsRes.ok) {
                        currentPdfStamps = await stampsRes.json();
                        renderStampsList();
                    }
                    
                    pdfCacheBuster = Date.now();
                    document.querySelectorAll('.page-wrapper').forEach(wrapper => {
                        const pageNum = parseInt(wrapper.dataset.page);
                        const img = wrapper.querySelector('.pdf-image');
                        if (img && wrapper.dataset.loaded === 'true') {
                            img.src = `/api/pdf/${encodeURIComponent(currentPdf)}/page/${pageNum}/image?scale=2&t=${pdfCacheBuster}`;
                            img.dataset.loadedScale = 2;
                        }
                        const hiResImg = wrapper.querySelector('.pdf-image-hires');
                        if (hiResImg) hiResImg.style.display = 'none';
                        
                        const svg = wrapper.querySelector('.vector-overlay');
                        if (svg) {
                            overlayStampRects(pageNum, svg);
                        }
                    });
                } catch (err) {
                    console.error("Error auto-reloading stamps:", err);
                }

                return;
            }

            if (isGeneratedOutputPath(data.output_file)) {
                removeGeneratedFileEntries();
                scannerStatus.textContent = data.message || 'Scan completed.';
                appendScannerLog(`> Generated file saved at ${data.output_file} (not added to file list)`);
                return;
            }
        } catch (e) {
            scannerStatus.textContent = `Error: ${e.message}`;
            scannerStatus.style.color = '#f43f5e'; // Red/Pink error color
            appendScannerLog(`> Error: ${e.message}`);
            console.error(e);
        } finally {
            if (currentPdf) {
                btnRunMatching.disabled = false;
                btnRunPatterns.disabled = false;
                if (btnRunStamps) btnRunStamps.disabled = false;
            }
            scannerSpinner.style.display = 'none';
        }
    }

    async function undoPatternScan() {
        if (!currentPdf || !canUndoPatternScan) return;

        btnRunMatching.disabled = true;
        btnRunPatterns.disabled = true;
        if (btnRunStamps) btnRunStamps.disabled = true;
        if (btnUndoPdf) btnUndoPdf.disabled = true;
        scannerSpinner.style.display = 'inline-block';
        scannerStatus.textContent = 'Undoing last pattern scan...';
        scannerStatus.style.color = 'var(--text-secondary)';
        appendScannerLog('> Undo requested');

        try {
            const res = await fetch(`/api/pdf/${encodeURIComponent(currentPdf)}/undo-pattern-scan`, {
                method: 'POST'
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Undo failed');

            scannerStatus.textContent = data.message || 'Undo completed.';
            scannerStatus.style.color = '#10b981';
            appendScannerLog('> Undo completed and saved to the current PDF');
            canUndoPatternScan = false;
            updateUndoButtonState();
        } catch (e) {
            scannerStatus.textContent = `Error: ${e.message}`;
            scannerStatus.style.color = '#f43f5e';
            appendScannerLog(`> Undo error: ${e.message}`);
            console.error(e);
            updateUndoButtonState();
        } finally {
            if (currentPdf) {
                btnRunMatching.disabled = false;
                btnRunPatterns.disabled = false;
                btnRunStamps.disabled = false;
            }
            updateUndoButtonState();
            scannerSpinner.style.display = 'none';
        }
    }
    
    btnRunMatching.addEventListener('click', () => {
        runScanner('run-matching-lines', btnRunMatching, 'line scan');
    });
    
    btnRunPatterns.addEventListener('click', async () => {
        // If there is an active add state with a selection, auto-save it first
        if (activeAddState && selectedItems.size > 0) {
            await saveCurrentSelectionSilent(activeAddState.type, activeAddState.name, activeAddState.editId);
        } else if (activeAddState) {
            // No lines selected — deactivate add mode and proceed
            deactivateAddMode();
            selectionMode = false;
            viewerContainer.classList.remove('selection-mode');
            clearSelection();
        }
        runScanner('run-patterns', btnRunPatterns, 'pattern scan');
    });

    if (btnUndoPdf) {
        btnUndoPdf.addEventListener('click', () => {
            undoPatternScan();
        });
    }
    
    window.deleteStampsBulk = async function(xrefs) {
        if (!xrefs || xrefs.length === 0) return true;
        
        const url = `/api/pdf/${encodeURIComponent(currentPdf)}/stamps/bulk-delete`;
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ xrefs: xrefs })
        });
        
        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.error || 'Bulk delete failed');
        }
        
        const xrefsSet = new Set(xrefs);
        currentPdfStamps = currentPdfStamps.filter(st => !xrefsSet.has(st.xref));
        xrefs.forEach(xref => selectedStamps.delete(xref));
        
        renderStampsList();
        if (scannerStatus) {
            scannerStatus.textContent = `${xrefs.length} stamp(s) deleted`;
        }
        window.dispatchEvent(new CustomEvent('stamps-deleted', { detail: { xrefs } }));
        if (window.renderStampHighlights) window.renderStampHighlights();
        
        // Let background image handler load the fresh PDF
        if (window.renderPdfPage) {
            window.renderPdfPage(currentPage);
        }
        return true;
    };

    window.deleteStampByXref = async function(xref, confirmFirst = false) {
        const stamp = currentPdfStamps.find(s => s.xref === xref);
        if (!stamp) {
            console.error("Stamp not found to delete:", xref);
            return false;
        }

        if (confirmFirst) {
            if (!confirm(`Delete stamp?\nThis permanently removes it from the PDF.`)) return false;
        }

        try {
            let forceAll = false;
            const useForce = forceAll;
            const url = `/api/pdf/${encodeURIComponent(currentPdf)}/stamps/${stamp.xref}` + (useForce ? "?force=true" : "");
            const res = await fetch(url, { method: 'POST' });
            if (!res.ok) {
                const data = await res.json();
                let shouldForce = forceAll;
                if (!shouldForce) {
                    shouldForce = confirm(`Failed to delete stamp from PDF (${data.error || 'Not found'}). Force-delete database record?`);
                    if (shouldForce) {
                        forceAll = true;
                    } else {
                        throw new Error(data.error || 'Delete failed');
                    }
                }
                
                if (shouldForce && !useForce) {
                    const forceRes = await fetch(`/api/pdf/${encodeURIComponent(currentPdf)}/stamps/${stamp.xref}?force=true`, { method: 'POST' });
                    if (!forceRes.ok) {
                        throw new Error('Force delete failed');
                    }
                }
            }
            currentPdfStamps = currentPdfStamps.filter(st => st.xref !== stamp.xref);
            selectedStamps.delete(stamp.xref);
            
            renderStampsList();
            if (scannerStatus) {
                scannerStatus.textContent = `Deleted stamp.`;
            }

            document.querySelectorAll(`.stamp-highlight-rect[data-xref="${stamp.xref}"]`).forEach(el => el.remove());

            pdfCacheBuster = Date.now();
            const pageNum = stamp.page_num;
            const pageWrapper = document.getElementById(`page-wrapper-${pageNum}`);
            if (pageWrapper) {
                const img = pageWrapper.querySelector('.pdf-image');
                if (img) {
                    img.src = `/api/pdf/${encodeURIComponent(currentPdf)}/page/${pageNum}/image?scale=2&t=${pdfCacheBuster}`;
                    img.dataset.loadedScale = 2;
                }
                const hiResImg = pageWrapper.querySelector('.pdf-image-hires');
                if (hiResImg) hiResImg.style.display = 'none';
            }
            return true;
        } catch (err) {
            alert('Failed to delete stamp: ' + err.message);
            return false;
        }
    };

    // --- Stamps List Rendering ---
    function renderStampsList() {
        window.currentPdfStamps = currentPdfStamps;
        try { window.currentPageNum = pageNum; } catch (e) {}
        if (!stampsList) return;
        stampsList.innerHTML = '';

        if (currentPdfStamps.length === 0) {
            const li = document.createElement('li');
            li.className = 'stamps-empty-state';
            li.textContent = 'No stamps detected on this drawing.';
            stampsList.appendChild(li);
            if (stampsCountLabel) stampsCountLabel.textContent = 'No stamps found';
            if (stampTabBadge) stampTabBadge.style.display = 'none';
            return;
        }

        if (stampsCountLabel) stampsCountLabel.textContent = `${currentPdfStamps.length} stamp${currentPdfStamps.length !== 1 ? 's' : ''} found`;
        if (stampTabBadge) {
            stampTabBadge.textContent = currentPdfStamps.length;
            stampTabBadge.style.display = 'inline-block';
        }

        currentPdfStamps.forEach(stamp => {
            const li = document.createElement('li');
            li.className = 'stamp-row';
            li.dataset.xref = stamp.xref;
            if (selectedStamps.has(stamp.xref)) li.classList.add('selected');

            li.innerHTML = `
                <span class="stamp-row-icon">💮</span>
                <div class="stamp-row-info">
                    <div class="stamp-row-subject">${stamp.pattern_name || stamp.name || stamp.title || 'Stamp'}</div>
                    <div class="stamp-row-meta">Page ${stamp.page_num}${stamp.subject ? ' · ' + stamp.subject : ''}</div>
                </div>
                <div class="stamp-actions" style="display: flex; gap: 5px;">
                    <button class="stamp-move-btn" title="Move stamp on canvas">✏️</button>
                    <button class="stamp-explode-btn" title="Explode stamp (Convert to lines)">💥</button>
                    <button class="stamp-delete-btn" title="Delete stamp from PDF">🗑</button>
                </div>
            `;

            // Click row → select & highlight on canvas
            li.addEventListener('click', (e) => {
                if (e.target.closest('button')) return;
                handleStampSelection(stamp, e);
                // Zoom to stamp on canvas
                if (selectedStamps.has(stamp.xref)) {
                    zoomToStamp(stamp);
                }
            });

            // Move button → enter ghost placement mode
            li.querySelector('.stamp-move-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                handleStampSelection(stamp, null);
                zoomToStamp(stamp);
                if (window.startStampMoveMode) {
                    window.startStampMoveMode(stamp);
                } else {
                    alert('Move mode not available.');
                }
            });

            // Trash button → delete
            li.querySelector('.stamp-delete-btn').addEventListener('click', async (e) => {
                e.stopPropagation();
                const stampsToDelete = selectedStamps.has(stamp.xref) 
                    ? currentPdfStamps.filter(s => selectedStamps.has(s.xref))
                    : [stamp];
                    
                if (!confirm(`Delete ${stampsToDelete.length} stamp(s)?\nThis permanently removes them from the PDF.`)) return;

                const btn = e.currentTarget;
                btn.textContent = '…';
                btn.disabled = true;

                try {
                    if (window.deleteStampsBulk) {
                        await window.deleteStampsBulk(stampsToDelete.map(s => s.xref));
                    } else {
                        for (const s of stampsToDelete) {
                            await window.deleteStampByXref(s.xref, false);
                        }
                    }
                } catch (err) {
                    alert('Failed to delete stamp(s): ' + err.message);
                } finally {
                    btn.textContent = '🗑';
                    btn.disabled = false;
                }
            });


            // Explode button → flatten into base content
            const explodeBtn = li.querySelector('.stamp-explode-btn');
            if (explodeBtn) {
                explodeBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const stampsToExplode = selectedStamps.has(stamp.xref)
                        ? currentPdfStamps.filter(s => selectedStamps.has(s.xref))
                        : [stamp];
                        
                    if (!confirm(`Explode ${stampsToExplode.length} stamp(s)?\nThis permanently bakes them into the PDF drawing lines.`)) return;

                    const btn = e.currentTarget;
                    btn.textContent = '…';
                    btn.disabled = true;

                    try {
                        for (const s of stampsToExplode) {
                            const res = await fetch(`/api/pdf/${encodeURIComponent(currentPdf)}/stamps/${s.xref}/explode`, { method: 'POST' });
                            if (!res.ok) {
                                const data = await res.json();
                                throw new Error(data.error || 'Explode failed');
                            }
                            currentPdfStamps = currentPdfStamps.filter(st => st.xref !== s.xref);
                            selectedStamps.delete(s.xref);
                            document.querySelectorAll(`.stamp-highlight-rect[data-xref="${s.xref}"]`).forEach(el => el.remove());
                        }

                        renderStampsList();

                        const pagesToReload = new Set(stampsToExplode.map(s => s.page_num));
                        pdfCacheBuster = Date.now();
                        pagesToReload.forEach(pageNum => {
                            const pageWrapper = document.getElementById(`page-wrapper-${pageNum}`);
                            if (pageWrapper && pageWrapper.dataset.loaded === 'true') {
                                const rid = parseInt(pageWrapper.dataset.renderId);
                                loadPageContent(pageWrapper, pageNum, rid);
                            }
                        });
                    } catch (err) {
                        alert('Error exploding stamp: ' + err.message);
                        btn.textContent = '💥';
                        btn.disabled = false;
                    }
                });
            }

            stampsList.appendChild(li);
        });
    }

    // --- Patterns List Rendering ---
    function renderPatternsList() {
        if (!patternsList) return;
        patternsList.innerHTML = '';

        const filteredPatterns = patternFilter
            ? currentPdfPatterns.filter(p => getPatternFilterType(p.type) === patternFilter)
            : currentPdfPatterns;

        if (filteredPatterns.length === 0) {
            const li = document.createElement('li');
            li.className = 'stamps-empty-state';
            li.textContent = 'No patterns saved for this PDF.';
            patternsList.appendChild(li);
            if (patternsCountLabel) patternsCountLabel.textContent = 'No patterns found';
            return;
        }

        if (patternsCountLabel) patternsCountLabel.textContent = `${filteredPatterns.length} pattern${filteredPatterns.length !== 1 ? 's' : ''} saved`;

        filteredPatterns.forEach(pattern => {
            const patternType = normalizePatternType(pattern.type);
            const li = document.createElement('li');
            li.className = 'stamp-row';
            li.dataset.id = pattern.id;
            if (selectedPatterns.has(pattern.id)) li.classList.add('selected');

            li.innerHTML = `
                <span class="stamp-row-icon">${patternType === 'grill' ? 'Air Outlet' : 'System'}</span>
                <div class="stamp-row-info">
                    <div class="stamp-row-subject">${pattern.name || 'Pattern'}</div>
                    <div class="stamp-row-meta">Page ${pattern.page_num} · ${pattern.vectors ? pattern.vectors.length : 0} lines</div>
                </div>
                <div class="stamp-actions" style="display: flex; gap: 5px;">
                    <button class="pattern-delete-btn" title="Delete pattern">🗑</button>
                </div>
            `;

            // Trash button → delete
            const deleteBtn = li.querySelector('.pattern-delete-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    
                    const patternsToDelete = selectedPatterns.has(pattern.id)
                        ? currentPdfPatterns.filter(p => selectedPatterns.has(p.id))
                        : [pattern];
                        
                    if (!confirm(`Delete ${patternsToDelete.length} pattern(s)?`)) return;

                    const btn = e.currentTarget;
                    btn.textContent = '…';
                    btn.disabled = true;

                    try {
                        for (const p of patternsToDelete) {
                            const res = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/pdf/${encodeURIComponent(currentPdf)}/patterns/${p.id}`, { method: 'DELETE' });
                            if (!res.ok) {
                                const data = await res.json();
                                throw new Error(data.error || 'Delete failed');
                            }
                            currentPdfPatterns = currentPdfPatterns.filter(pat => pat.id !== p.id);
                            selectedPatterns.delete(p.id);
                            document.querySelectorAll(`.pattern-highlight-rect[data-id="${p.id}"]`).forEach(el => el.remove());
                        }
                        clearSelection();
                        renderPatternsList();
                        updatePatternSelections();
                    } catch (err) {
                        alert('Error deleting pattern: ' + err.message);
                        btn.textContent = '🗑';
                        btn.disabled = false;
                    }
                });
            }
            li.addEventListener('click', (e) => {
                if (e.target.closest('button')) return;
                handlePatternSelection(pattern, e);
                if (selectedPatterns.has(pattern.id)) {
                    flashPattern(pattern);
                    showPatternInInspector(pattern);
                }
            });

            patternsList.appendChild(li);
        });
    }

    function zoomToStamp(stamp) {
        window.isZoomingToStamp = true;
        const pageWrapper = document.getElementById(`page-wrapper-${stamp.page_num}`);
        if (!pageWrapper) {
            window.isZoomingToStamp = false;
            return;
        }

        // Stamp center in page (PDF pt) space
        const centerX = stamp.rect[0] + (stamp.rect[2] - stamp.rect[0]) / 2;
        const centerY = stamp.rect[1] + (stamp.rect[3] - stamp.rect[1]) / 2;

        // Stamp size — pick a comfortable zoom level
        const stampW = Math.max(stamp.rect[2] - stamp.rect[0], 40);
        const stampH = Math.max(stamp.rect[3] - stamp.rect[1], 40);
        const viewerRect = viewerContainer.getBoundingClientRect();

        let targetScale = Math.min(
            (viewerRect.width  * 0.6) / stampW,
            (viewerRect.height * 0.6) / stampH
        );
        targetScale = Math.max(1.5, Math.min(targetScale, 8.0));

        // Element centre in the un-scaled container coordinate space
        const elementCenterXInContainer = pageWrapper.offsetLeft + centerX;
        const elementCenterYInContainer = pageWrapper.offsetTop  + centerY;

        panZoomContainer.classList.add('smooth-transition');

        scale      = targetScale;
        translateX = viewerRect.width  / 2 - elementCenterXInContainer * scale;
        translateY = viewerRect.height / 2 - elementCenterYInContainer * scale;

        updateTransform();

        clearTimeout(zoomEndTimer);
        zoomEndTimer = setTimeout(() => {
            panZoomContainer.classList.remove('smooth-transition');
            updateImageResolutions();
            window.isZoomingToStamp = false;
        }, 400);
    }

    // Exposed globally so the data viewer can navigate to a stamp on the canvas
    window.navigateToStamp = async function(pdfPath, xref, page) {
        // 1. Close data viewer, show canvas
        const dvContainer = document.getElementById('data-viewer-container');
        if (dvContainer) dvContainer.style.display = 'none';
        const viewerContainerEl = document.getElementById('viewer-container');
        if (viewerContainerEl) viewerContainerEl.style.display = '';
        
        if (window.switchToolbarPanel) window.switchToolbarPanel('toolbar-pdf-tools');

        function highlightAndZoom() {
            const stamp = currentPdfStamps.find(s => String(s.xref) === String(xref));
            if (stamp) {
                selectedStamps.clear();
                selectedStamps.add(stamp.xref);
                updateStampSelections();
                switchSidebarTab('stamps');
                toggleSidebarRight(true);
                
                if (layoutMode === 'single' && currentPage !== stamp.page_num) {
                    currentPage = stamp.page_num;
                    reloadView().then(() => {
                        requestAnimationFrame(() => zoomToStamp(stamp));
                    });
                } else {
                    requestAnimationFrame(() => requestAnimationFrame(() => zoomToStamp(stamp)));
                }
            } else {
                console.warn('navigateToStamp: Stamp not found with xref', xref);
            }
        }

        // Match using base filename since UI uses relative paths and DB uses absolute paths
        const getBase = p => (p || '').toLowerCase().replace(/\\/g, '/').split('/').pop();

        if (getBase(currentPdf) === getBase(pdfPath)) {
            highlightAndZoom();
        } else {
            const listItems = Array.from(document.querySelectorAll('.file-list li'));
            const li = listItems.find(el => getBase(el.title) === getBase(pdfPath));
            if (li) {
                await loadPdf(li.title, li);
                highlightAndZoom();
            } else {
                console.warn('navigateToStamp: PDF not found in list', pdfPath);
            }
        }
    };

    function flashPattern(pattern) {
        const pageNum = pattern.page_num;
        const pageWrapper = document.getElementById(`page-wrapper-${pageNum}`);
        if (!pageWrapper) return;
        
        const svg = pageWrapper.querySelector('.vector-overlay');
        if (!svg) return;
        
        const rect = svg.querySelector(`.pattern-highlight-rect[data-id="${pattern.id}"]`);
        if (!rect) return;

        // Calculate center for zooming
        const rectX = parseFloat(rect.getAttribute('x'));
        const rectY = parseFloat(rect.getAttribute('y'));
        const rectW = parseFloat(rect.getAttribute('width'));
        const rectH = parseFloat(rect.getAttribute('height'));

        const centerX = rectX + rectW / 2;
        const centerY = rectY + rectH / 2;

        const viewerRect = viewerContainer.getBoundingClientRect();
        let targetScale = Math.min(
            (viewerRect.width  * 0.6) / Math.max(rectW, 40),
            (viewerRect.height * 0.6) / Math.max(rectH, 40)
        );
        targetScale = Math.max(1.5, Math.min(targetScale, 8.0));

        const elementCenterXInContainer = pageWrapper.offsetLeft + centerX;
        const elementCenterYInContainer = pageWrapper.offsetTop  + centerY;

        panZoomContainer.classList.add('smooth-transition');

        scale      = targetScale;
        translateX = viewerRect.width  / 2 - elementCenterXInContainer * scale;
        translateY = viewerRect.height / 2 - elementCenterYInContainer * scale;

        updateTransform();

        clearTimeout(zoomEndTimer);
        zoomEndTimer = setTimeout(() => {
            panZoomContainer.classList.remove('smooth-transition');
            updateImageResolutions();
        }, 400);

        // Flash animation
        rect.classList.remove('flashing');
        void rect.offsetWidth; // trigger reflow
        rect.classList.add('flashing');
        
        // Highlight the list row
        document.querySelectorAll('#patterns-list .stamp-row').forEach(row => {
            row.classList.toggle('selected', row.dataset.id === pattern.id);
        });
    }

    function showPatternInInspector(pattern) {
        const vectors = pattern.vectors || [];

        // Update selection count label
        selectionCount.textContent = vectors.length;
        btnCopyInfo.disabled = vectors.length === 0;
        // Don't enable save/clear – these are read-only view of a saved pattern
        btnSaveSelection.disabled = true;
        btnClearSelection.disabled = true;

        inspectorBody.innerHTML = '';
        const rawArray = [];

        let count = 0;

        vectors.forEach(item => {
            if (count < 100) {
                const tr = document.createElement('tr');

                const type = item.type || 'Line';
                const length = typeof item.length === 'number' ? item.length.toFixed(2) : '–';
                const thickness = typeof item.thickness === 'number' ? item.thickness.toFixed(2) : '–';

                let coordsText = '–';
                if (item.start && item.end) {
                    coordsText = `(${item.start[0].toFixed(1)}, ${item.start[1].toFixed(1)}) → (${item.end[0].toFixed(1)}, ${item.end[1].toFixed(1)})`;
                } else if (item.x !== undefined) {
                    coordsText = `(${item.x.toFixed(1)}, ${item.y.toFixed(1)}) → (${(item.x + item.width).toFixed(1)}, ${(item.y + item.height).toFixed(1)})`;
                } else if (item.points && item.points.length >= 2) {
                    const s = item.points[0], en = item.points[item.points.length - 1];
                    coordsText = `(${s[0].toFixed(1)}, ${s[1].toFixed(1)}) → (${en[0].toFixed(1)}, ${en[1].toFixed(1)})`;
                }

                const colorHex = item.color_hex || '#888';

                const tdType   = document.createElement('td'); tdType.textContent   = type;
                const tdLen    = document.createElement('td'); tdLen.textContent    = length;
                const tdW      = document.createElement('td'); tdW.textContent      = thickness;
                const tdCoords = document.createElement('td'); tdCoords.textContent = coordsText;

                const tdCol = document.createElement('td');
                const swatch = document.createElement('span');
                swatch.className = 'color-swatch';
                swatch.style.backgroundColor = colorHex;
                let colorText = 'None';
                if (item.color) {
                    colorText = `(${item.color[0].toFixed(2)}, ${item.color[1].toFixed(2)}, ${item.color[2].toFixed(2)})`;
                }
                tdCol.appendChild(swatch);
                tdCol.appendChild(document.createTextNode(colorText));

                tr.appendChild(tdType);
                tr.appendChild(tdLen);
                tr.appendChild(tdW);
                tr.appendChild(tdCoords);
                tr.appendChild(tdCol);

                // --- Click: highlight the SVG vector on the canvas and zoom to it ---
                tr.style.cursor = 'pointer';
                tr.addEventListener('click', async () => {
                    // Clear previous row highlights
                    document.querySelectorAll('.inspector-table tbody tr.active').forEach(r => r.classList.remove('active'));
                    tr.classList.add('active');

                    // Clear previous SVG highlights
                    document.querySelectorAll('.vector-item.highlighted').forEach(el => el.classList.remove('highlighted'));

                    if (item.globalId) {
                        highlightedItemId = item.globalId;
                        if (currentRendererSetting === 'canvas') {
                            refreshCanvasHighlights();
                        }

                        // Switch page if needed (single-page layout)
                        if (layoutMode === 'single' && item.page && currentPage !== item.page) {
                            currentPage = item.page;
                            await reloadView();
                            await new Promise(resolve => requestAnimationFrame(resolve));
                        }

                        const svgEl = document.getElementById(`vec-${item.globalId}`);
                        if (svgEl) {
                            svgEl.classList.add('highlighted');
                        }

                        // Zoom to the individual line
                        zoomToItem(item);
                    }
                });

                inspectorBody.appendChild(tr);
            }

            rawArray.push(item);
            count++;
        });

        if (vectors.length > 100) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 5;
            td.style.textAlign = 'center';
            td.style.color = '#94a3b8';
            td.style.fontStyle = 'italic';
            td.style.padding = '8px';
            td.textContent = `... and ${vectors.length - 100} more items (copied to clipboard fully)`;
            tr.appendChild(td);
            inspectorBody.appendChild(tr);
        }

        window.currentInspectorRawArray = rawArray;
        if (rawArray.length > 100) {
            rawOutput.value = "JSON too large to display. Click 'Copy Info' to copy the full JSON to your clipboard.";
        } else {
            rawOutput.value = rawArray.length > 0 ? JSON.stringify(rawArray, null, 2) : '';
        }
    }

    if (btnRunStamps) {
        btnRunStamps.addEventListener('click', () => {
            if (!currentPdf) return;
            
            const isMobile = window.innerWidth <= 1024;
            const isVisible = isMobile ? sidebarRight.classList.contains('open') : sidebarRight.style.display !== 'none';
            const isStampsActive = document.getElementById('panel-stamps').classList.contains('active');
            
            if (isVisible && isStampsActive) {
                // If already visible and on stamps tab, close it
                toggleSidebarRight(false);
            } else {
                // Otherwise, open it and switch to stamps tab
                switchSidebarTab('stamps');
                toggleSidebarRight(true);
            }
        });
    }

    // Add Item Modal Helper Functions
    function openAddItemModal(type) {
        if (!currentProject) {
            alert("Please select or create a project first.");
            return;
        }
        currentAddType = normalizePatternType(type);
        addItemModalTitle.textContent = currentAddType === 'grill' ? 'Select Air Outlet Type' : 'Select System Type';
        newItemInputName.value = '';
        itemModalErrorMessage.style.display = 'none';
        
        // Populate dropdown with existing item names of this type
        itemTypeSelect.innerHTML = '<option value="">-- Create New --</option>';
        const names = new Set();
        if (typeof currentPdfPatterns !== 'undefined') {
            currentPdfPatterns.forEach(pattern => {
                if (normalizePatternType(pattern.type) === currentAddType) {
                    names.add(pattern.name);
                }
            });
        }
        
        names.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            itemTypeSelect.appendChild(opt);
        });
        
        addItemModal.style.display = 'flex';
        newItemInputName.focus();

        // When user picks from dropdown, switch to "Edit Existing" mode
        itemTypeSelect.onchange = () => {
            if (itemTypeSelect.value) {
                // Existing pattern selected
                newItemInputName.value = '';
                newItemInputName.disabled = true;
                newItemInputName.placeholder = 'Editing existing pattern…';
                btnSubmitItem.textContent = 'Edit Existing';
                itemModalErrorMessage.style.display = 'none';
            } else {
                newItemInputName.disabled = false;
                newItemInputName.placeholder = 'e.g., Type A';
                btnSubmitItem.textContent = 'Confirm';
                itemModalErrorMessage.style.display = 'none';
            }
        };
    }

    function hideItemModal() {
        addItemModal.style.display = 'none';
        isSavingDirectly = false;
        // Reset modal state
        newItemInputName.disabled = false;
        newItemInputName.placeholder = 'e.g., Type A';
        btnSubmitItem.textContent = 'Confirm';
        itemTypeSelect.onchange = null;
    }
    
    btnCancelItem.addEventListener('click', hideItemModal);
    btnCloseItemModal.addEventListener('click', hideItemModal);
    addItemModal.addEventListener('click', (e) => {
        if (e.target === addItemModal) hideItemModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (addItemModal.style.display === 'flex') {
                hideItemModal();
            }
            // Cancel active grill/HVAC creation mode
            if (activeAddState) {
                deactivateAddMode();
                selectionMode = false;
                viewerContainer.classList.remove('selection-mode');
                clearSelection();
                // Close the side panel
                toggleSidebarRight(false);
                patternFilter = null;
            }
        }
    });

    btnSubmitItem.addEventListener('click', async () => {
        // Determine if user picked an existing pattern or typed a new name
        const isEditExisting = !!itemTypeSelect.value;
        let name = isEditExisting ? itemTypeSelect.value : newItemInputName.value.trim();

        if (!name) {
            itemModalErrorMessage.textContent = 'Please select an existing type or enter a new name.';
            itemModalErrorMessage.style.display = 'block';
            return;
        }

        // Same-name patterns are allowed — they share a numbering sequence in the scan

        // Find the existing pattern object if editing
        const existingPattern = isEditExisting
            ? currentPdfPatterns.find(p => p.name.trim().toLowerCase() === name.toLowerCase() && normalizePatternType(p.type) === currentAddType)
            : null;

        addItemModal.style.display = 'none';
        
        if (isSavingDirectly) {
            isSavingDirectly = false;
            await saveCurrentSelection(currentAddType, name, existingPattern ? existingPattern.id : null);
        } else {
            // Deactivate any existing active add mode
            deactivateAddMode();
            
            // Set active add state — include editId if editing an existing pattern
            activeAddState = { type: currentAddType, name: name, editId: existingPattern ? existingPattern.id : null };

            // If editing, pre-select the existing pattern's vectors on the current page
            if (existingPattern && existingPattern.vectors && existingPattern.vectors.length > 0) {
                clearSelection();
                existingPattern.vectors.forEach(v => {
                    const globalId = v.globalId || `p${existingPattern.page_num}-${v.id}`;
                    const svgEl = document.getElementById(`vec-${globalId}`);
                    if (svgEl) {
                        const fullItem = { ...v, globalId };
                        selectedItems.set(globalId, fullItem);
                        svgEl.classList.add('selected');
                    }
                });
                updateInspector();
            }
            
            // Toggle selection mode ON
            selectionMode = true;
            viewerContainer.classList.add('selection-mode');
            
            // Open right sidebar and show Patterns tab
            toggleSidebarRight(true);
            switchSidebarTab('patterns');
            
            // Style the active Add button
            if (btnAddPatternPlus) {
                btnAddPatternPlus.classList.add('active');
                const editLabel = existingPattern ? `Editing: ${name}` : `Adding: ${name}`;
                btnAddPatternPlus.title = editLabel;
            }

            // Show the split + button in the sidebar
            updatePatternModeButtons();
        }
    });

    newItemInputName.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            btnSubmitItem.click();
        }
    });

    function deactivateAddMode() {
        activeAddState = null;
        if (btnAddPatternPlus) {
            btnAddPatternPlus.classList.remove('active');
            btnAddPatternPlus.title = "Add Pattern";
        }
        updatePatternModeButtons();
    }

    async function saveCurrentSelection(type, name, editId = null) {
        // Use editId from activeAddState if not explicitly passed
        const resolvedEditId = editId ?? (activeAddState ? activeAddState.editId : null);

        if (!currentProject || !currentPdf) {
            alert('No active project or PDF.');
            return;
        }

        const normalizedType = normalizePatternType(type);
        
        const vectors = Array.from(selectedItems.values());
        
        btnSaveSelection.disabled = true;
        try {
            let res, result;

            if (resolvedEditId) {
                // PATCH — update existing pattern's vectors
                res = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/pdf/${encodeURIComponent(currentPdf)}/patterns/${encodeURIComponent(resolvedEditId)}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        page_num: currentPage,
                        vectors: vectors
                    })
                });
                result = await res.json();
                if (res.ok && result.success) {
                    // Replace the pattern in the local array
                    const idx = currentPdfPatterns.findIndex(p => p.id === resolvedEditId);
                    if (idx !== -1) currentPdfPatterns[idx] = result.pattern;
                }
            } else {
                // POST — create new pattern
                res = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/pdf/${encodeURIComponent(currentPdf)}/patterns`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name,
                        type: normalizedType,
                        page_num: currentPage,
                        vectors: vectors
                    })
                });
                result = await res.json();
                if (res.ok && result.success) {
                    currentPdfPatterns.push(result.pattern);
                }
            }

            if (res.ok && result.success) {
                renderPatternsList();
                
                // Redraw annotations on the current page SVG overlays
                document.querySelectorAll('.page-wrapper').forEach(wrapper => {
                    const pageNum = parseInt(wrapper.dataset.page);
                    const svg = wrapper.querySelector('.vector-overlay');
                    if (svg) {
                        overlayPatternRects(pageNum, svg);
                    }
                });
                
                // Show "Saved!" / "Updated!" notification
                const originalText = btnSaveSelection.textContent;
                btnSaveSelection.textContent = resolvedEditId ? "Updated!" : "Saved!";
                btnSaveSelection.style.backgroundColor = "#10b981"; // Green
                setTimeout(() => {
                    btnSaveSelection.textContent = originalText;
                    btnSaveSelection.style.backgroundColor = "";
                    btnSaveSelection.disabled = selectedItems.size === 0;
                }, 2000);

                // Clear selection
                clearSelection();
                
                // Deactivate Adding mode
                deactivateAddMode();
                selectionMode = false;
                viewerContainer.classList.remove('selection-mode');
            } else {
                alert(result.error || 'Failed to save annotation.');
                btnSaveSelection.disabled = selectedItems.size === 0;
            }
        } catch (e) {
            alert('Error saving annotation: ' + e.message);
            btnSaveSelection.disabled = selectedItems.size === 0;
        }
    }

    // Silent save: saves the current selection without UI feedback or deactivating add mode.
    // Used by the "+" (add another) and Scan Patterns buttons to auto-save before moving on.
    async function saveCurrentSelectionSilent(type, name, editId = null) {
        const resolvedEditId = editId ?? null;
        if (!currentProject || !currentPdf) return;
        if (selectedItems.size === 0) return;

        const normalizedType = normalizePatternType(type);
        const vectors = Array.from(selectedItems.values());

        try {
            let res, result;
            if (resolvedEditId) {
                res = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/pdf/${encodeURIComponent(currentPdf)}/patterns/${encodeURIComponent(resolvedEditId)}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ page_num: currentPage, vectors })
                });
                result = await res.json();
                if (res.ok && result.success) {
                    const idx = currentPdfPatterns.findIndex(p => p.id === resolvedEditId);
                    if (idx !== -1) currentPdfPatterns[idx] = result.pattern;
                }
            } else {
                res = await fetch(`/api/projects/${encodeURIComponent(currentProject)}/pdf/${encodeURIComponent(currentPdf)}/patterns`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, type: normalizedType, page_num: currentPage, vectors })
                });
                result = await res.json();
                if (res.ok && result.success) {
                    currentPdfPatterns.push(result.pattern);
                }
            }
            if (res.ok && result.success) {
                renderPatternsList();
                document.querySelectorAll('.page-wrapper').forEach(wrapper => {
                    const pageNum = parseInt(wrapper.dataset.page);
                    const svg = wrapper.querySelector('.vector-overlay');
                    if (svg) overlayPatternRects(pageNum, svg);
                });
                clearSelection();
                // Keep activeAddState active so user can continue adding
            } else {
                alert(result.error || 'Failed to save annotation.');
            }
        } catch (e) {
            alert('Error saving annotation: ' + e.message);
        }
    }

    function handleVectorMousedown(e, itemData, svgElement) {
        if (!selectionMode) return;
        if (e && typeof e.stopPropagation === 'function') e.stopPropagation(); // Stop panning
        
        const isSelected = selectedItems.has(itemData.globalId);
        
        // On touch events or if explicitly toggle-mode:
        const isTouch = e && (e.type && e.type.startsWith('touch'));

        if (isTouch) {
            // Toggle behavior for touch screens (no modifier keys needed)
            if (isSelected) {
                removeFromSelection(itemData.globalId, svgElement);
            } else {
                addToSelection(itemData, svgElement);
            }
        } else {
            // Standard keyboard-modifier mouse click behavior
            if (e.ctrlKey || e.metaKey) {
                // Ctrl/Meta: toggle the clicked item
                if (isSelected) {
                    removeFromSelection(itemData.globalId, svgElement);
                } else {
                    addToSelection(itemData, svgElement);
                }
            } else if (e.shiftKey) {
                if (isSelected) removeFromSelection(itemData.globalId, svgElement);
            } else {
                // Plain click: toggle if already selected, otherwise select only this one
                if (isSelected) {
                    removeFromSelection(itemData.globalId, svgElement);
                } else {
                    clearSelection();
                    addToSelection(itemData, svgElement);
                }
            }
        }
    }

    function refreshCanvasHighlights() {
        if (currentRendererSetting !== 'canvas') return;
        canvasRenderers.forEach((renderer, pageNum) => {
            renderer.clearHighlights();
            
            // 1. Draw selections
            selectedItems.forEach(item => {
                if (parseInt(item.page) === parseInt(pageNum)) {
                    renderer.drawHighlight(item, 'selected');
                }
            });
            
            // 2. Draw hover highlight
            const isTabActive = typeof tabCycleCandidates !== 'undefined' && tabCycleCandidates.length > 0 && tabCycleIndex >= 0;
            if (highlightedItemId && !isTabActive) {
                const hoverPageMatch = highlightedItemId.match(/^p(\d+)-/);
                if (hoverPageMatch && parseInt(hoverPageMatch[1]) === parseInt(pageNum)) {
                    const itemData = selectedItems.get(highlightedItemId) || 
                                     (pagesData.get(pageNum) && pagesData.get(pageNum).drawings.find(d => d.globalId === highlightedItemId));
                    if (itemData) {
                        renderer.drawHighlight(itemData, 'hover');
                    }
                }
            }
            
            // 3. Draw tab cycle preview highlight
            if (typeof tabCycleCandidates !== 'undefined' && tabCycleCandidates.length > 0 && tabCycleIndex >= 0) {
                const candidate = tabCycleCandidates[tabCycleIndex];
                if (candidate.originalData && candidate.originalData.type === 'vector') {
                    candidate.items.forEach(item => {
                        if (item && parseInt(item.page) === parseInt(pageNum)) {
                            renderer.drawHighlight(item, 'hover');
                        }
                    });
                }
            }

            // 4. Draw lasso preview highlights
            if (typeof lassoHighlightedItems !== 'undefined') {
                lassoHighlightedItems.forEach(item => {
                    if (item && parseInt(item.page) === parseInt(pageNum)) {
                        renderer.drawHighlight(item, 'hover');
                    }
                });
            }
        });
    }

    function addToSelection(itemData, svgElement) {
        selectedItems.set(itemData.globalId, itemData);
        if (svgElement) {
            svgElement.classList.add('selected');
        }
        // Clear previous highlight
        highlightedItemId = null;
        if (currentRendererSetting !== 'canvas') {
            document.querySelectorAll('.vector-item.highlighted').forEach(el => {
                el.classList.remove('highlighted');
            });
        } else {
            refreshCanvasHighlights();
        }
        updateInspector();
    }

    function removeFromSelection(globalId, svgElement) {
        selectedItems.delete(globalId);
        if (svgElement) {
            svgElement.classList.remove('selected');
            svgElement.classList.remove('highlighted');
        }
        if (highlightedItemId === globalId) {
            highlightedItemId = null;
        }
        if (currentRendererSetting === 'canvas') {
            refreshCanvasHighlights();
        }
        updateInspector();
    }

    function clearSelection() {
        selectedItems.clear();
        if (currentRendererSetting !== 'canvas') {
            document.querySelectorAll('.vector-item.selected').forEach(el => {
                el.classList.remove('selected');
            });
            document.querySelectorAll('.vector-item.highlighted').forEach(el => {
                el.classList.remove('highlighted');
            });
        } else {
            refreshCanvasHighlights();
        }
        highlightedItemId = null;

        // Clear stamp/pattern selection
        selectedStamps.clear();
        lastSelectedStampIndex = -1;
        selectedPatterns.clear();
        lastSelectedPatternIndex = -1;
        updateStampSelections();
        updatePatternSelections();

        updateInspector();
    }

    btnClearSelection.addEventListener('click', clearSelection);

    // --- Lasso Selection ---
    function getViewerCoords(e) {
        const rect = viewerContainer.getBoundingClientRect();
        let clientX = 0;
        let clientY = 0;
        if (e.clientX !== undefined) {
            clientX = e.clientX;
            clientY = e.clientY;
        } else if (e.touches && e.touches[0]) {
            clientX = e.touches[0].clientX;
            clientY = e.touches[0].clientY;
        } else if (e.changedTouches && e.changedTouches[0]) {
            clientX = e.changedTouches[0].clientX;
            clientY = e.changedTouches[0].clientY;
        }
        return {
            x: clientX - rect.left,
            y: clientY - rect.top
        };
    }

    function startLasso(e) {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        isLassoing = true;
        const coords = getViewerCoords(e);
        lassoStartX = coords.x;
        lassoStartY = coords.y;
        
        selectionLasso.style.left = `${lassoStartX}px`;
        selectionLasso.style.top = `${lassoStartY}px`;
        selectionLasso.style.width = '0px';
        selectionLasso.style.height = '0px';
        selectionLasso.style.display = 'block';
    }

    function updateLasso(e) {
        const coords = getViewerCoords(e);
        const x = Math.min(coords.x, lassoStartX);
        const y = Math.min(coords.y, lassoStartY);
        const width = Math.abs(coords.x - lassoStartX);
        const height = Math.abs(coords.y - lassoStartY);
        
        selectionLasso.style.left = `${x}px`;
        selectionLasso.style.top = `${y}px`;
        selectionLasso.style.width = `${width}px`;
        selectionLasso.style.height = `${height}px`;

        if (!selectionMode) return;

        const endX = coords.x;
        const endY = coords.y;
        const minX = Math.min(lassoStartX, endX);
        const maxX = Math.max(lassoStartX, endX);
        const minY = Math.min(lassoStartY, endY);
        const maxY = Math.max(lassoStartY, endY);

        lassoHighlightedItems = [];

        const pageWrappers = panZoomContainer.querySelectorAll('.page-wrapper');
        pageWrappers.forEach(wrapper => {
            const pageNum = parseInt(wrapper.dataset.page);
            const pageData = pagesData.get(pageNum);
            if (!pageData) return;

            const wrapperLeft = wrapper.offsetLeft;
            const wrapperTop = wrapper.offsetTop;

            const pdfMinX = (minX - translateX) / scale - wrapperLeft;
            const pdfMaxX = (maxX - translateX) / scale - wrapperLeft;
            const pdfMinY = (minY - translateY) / scale - wrapperTop;
            const pdfMaxY = (maxY - translateY) / scale - wrapperTop;

            if (currentRendererSetting === 'canvas') {
                const renderer = canvasRenderers.get(pageNum);
                if (renderer) {
                    const queryRect = { minX: pdfMinX, maxX: pdfMaxX, minY: pdfMinY, maxY: pdfMaxY };
                    const matchedDrawings = renderer.queryRect(queryRect);
                    matchedDrawings.forEach(item => {
                        if (isItemInRect(item, pdfMinX, pdfMaxX, pdfMinY, pdfMaxY)) {
                            lassoHighlightedItems.push(item);
                        }
                    });
                }
            } else {
                pageData.drawings.forEach(item => {
                    const isIn = isItemInRect(item, pdfMinX, pdfMaxX, pdfMinY, pdfMaxY);
                    const svgEl = document.getElementById(`vec-${item.globalId}`);
                    if (svgEl) {
                        if (isIn) {
                            svgEl.classList.add('highlighted');
                        } else {
                            const isSelected = selectedItems.has(item.globalId);
                            if (item.globalId !== highlightedItemId && !isSelected) {
                                svgEl.classList.remove('highlighted');
                            }
                        }
                    }
                });
            }
        });

        if (currentRendererSetting === 'canvas') {
            refreshCanvasHighlights();
        }
    }

    function finishLasso(e) {
        isLassoing = false;
        selectionLasso.style.display = 'none';
        
        if (!selectionMode) return;

        // Calculate Lasso rect in container local coordinates
        const coords = getViewerCoords(e);
        const endX = coords.x;
        const endY = coords.y;
        
        const minX = Math.min(lassoStartX, endX);
        const maxX = Math.max(lassoStartX, endX);
        const minY = Math.min(lassoStartY, endY);
        const maxY = Math.max(lassoStartY, endY);
        
        // Show the processing spinner next to the selection count
        selectionSpinner.style.display = 'inline-block';

        // Process intersection logic asynchronously to keep the UI smooth and responsive
        setTimeout(() => {
            lassoHighlightedItems = [];
            
            // Window selection always adds to the existing selection — never clears it

            // Iterate over all page wrappers inside panZoomContainer
            const pageWrappers = panZoomContainer.querySelectorAll('.page-wrapper');
            
            pageWrappers.forEach(wrapper => {
                const pageNum = parseInt(wrapper.dataset.page);
                const pageData = pagesData.get(pageNum);
                if (!pageData) return;

                // Get wrapper rect relative to panZoomContainer
                const wrapperLeft = wrapper.offsetLeft;
                const wrapperTop = wrapper.offsetTop;

                const pdfMinX = (minX - translateX) / scale - wrapperLeft;
                const pdfMaxX = (maxX - translateX) / scale - wrapperLeft;
                const pdfMinY = (minY - translateY) / scale - wrapperTop;
                const pdfMaxY = (maxY - translateY) / scale - wrapperTop;

                if (currentRendererSetting === 'canvas') {
                    const renderer = canvasRenderers.get(pageNum);
                    if (renderer) {
                        const queryRect = { minX: pdfMinX, maxX: pdfMaxX, minY: pdfMinY, maxY: pdfMaxY };
                        const matchedDrawings = renderer.queryRect(queryRect);
                        matchedDrawings.forEach(item => {
                            if (isItemInRect(item, pdfMinX, pdfMaxX, pdfMinY, pdfMaxY)) {
                                if (!selectedItems.has(item.globalId)) {
                                    selectedItems.set(item.globalId, item);
                                }
                            }
                        });
                    }
                } else {
                    pageData.drawings.forEach(item => {
                        if (isItemInRect(item, pdfMinX, pdfMaxX, pdfMinY, pdfMaxY)) {
                            const svgEl = document.getElementById(`vec-${item.globalId}`);
                            if (svgEl && !selectedItems.has(item.globalId)) {
                                selectedItems.set(item.globalId, item);
                                svgEl.classList.add('selected');
                            }
                        }
                    });
                }
            });
            
            // Update inspector UI exactly once after bulk updates
            updateInspector();
            if (currentRendererSetting === 'canvas') {
                refreshCanvasHighlights();
            } else {
                document.querySelectorAll('.vector-item.highlighted').forEach(el => {
                    const id = el.id.replace('vec-', '');
                    if (id !== highlightedItemId && !selectedItems.has(id)) {
                        el.classList.remove('highlighted');
                    }
                });
            }

            // Hide the processing spinner
            selectionSpinner.style.display = 'none';
        }, 50);
    }

    function isItemInRect(item, minX, maxX, minY, maxY) {
        let ix, iy, iw, ih;
        if (item.type === 'Line') {
            ix = Math.min(item.start[0], item.end[0]);
            iy = Math.min(item.start[1], item.end[1]);
            iw = Math.abs(item.start[0] - item.end[0]);
            ih = Math.abs(item.start[1] - item.end[1]);
        } else if (item.type === 'Rect') {
            ix = item.x; iy = item.y; iw = item.width; ih = item.height;
        } else if (item.type === 'Arc/Curve' || item.type === 'Polygon') {
            const xs = item.points.map(p => p[0]);
            const ys = item.points.map(p => p[1]);
            ix = Math.min(...xs); iy = Math.min(...ys);
            iw = Math.max(...xs) - ix; ih = Math.max(...ys) - iy;
        } else {
            return false;
        }
        
        return !(ix > maxX || (ix + iw) < minX || iy > maxY || (iy + ih) < minY);
    }

    // --- Inspector Updates ---
    function updateInspector() {
        selectionCount.textContent = selectedItems.size;
        const stateHasItems = selectedItems.size > 0;
        btnCopyInfo.disabled = !stateHasItems;
        btnSaveSelection.disabled = !stateHasItems;
        btnClearSelection.disabled = !stateHasItems;
        
        inspectorBody.innerHTML = '';
        const rawArray = [];
        
        let count = 0;
        selectedItems.forEach(item => {
            if (count < 100) {
                const tr = document.createElement('tr');
                const tdType = document.createElement('td'); tdType.textContent = item.type;
                const tdLen = document.createElement('td'); tdLen.textContent = item.length.toFixed(2);
                const tdW = document.createElement('td'); tdW.textContent = item.thickness.toFixed(2);
                
                const tdCoords = document.createElement('td');
                let coordsText = "";
                if (item.type === 'Line') {
                    coordsText = `(${item.start[0].toFixed(1)}, ${item.start[1].toFixed(1)}) → (${item.end[0].toFixed(1)}, ${item.end[1].toFixed(1)})`;
                } else if (item.type === 'Rect') {
                    coordsText = `(${item.x.toFixed(1)}, ${item.y.toFixed(1)}) → (${(item.x + item.width).toFixed(1)}, ${(item.y + item.height).toFixed(1)})`;
                } else if (item.type === 'Arc/Curve' || item.type === 'Polygon') {
                    if (item.points && item.points.length >= 2) {
                        const startPt = item.points[0];
                        const endPt = item.points[item.points.length - 1];
                        coordsText = `(${startPt[0].toFixed(1)}, ${startPt[1].toFixed(1)}) → (${endPt[0].toFixed(1)}, ${endPt[1].toFixed(1)})`;
                    } else {
                        coordsText = "-";
                    }
                } else {
                    coordsText = "-";
                }
                tdCoords.textContent = coordsText;
                
                const tdCol = document.createElement('td');
                const swatch = document.createElement('span');
                swatch.className = 'color-swatch';
                swatch.style.backgroundColor = item.color_hex || '#000';
                
                let colorText = "None";
                if (item.color) {
                    colorText = `(${item.color[0].toFixed(2)}, ${item.color[1].toFixed(2)}, ${item.color[2].toFixed(2)})`;
                }
                tdCol.appendChild(swatch);
                tdCol.appendChild(document.createTextNode(colorText));
                
                tr.appendChild(tdType); tr.appendChild(tdLen); tr.appendChild(tdW); tr.appendChild(tdCoords); tr.appendChild(tdCol);

                // Highlight and zoom to element on click
                if (highlightedItemId === item.globalId) {
                    tr.classList.add('active');
                }

                tr.addEventListener('click', async () => {
                    highlightedItemId = item.globalId;
                    if (currentRendererSetting === 'canvas') {
                        refreshCanvasHighlights();
                    }

                    // Clear previous highlights
                    document.querySelectorAll('.vector-item.highlighted').forEach(el => {
                        el.classList.remove('highlighted');
                    });
                    document.querySelectorAll('.inspector-table tbody tr.active').forEach(r => {
                        r.classList.remove('active');
                    });

                    // Mark current row as active
                    tr.classList.add('active');

                    // Switch page if in single page mode and on different page
                    if (layoutMode === 'single' && currentPage !== item.page) {
                        currentPage = item.page;
                        await reloadView();
                        await new Promise(resolve => requestAnimationFrame(resolve));
                    }

                    // Add highlight to current element
                    const svgEl = document.getElementById(`vec-${item.globalId}`);
                    if (svgEl) {
                        svgEl.classList.add('highlighted');
                        console.log(`[Inspector Click] Highlighted SVG element found: vec-${item.globalId}`, svgEl);
                    } else {
                        console.warn(`[Inspector Click] SVG element not found in DOM: vec-${item.globalId}`);
                    }

                    // Zoom to the element
                    zoomToItem(item);
                });

                inspectorBody.appendChild(tr);
                count++;
            }
            
            rawArray.push({
                page: item.page,
                type: item.type,
                length: item.length,
                thickness: item.thickness,
                color: item.color,
                color_hex: item.color_hex,
                coordinates: item.type === 'Line' ? {start: item.start, end: item.end} : 
                             item.type === 'Rect' ? {x: item.x, y: item.y, w: item.width, h: item.height} :
                             item.type === 'Arc/Curve' || item.type === 'Polygon' ? {points: item.points} : {}
            });
        });
        
        if (selectedItems.size > 100) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 5;
            td.style.textAlign = 'center';
            td.style.color = '#94a3b8';
            td.style.fontStyle = 'italic';
            td.style.padding = '8px';
            td.textContent = `... and ${selectedItems.size - 100} more items (copied to clipboard fully)`;
            tr.appendChild(td);
            inspectorBody.appendChild(tr);
        }
        
        window.currentInspectorRawArray = rawArray;
        if (rawArray.length > 100) {
            rawOutput.value = "JSON too large to display. Click 'Copy Info' to copy the full JSON to your clipboard.";
        } else {
            rawOutput.value = rawArray.length > 0 ? JSON.stringify(rawArray, null, 2) : "";
        }

        // Toggle sidebar visibility based on active selections
        const hasSelection = (selectedItems.size > 0) || (selectedStamps.size > 0) || (selectedPatterns.size > 0);
        toggleSidebarRight(hasSelection);
    }

    function toggleSidebarRight(show) {
        const isMobile = window.innerWidth <= 1024;
        if (isMobile) {
            if (show) {
                sidebarRight.classList.add('open');
                if (sidebarBackdrop) sidebarBackdrop.classList.add('active');
            } else {
                sidebarRight.classList.remove('open');
                if (sidebarBackdrop) sidebarBackdrop.classList.remove('active');
            }
            sidebarRight.style.display = '';
        } else {
            sidebarRight.style.display = show ? 'flex' : 'none';
            sidebarRight.classList.remove('open');
            if (sidebarBackdrop) sidebarBackdrop.classList.remove('active');
        }
        updateStampsModeVisibility();
    }

    function updateStampsModeVisibility() {
        const isMobile = window.innerWidth <= 1024;
        const isVisible = isMobile ? sidebarRight.classList.contains('open') : sidebarRight.style.display !== 'none';
        const isStampsActive = document.getElementById('panel-stamps').classList.contains('active');
        
        if (isVisible && isStampsActive) {
            document.body.classList.add('stamps-mode-active');
        } else {
            document.body.classList.remove('stamps-mode-active');
        }
    }

    function getStampHyperlink(stamp) {
        const pageNum = stamp.page_num;
        const pageData = pagesData.get(pageNum);
        if (!pageData || !pageData.links || pageData.links.length === 0) return null;
        
        const sX0 = stamp.rect[0];
        const sY0 = stamp.rect[1];
        const sX1 = stamp.rect[2];
        const sY1 = stamp.rect[3];
        
        for (const link of pageData.links) {
            const lX0 = link.x;
            const lY0 = link.y;
            const lX1 = link.x + link.width;
            const lY1 = link.y + link.height;
            
            const overlapX = Math.max(0, Math.min(sX1, lX1) - Math.max(sX0, lX0));
            const overlapY = Math.max(0, Math.min(sY1, lY1) - Math.max(sY0, lY0));
            const overlapArea = overlapX * overlapY;
            
            if (overlapArea > 0) {
                return link.uri;
            }
        }
        return null;
    }

    btnCopyInfo.addEventListener('click', () => {
        const rawArray = window.currentInspectorRawArray || [];
        if (rawArray.length === 0) return;
        const jsonText = JSON.stringify(rawArray, null, 2);
        
        function finalizeCopy() {
            const originalText = btnCopyInfo.textContent;
            btnCopyInfo.textContent = "Copied!";
            setTimeout(() => { btnCopyInfo.textContent = originalText; }, 2000);
        }
        
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(jsonText).then(finalizeCopy).catch(err => {
                fallbackCopy(jsonText, finalizeCopy);
            });
        } else {
            fallbackCopy(jsonText, finalizeCopy);
        }
    });

    function fallbackCopy(text, callback) {
        const tempTextArea = document.createElement("textarea");
        tempTextArea.value = text;
        tempTextArea.style.position = "absolute";
        tempTextArea.style.left = "-9999px";
        document.body.appendChild(tempTextArea);
        tempTextArea.select();
        try {
            document.execCommand('copy');
        } catch (e) {}
        document.body.removeChild(tempTextArea);
        if (callback) callback();
    }

    window.reloadStampsAndPage = async function(pageNum) {
        try {
            const stampsRes = await fetch(`/api/pdf/${encodeURIComponent(currentPdf)}/stamps`);
            if (stampsRes.ok) {
                currentPdfStamps = await stampsRes.json();
                renderStampsList();
            }
            
            pdfCacheBuster = Date.now();
            const wrapper = document.getElementById(`page-wrapper-${pageNum}`);
            if (wrapper) {
                const img = wrapper.querySelector('.pdf-image');
                if (img && wrapper.dataset.loaded === 'true') {
                    img.src = `/api/pdf/${encodeURIComponent(currentPdf)}/page/${pageNum}/image?scale=2&t=${pdfCacheBuster}`;
                    img.dataset.loadedScale = 2;
                }
                const hiResImg = wrapper.querySelector('.pdf-image-hires');
                if (hiResImg) hiResImg.style.display = 'none';
                
                const svg = wrapper.querySelector('.vector-overlay');
                if (svg) {
                    overlayStampRects(pageNum, svg);
                }
            }
        } catch (err) {
            console.error("Error auto-reloading stamps:", err);
        }
    };

    window.addEventListener('resize', () => {
        // Avoid auto-resetting layout completely on tiny resize
        updateTransform();
    });

    // Spacebar Modifier for Panning in Selection Mode
    window.addEventListener('keydown', (e) => {
        const activeTag = document.activeElement ? document.activeElement.tagName : '';
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
            if (activeTag !== 'INPUT' && activeTag !== 'TEXTAREA' && activeTag !== 'SELECT') {
                e.preventDefault();
                undoPatternScan();
                return;
            }
        }

        if (e.code === 'Space') {
            if (activeTag !== 'INPUT' && activeTag !== 'TEXTAREA') {
                e.preventDefault();
                if (!isSpacePressed) {
                    isSpacePressed = true;
                    if (selectionMode) {
                        viewerContainer.style.cursor = 'grab';
                    }
                }
            }
        }
    });

    window.addEventListener('keyup', (e) => {
        if (e.code === 'Space') {
            isSpacePressed = false;
            if (selectionMode) {
                viewerContainer.style.cursor = 'crosshair';
            } else {
                viewerContainer.style.cursor = 'grab';
            }
        }
    });

    window.addEventListener('blur', () => {
        isSpacePressed = false;
        if (selectionMode) {
            viewerContainer.style.cursor = 'crosshair';
        } else {
            viewerContainer.style.cursor = 'grab';
        }
    });

    // --- Coordinates Tracking Logic ---
    btnToggleCoords.addEventListener('click', () => {
        showCoordsMode = !showCoordsMode;
        if (showCoordsMode) {
            btnToggleCoords.textContent = "Show Coordinates: ON";
            btnToggleCoords.classList.add('active');
            coordsOverlay.style.display = 'flex';
        } else {
            btnToggleCoords.textContent = "Show Coordinates: OFF";
            btnToggleCoords.classList.remove('active');
            coordsOverlay.style.display = 'none';
            coordsTooltip.style.display = 'none';
        }
    });

    // --- Thin Lines Toggle ---
    let thinLinesMode = false;
    btnToggleThinLines.addEventListener('click', () => {
        thinLinesMode = !thinLinesMode;
        if (thinLinesMode) {
            btnToggleThinLines.textContent = "Thin Lines: ON";
            btnToggleThinLines.classList.add('active');
            viewerContainer.classList.add('thin-lines');
        } else {
            btnToggleThinLines.textContent = "Thin Lines: OFF";
            btnToggleThinLines.classList.remove('active');
            viewerContainer.classList.remove('thin-lines');
        }
    });

    // --- Vector Layer Toggle ---
    if (btnToggleSvgLayer) {
        btnToggleSvgLayer.addEventListener('click', () => {
            showVectors = !showVectors;
            if (showVectors) {
                btnToggleSvgLayer.textContent = "Vectors: ON";
                btnToggleSvgLayer.classList.remove('active');
            } else {
                btnToggleSvgLayer.textContent = "Vectors: OFF";
                btnToggleSvgLayer.classList.add('active');
            }
            // Reload the view so the vectors are added or removed
            if (currentPdf) {
                reloadView();
            }
        });
    }

    // --- Revit-Style Tab Key Navigation ---
    let tabCycleCandidates = []; // Array of candidate objects
    let tabCycleIndex = -1;
    let lastTabMousePos = null;

    function clearTabState() {
        tabCycleCandidates.forEach(c => {
            if (c.items) {
                c.items.forEach(hitTarget => {
                    if (hitTarget && hitTarget.nextElementSibling) {
                        hitTarget.nextElementSibling.classList.remove('tab-preview-highlight');
                    }
                    if (hitTarget && typeof hitTarget.classList !== 'undefined') {
                        hitTarget.classList.remove('tab-preview-highlight');
                    }
                });
            }
        });
        viewerContainer.classList.remove('tab-active');
        tabCycleCandidates = [];
        tabCycleIndex = -1;
        lastTabMousePos = null;
        if (currentRendererSetting === 'canvas') {
            refreshCanvasHighlights();
        }
    }

    // Helper to find connected chains
    function findConnectedChain(seedItemData, allItemNodes) {
        const chainNodes = new Set();
        const stack = [seedItemData];
        const seedGlobalId = seedItemData.globalId;
        
        const nodeMap = new Map();
        const dataMap = new Map();
        allItemNodes.forEach(node => {
            if (node._itemData) {
                nodeMap.set(node._itemData.globalId, node);
                dataMap.set(node._itemData.globalId, node._itemData);
            } else if (node.globalId) {
                nodeMap.set(node.globalId, node);
                dataMap.set(node.globalId, node);
            }
        });

        const seedNode = nodeMap.get(seedGlobalId);
        if (seedNode) chainNodes.add(seedNode);

        const visitedIds = new Set([seedGlobalId]);

        const seedColor = seedItemData.color_hex;
        const seedThickness = seedItemData.thickness;
        
        function isCompatible(item) {
            if (!item) return false;
            const c1 = (seedColor || '').toLowerCase();
            const c2 = (item.color_hex || '').toLowerCase();
            if (c1 !== c2) return false;
            
            const t1 = seedThickness || 0;
            const t2 = item.thickness || 0;
            if (Math.abs(t1 - t2) >= 0.05) return false;
            
            return true;
        }

        function getEndpoints(item) {
            if (!item) return [];
            if (item.type === 'Line') {
                if (!item.start || !item.end) return [];
                return [item.start, item.end];
            }
            if (item.type === 'Rect') {
                if (typeof item.x !== 'number' || typeof item.y !== 'number' || typeof item.width !== 'number' || typeof item.height !== 'number') return [];
                return [[item.x, item.y], [item.x+item.width, item.y], [item.x+item.width, item.y+item.height], [item.x, item.y+item.height]];
            }
            if (item.type === 'Polygon') {
                if (!item.points) return [];
                return item.points;
            }
            if (item.type === 'Arc/Curve') {
                if (!item.points || item.points.length < 4) return [];
                return [item.points[0], item.points[3]];
            }
            return [];
        }

        const TOLERANCE = 0.08; // Tighter tolerance to prevent bridging parallel lines
        function arePointsClose(p1, p2) {
            if (!p1 || !p2) return false;
            return Math.hypot(p1[0]-p2[0], p1[1]-p2[1]) <= TOLERANCE;
        }

        // Distance from point p to line segment (v, w)
        function distToSegment(p, v, w) {
            if (!p || !v || !w) return Infinity;
            const l2 = (w[0] - v[0])**2 + (w[1] - v[1])**2;
            if (l2 === 0) return Math.hypot(p[0] - v[0], p[1] - v[1]);
            let t = ((p[0] - v[0]) * (w[0] - v[0]) + (p[1] - v[1]) * (w[1] - v[1])) / l2;
            t = Math.max(0, Math.min(1, t));
            const proj = [v[0] + t * (w[0] - v[0]), v[1] + t * (w[1] - v[1])];
            return Math.hypot(p[0] - proj[0], p[1] - proj[1]);
        }
        
        function isPointCloseToItem(p, item) {
            if (!p || !item) return false;
            if (item.type === 'Line') {
                if (!item.start || !item.end) return false;
                return distToSegment(p, item.start, item.end) <= TOLERANCE;
            } else if (item.type === 'Rect') {
                if (typeof item.x !== 'number' || typeof item.y !== 'number' || typeof item.width !== 'number' || typeof item.height !== 'number') return false;
                const pts = [[item.x, item.y], [item.x+item.width, item.y], [item.x+item.width, item.y+item.height], [item.x, item.y+item.height]];
                for (let i=0; i<4; i++) {
                    if (distToSegment(p, pts[i], pts[(i+1)%4]) <= TOLERANCE) return true;
                }
                return false;
            } else if (item.type === 'Polygon') {
                if (!item.points || item.points.length < 3) return false;
                const pts = item.points;
                const len = pts.length;
                for (let i = 0; i < len; i++) {
                    if (distToSegment(p, pts[i], pts[(i + 1) % len]) <= TOLERANCE) return true;
                }
                return false;
            } else if (item.type === 'Arc/Curve') {
                if (!item.points || item.points.length < 4) return false;
                return arePointsClose(p, item.points[0]) || arePointsClose(p, item.points[3]);
            }
            return false;
        }

        // Partition items into a spatial grid to optimize search performance from O(N^2) to O(N)
        const CELL_SIZE = 100;
        const grid = new Map();
        const largeItems = [];
        
        function getCellKeys(item) {
            if (!item) return [];
            let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
            if (item.type === 'Line') {
                if (!item.start || !item.end) return [];
                minX = Math.min(item.start[0], item.end[0]);
                maxX = Math.max(item.start[0], item.end[0]);
                minY = Math.min(item.start[1], item.end[1]);
                maxY = Math.max(item.start[1], item.end[1]);
            } else if (item.type === 'Rect') {
                if (typeof item.x !== 'number' || typeof item.y !== 'number' || typeof item.width !== 'number' || typeof item.height !== 'number') return [];
                minX = item.x;
                maxX = item.x + item.width;
                minY = item.y;
                maxY = item.y + item.height;
            } else if (item.type === 'Polygon') {
                if (!item.points) return [];
                const xs = item.points.map(p => p ? p[0] : 0);
                const ys = item.points.map(p => p ? p[1] : 0);
                minX = Math.min(...xs);
                maxX = Math.max(...xs);
                minY = Math.min(...ys);
                maxY = Math.max(...ys);
            } else if (item.type === 'Arc/Curve') {
                if (!item.points || item.points.length < 4) return [];
                const xs = item.points.map(p => p ? p[0] : 0);
                const ys = item.points.map(p => p ? p[1] : 0);
                minX = Math.min(...xs);
                maxX = Math.max(...xs);
                minY = Math.min(...ys);
                maxY = Math.max(...ys);
            } else {
                return [];
            }
            
            minX -= TOLERANCE; maxX += TOLERANCE;
            minY -= TOLERANCE; maxY += TOLERANCE;
            
            const startCol = Math.floor(minX / CELL_SIZE);
            const endCol = Math.floor(maxX / CELL_SIZE);
            const startRow = Math.floor(minY / CELL_SIZE);
            const endRow = Math.floor(maxY / CELL_SIZE);

            if (isNaN(startCol) || isNaN(endCol) || isNaN(startRow) || isNaN(endRow) ||
                (endCol - startCol) > 8 || (endRow - startRow) > 8) {
                return null; // Signals this is a large/global item
            }
            
            const keys = [];
            for (let c = startCol; c <= endCol; c++) {
                for (let r = startRow; r <= endRow; r++) {
                    keys.push(`${c},${r}`);
                }
            }
            return keys;
        }

        for (const [globalId, itemData] of dataMap.entries()) {
            const keys = getCellKeys(itemData);
            if (keys === null) {
                largeItems.push({ globalId, itemData });
            } else {
                keys.forEach(key => {
                    if (!grid.has(key)) {
                        grid.set(key, []);
                    }
                    grid.get(key).push({ globalId, itemData });
                });
            }
        }

        // Helper to count connection degree and avoid layout borders or grid lines with 8+ connections
        function getTouchCount(item, maxCount = 8) {
            const pts = getEndpoints(item);
            if (pts.length === 0) return 0;
            
            const touchedIds = new Set();
            for (const pt of pts) {
                if (!pt) continue;
                const col = Math.floor(pt[0] / CELL_SIZE);
                const row = Math.floor(pt[1] / CELL_SIZE);
                
                for (let dc = -1; dc <= 1; dc++) {
                    for (let dr = -1; dr <= 1; dr++) {
                        const key = `${col + dc},${row + dr}`;
                        const cellItems = grid.get(key);
                        if (cellItems) {
                            for (const entry of cellItems) {
                                if (entry.globalId === item.globalId || touchedIds.has(entry.globalId)) continue;
                                
                                let connected = false;
                                const itemPts = getEndpoints(entry.itemData);
                                
                                for (const p1 of pts) {
                                    if (isPointCloseToItem(p1, entry.itemData)) {
                                        connected = true;
                                        break;
                                    }
                                }
                                if (!connected) {
                                    for (const p2 of itemPts) {
                                        if (isPointCloseToItem(p2, item)) {
                                            connected = true;
                                            break;
                                        }
                                    }
                                }
                                
                                if (connected) {
                                    touchedIds.add(entry.globalId);
                                    if (touchedIds.size >= maxCount) {
                                        return touchedIds.size;
                                    }
                                }
                            }
                        }
                    }
                }
            }
            return touchedIds.size;
        }

        // If the seed item itself has too many connections, it's a grid/border/background line; do not traverse
        if (getTouchCount(seedItemData, 8) >= 8) {
            return Array.from(chainNodes);
        }

        while(stack.length > 0) {
            const current = stack.pop();
            const currentPts = getEndpoints(current);
            if (currentPts.length === 0) continue;
            
            const candidateIds = new Set();
            for (const pt of currentPts) {
                if (!pt) continue;
                const col = Math.floor(pt[0] / CELL_SIZE);
                const row = Math.floor(pt[1] / CELL_SIZE);
                
                for (let dc = -1; dc <= 1; dc++) {
                    for (let dr = -1; dr <= 1; dr++) {
                        const key = `${col + dc},${row + dr}`;
                        const cellItems = grid.get(key);
                        if (cellItems) {
                            for (const entry of cellItems) {
                                if (!visitedIds.has(entry.globalId)) {
                                    candidateIds.add(entry.globalId);
                                }
                            }
                        }
                    }
                }
            }

            for (const globalId of candidateIds) {
                const itemData = dataMap.get(globalId);
                if (!itemData) continue;
                if (!isCompatible(itemData)) continue;
                let connected = false;
                
                // 1. Check if any endpoint of 'current' touches 'itemData'
                for (const p1 of currentPts) {
                    if (isPointCloseToItem(p1, itemData)) {
                        connected = true;
                        break;
                    }
                }
                
                // 2. Check if any endpoint of 'itemData' touches 'current'
                if (!connected) {
                    const itemPts = getEndpoints(itemData);
                    for (const p2 of itemPts) {
                        if (isPointCloseToItem(p2, current)) {
                            connected = true;
                            break;
                        }
                    }
                }
                
                if (connected) {
                    // Exclude candidate if it has 8 or more connections (grid/border/layout element)
                    if (getTouchCount(itemData, 8) >= 8) {
                        visitedIds.add(globalId); // mark visited so we don't check again
                        continue;
                    }

                    visitedIds.add(globalId);
                    const node = nodeMap.get(globalId);
                    if (node) chainNodes.add(node);
                    if (chainNodes.size >= 1000) {
                        stack.length = 0; // Clear stack to stop BFS traversal
                        break;
                    }
                    stack.push(itemData);
                }
            }
        }
        return Array.from(chainNodes);
    }

    function handleTabNavigation(isShift) {
        if (!lastMouseEvent) return;
        const mouseX = lastMouseEvent.clientX;
        const mouseY = lastMouseEvent.clientY;

        // If mouse moved more than 20px, reset candidates
        if (!lastTabMousePos || Math.hypot(lastTabMousePos.x - mouseX, lastTabMousePos.y - mouseY) > 20) {
            clearTabState();
            lastTabMousePos = { x: mouseX, y: mouseY };

            let singleHits = [];
            let allPageNodes = [];
            
            if (currentRendererSetting === 'canvas') {
                const containerRect = panZoomContainer.getBoundingClientRect();
                const pdfX = (mouseX - containerRect.left) / scale;
                const pdfY = (mouseY - containerRect.top) / scale;
                
                const pageRects = getPageRects();
                let hoveredWrapper = null;
                let relativeX = 0;
                let relativeY = 0;
                
                for (const pr of pageRects) {
                    if (
                        pdfX >= pr.offsetLeft && pdfX <= pr.offsetLeft + pr.offsetWidth &&
                        pdfY >= pr.offsetTop && pdfY <= pr.offsetTop + pr.offsetHeight
                    ) {
                        hoveredWrapper = pr.wrapper;
                        relativeX = pdfX - pr.offsetLeft;
                        relativeY = pdfY - pr.offsetTop;
                        break;
                    }
                }
                
                if (hoveredWrapper) {
                    const pageNum = parseInt(hoveredWrapper.dataset.page);
                    const renderer = canvasRenderers.get(pageNum);
                    if (renderer) {
                        const hoveredEls = document.elementsFromPoint(mouseX, mouseY);
                        hoveredEls.forEach(el => {
                            if (el.classList.contains('stamp-highlight-rect')) {
                                singleHits.push({ type: 'stamp', node: el });
                            } else if (el.classList.contains('pattern-highlight-rect')) {
                                singleHits.push({ type: 'pattern', node: el });
                            }
                        });
                        const matchedItems = renderer.queryPointAll(relativeX, relativeY, 8);
                        matchedItems.forEach(matched => {
                            singleHits.push({ type: 'vector', node: null, data: matched });
                        });
                        
                        if (pagesData.get(pageNum)) {
                            allPageNodes = pagesData.get(pageNum).drawings;
                        }
                    }
                }
            } else {
                const hoveredEls = document.elementsFromPoint(mouseX, mouseY);
                hoveredEls.forEach(el => {
                    if (el.classList.contains('vector-item-hit-target')) {
                        singleHits.push({ type: 'vector', node: el, data: el._itemData });
                    } else if (el.classList.contains('stamp-highlight-rect')) {
                        singleHits.push({ type: 'stamp', node: el });
                    } else if (el.classList.contains('pattern-highlight-rect')) {
                        singleHits.push({ type: 'pattern', node: el });
                    }
                });
            }

            if (singleHits.length === 0) return;

            let pageSvg;
            if (currentRendererSetting !== 'canvas') {
                pageSvg = singleHits[0].node.closest('svg.vector-overlay');
                allPageNodes = pageSvg ? Array.from(pageSvg.querySelectorAll('.vector-item-hit-target')) : [];
            }

            singleHits.forEach((hit, index) => {
                let isSelected = false;
                if (hit.type === 'vector' && hit.data && selectedItems.has(hit.data.globalId)) {
                    isSelected = true;
                } else if (hit.type === 'stamp' && selectedStamps.has(parseInt(hit.node.dataset.xref))) {
                    isSelected = true;
                }

                // Only add the chain candidate for the closest vector item (index 0) to avoid distant chains
                if (index === 0 && hit.type === 'vector' && allPageNodes.length > 0) {
                    const chainNodes = findConnectedChain(hit.data, allPageNodes);
                    // Only offer the chain candidate if it contains at least one UNSELECTED item, and has more than 1 item total.
                    const unselectedCount = chainNodes.filter(n => {
                        const id = n._itemData ? n._itemData.globalId : n.globalId;
                        return !selectedItems.has(id);
                    }).length;
                    
                    if (chainNodes.length > 1 && unselectedCount > 0) {
                        tabCycleCandidates.push({
                            type: 'chain',
                            items: chainNodes,
                            originalData: hit
                        });
                    }
                }

                if (!isSelected) {
                    tabCycleCandidates.push({
                        type: 'single',
                        items: [currentRendererSetting === 'canvas' ? hit.data : hit.node],
                        originalData: hit
                    });
                }
            });
        }

        if (tabCycleCandidates.length === 0) return;
        
        // Remove regular hover highlights when tab cycling
        document.querySelectorAll('.vector-item.highlighted').forEach(el => el.classList.remove('highlighted'));
        viewerContainer.classList.add('tab-active');

        // Remove highlight from previous safely
        if (tabCycleIndex >= 0 && tabCycleIndex < tabCycleCandidates.length) {
            tabCycleCandidates[tabCycleIndex].items.forEach(hitTarget => {
                if (hitTarget) {
                    if (hitTarget.nextElementSibling && hitTarget.nextElementSibling.classList) {
                        hitTarget.nextElementSibling.classList.remove('tab-preview-highlight');
                    }
                    if (hitTarget.classList) {
                        hitTarget.classList.remove('tab-preview-highlight');
                    }
                }
            });
        }

        if (isShift) {
            tabCycleIndex = (tabCycleIndex - 1 + tabCycleCandidates.length) % tabCycleCandidates.length;
        } else {
            tabCycleIndex = (tabCycleIndex + 1) % tabCycleCandidates.length;
        }

        if (currentRendererSetting === 'canvas') {
            refreshCanvasHighlights();
            return;
        }

        // Apply highlight to new safely
        tabCycleCandidates[tabCycleIndex].items.forEach(hitTarget => {
            if (hitTarget && hitTarget.classList) {
                if (hitTarget.classList.contains('vector-item-hit-target')) {
                    if (hitTarget.nextElementSibling && hitTarget.nextElementSibling.classList) {
                        hitTarget.nextElementSibling.classList.add('tab-preview-highlight');
                    }
                } else {
                    hitTarget.classList.add('tab-preview-highlight');
                }
            }
        });
    }

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
            if (selectionMode) {
                e.preventDefault();
                handleTabNavigation(e.shiftKey);
            }
        }
    });

    window.addEventListener('mousemove', (e) => {
        if (lastTabMousePos && Math.hypot(lastTabMousePos.x - e.clientX, lastTabMousePos.y - e.clientY) > 20) {
            clearTabState();
        }
    });

    coordsOverlay.addEventListener('click', () => {
        if (coordsUnit === 'pt') {
            coordsUnit = 'in';
        } else if (coordsUnit === 'in') {
            coordsUnit = 'mm';
        } else {
            coordsUnit = 'pt';
        }
        if (lastMouseEvent) {
            updateCoordsFromMouseEvent(lastMouseEvent);
        }
    });

    viewerContainer.addEventListener('mouseleave', () => {
        coordsTooltip.style.display = 'none';
    });

    let cachedPageRects = null;

    function getPageRects() {
        if (cachedPageRects) return cachedPageRects;
        cachedPageRects = [];
        const pageWrappers = panZoomContainer.querySelectorAll('.page-wrapper');
        for (const wrapper of pageWrappers) {
            cachedPageRects.push({
                wrapper: wrapper,
                pageNum: wrapper.dataset.page,
                offsetLeft: wrapper.offsetLeft,
                offsetTop: wrapper.offsetTop,
                offsetWidth: wrapper.offsetWidth,
                offsetHeight: wrapper.offsetHeight
            });
        }
        return cachedPageRects;
    }

    // Call this whenever pages change
    function invalidatePageRects() {
        cachedPageRects = null;
    }

    function updateCoordsFromMouseEvent(e) {
        if (!showCoordsMode) return;
        
        const containerRect = panZoomContainer.getBoundingClientRect();
        const mouseX = (e.clientX - containerRect.left) / scale;
        const mouseY = (e.clientY - containerRect.top) / scale;
        
        const pageRects = getPageRects();
        let hoveredWrapper = null;
        let relativeX = 0;
        let relativeY = 0;
        
        for (const pr of pageRects) {
            if (
                mouseX >= pr.offsetLeft && mouseX <= pr.offsetLeft + pr.offsetWidth &&
                mouseY >= pr.offsetTop && mouseY <= pr.offsetTop + pr.offsetHeight
            ) {
                hoveredWrapper = pr.wrapper;
                relativeX = mouseX - pr.offsetLeft;
                relativeY = mouseY - pr.offsetTop;
                break;
            }
        }
        
        if (hoveredWrapper) {
            const pageNum = hoveredWrapper.dataset.page;
            
            let xVal = relativeX;
            let yVal = relativeY;
            let unitStr = 'pt';
            
            if (coordsUnit === 'in') {
                xVal = relativeX / 72;
                yVal = relativeY / 72;
                unitStr = 'in';
            } else if (coordsUnit === 'mm') {
                xVal = relativeX * 0.352778;
                yVal = relativeY * 0.352778;
                unitStr = 'mm';
            }
            
            const decimals = coordsUnit === 'pt' ? 1 : 3;
            const xStr = xVal.toFixed(decimals);
            const yStr = yVal.toFixed(decimals);
            
            coordsVal.textContent = `${xStr}, ${yStr} ${unitStr}`;
            coordsPage.textContent = `Page ${pageNum}`;
            coordsPage.style.display = 'inline-block';
            
            // Position and show Tooltip relative to viewer container
            const viewerRect = viewerContainer.getBoundingClientRect();
            const tooltipX = e.clientX - viewerRect.left;
            const tooltipY = e.clientY - viewerRect.top;
            
            coordsTooltip.textContent = `${xStr}, ${yStr} ${unitStr}`;
            coordsTooltip.style.left = `${tooltipX}px`;
            coordsTooltip.style.top = `${tooltipY}px`;
            coordsTooltip.style.display = 'block';
        } else {
            coordsVal.textContent = "-";
            coordsPage.style.display = 'none';
            coordsTooltip.style.display = 'none';
        }
    }

    // --- Sidebar Drawer Listeners ---
    if (btnToggleSidebarLeft) {
        btnToggleSidebarLeft.addEventListener('click', () => {
            const isMobile = window.innerWidth <= 1024;
            if (isMobile) {
                sidebarLeft.classList.toggle('open');
                sidebarRight.classList.remove('open'); // Close other drawer
                updateBackdrop();
            } else {
                if (sidebarLeft.style.display === 'none') {
                    sidebarLeft.style.display = 'flex';
                } else {
                    sidebarLeft.style.display = 'none';
                }
            }
        });
    }

    if (btnToggleSidebarRight) {
        btnToggleSidebarRight.addEventListener('click', () => {
            const isMobile = window.innerWidth <= 1024;
            if (isMobile) {
                sidebarRight.classList.toggle('open');
                sidebarLeft.classList.remove('open'); // Close other drawer
                updateBackdrop();
            } else {
                const isVisible = sidebarRight.style.display !== 'none';
                toggleSidebarRight(!isVisible);
            }
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', () => {
            sidebarLeft.classList.remove('open');
            sidebarRight.classList.remove('open');
            updateBackdrop();
        });
    }

    function updateBackdrop() {
        if (sidebarLeft.classList.contains('open') || sidebarRight.classList.contains('open')) {
            sidebarBackdrop.classList.add('active');
        } else {
            sidebarBackdrop.classList.remove('active');
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}
