function initManageTags() {
    const btnManageTags = document.getElementById('btn-manage-tags');
    const panel = document.getElementById('manage-tags-panel');
    const header = document.getElementById('manage-tags-header');
    const btnClose = document.getElementById('btn-close-manage-tags');

    if (!btnManageTags || !panel) return;

    let projectFieldsData = { fields: [], fields_data: {}, patterns: [], system_patterns: [] };

    // Toggle panel
    btnManageTags.addEventListener('click', async () => {
        if (panel.style.display === 'none' || !panel.style.display) {
            panel.style.display = 'flex';
            await loadProjectFieldsData();
            loadTagsConfig();
        } else {
            panel.style.display = 'none';
        }
    });

    btnClose.addEventListener('click', () => {
        panel.style.display = 'none';
    });
    
    async function loadProjectFieldsData() {
        const projectName = window.currentProject || getProjectNameFromUrl();
        if (!projectName) return;
        try {
            const res = await fetch(`/api/projects/${encodeURIComponent(projectName)}/fields_data`);
            const data = await res.json();
            if (data.success) {
                projectFieldsData = {
                    fields: data.fields || [],
                    fields_data: data.fields_data || {},
                    patterns: data.patterns || [],
                    system_patterns: data.system_patterns || []
                };
            }
        } catch (e) {
            console.error("Error fetching project fields data:", e);
        }
    }

    // Make panel draggable
    let isDragging = false;
    let offsetX, offsetY;

    header.addEventListener('mousedown', (e) => {
        isDragging = true;
        offsetX = e.clientX - panel.offsetLeft;
        offsetY = e.clientY - panel.offsetTop;
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        panel.style.left = `${e.clientX - offsetX}px`;
        panel.style.top = `${e.clientY - offsetY}px`;
        panel.style.right = 'auto'; // Reset right so left works
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
        document.body.style.userSelect = '';
    });

    header.addEventListener('touchstart', (e) => {
        isDragging = true;
        offsetX = e.touches[0].clientX - panel.offsetLeft;
        offsetY = e.touches[0].clientY - panel.offsetTop;
        document.body.style.userSelect = 'none';
    }, {passive: true});

    document.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        panel.style.left = `${e.touches[0].clientX - offsetX}px`;
        panel.style.top = `${e.touches[0].clientY - offsetY}px`;
        panel.style.right = 'auto'; // Reset right so left works
    }, {passive: true});

    document.addEventListener('touchend', () => {
        isDragging = false;
        document.body.style.userSelect = '';
    });

    // Close on outside click
    document.addEventListener('mousedown', (e) => {
        if (panel.style.display !== 'none' && !panel.contains(e.target) && !btnManageTags.contains(e.target)) {
            // Ignore if clicking on dropdowns
            if (!e.target.closest('.val-dropdown-list') && !e.target.closest('.field-dropdown-list') && !e.target.closest('.shape-dropdown-menu')) {
                panel.style.display = 'none';
            }
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && panel.style.display !== 'none') {
            panel.style.display = 'none';
        }
    });

    // Upload Samples
    const fileInput = document.getElementById('stamp-sample-upload');
    const btnUpload = document.getElementById('btn-trigger-stamp-upload');
    const uploadStatus = document.getElementById('stamp-upload-status');
    const uploadedList = document.getElementById('uploaded-stamps-list');

    btnUpload.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', async (e) => {
        const files = e.target.files;
        if (!files.length) return;
        
        // Find current project name from somewhere (maybe URL or window.currentProject)
        const projectName = window.currentProject || getProjectNameFromUrl();
        if (!projectName) {
            alert('Please select a project first.');
            return;
        }

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files[]', files[i]);
        }
        formData.append('project', projectName);

        uploadStatus.textContent = 'Uploading...';
        
        try {
            const res = await fetch('/api/manage_tags/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                uploadStatus.textContent = `${files.length} file(s) uploaded.`;
                loadTagsConfig(); // Refresh list
            } else {
                uploadStatus.textContent = 'Upload failed: ' + data.error;
            }
        } catch (err) {
            console.error(err);
            uploadStatus.textContent = 'Upload error.';
        }
    });

    // Rules Editor
    const btnAddShapeRule = document.getElementById('btn-add-shape-rule');
    const btnAddColorRule = document.getElementById('btn-add-color-rule');
    const shapeRulesContainer = document.getElementById('shape-rules-container');
    const colorRulesContainer = document.getElementById('color-rules-container');
    const btnSaveConfig = document.getElementById('btn-save-tags-config');
    
    let tagsConfig = {
        uploadedStamps: [],
        rules: [],
        hoverFields: []
    };
    
    let globalTargets = [];

    // Fetch targets for dropdown
    fetch('/api/config')
        .then(res => res.json())
        .then(data => {
            if (data && data.targets) {
                globalTargets = data.targets;
            }
        })
        .catch(err => console.error("Error fetching config for targets:", err));

    btnAddShapeRule.addEventListener('click', () => {
        addRuleRow({ type: 'shape', field: '', operator: '==', value: '', result: '' });
    });

    btnAddColorRule.addEventListener('click', () => {
        addRuleRow({ type: 'color', field: '', operator: '==', value: '', result: '' });
    });

    function addRuleRow(rule) {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.gap = '6px';
        row.style.alignItems = 'center';
        row.style.background = 'var(--modal-input-bg)';
        row.style.border = '1px solid var(--border-color)';
        row.style.padding = '4px 6px';
        row.style.borderRadius = '4px';
        row.style.fontSize = '0.85rem';
        row.className = 'tag-rule-row';

        // Create elements manually to handle dynamic dropdowns
        const spanIf = document.createElement('span');
        spanIf.textContent = 'IF';
        spanIf.style.fontWeight = 'bold';
        
        const fieldContainer = document.createElement('div');
        fieldContainer.style.position = 'relative';
        
        const fieldInput = document.createElement('input');
        fieldInput.type = 'text';
        fieldInput.className = 'rule-field rule-input';
        fieldInput.value = rule.field || 'Target';
        fieldInput.style.padding = '4px 8px';
        fieldInput.style.borderRadius = '4px';
        fieldInput.style.border = '1px solid var(--border-color)';
        fieldInput.style.background = 'var(--modal-input-bg)';
        fieldInput.style.color = 'var(--text-primary)';
        fieldInput.style.width = '120px';
        fieldInput.autocomplete = 'off';
        
        const fieldDropdownList = document.createElement('div');
        fieldDropdownList.className = 'field-dropdown-list';
        fieldDropdownList.style.position = 'absolute';
        fieldDropdownList.style.top = '100%';
        fieldDropdownList.style.left = '0';
        fieldDropdownList.style.width = '100%';
        fieldDropdownList.style.maxHeight = '150px';
        fieldDropdownList.style.overflowY = 'auto';
        fieldDropdownList.style.background = 'var(--modal-bg)';
        fieldDropdownList.style.border = '1px solid var(--border-color)';
        fieldDropdownList.style.borderRadius = '4px';
        fieldDropdownList.style.zIndex = '1000';
        fieldDropdownList.style.display = 'none';
        fieldDropdownList.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';
        
        fieldContainer.appendChild(fieldInput);
        fieldContainer.appendChild(fieldDropdownList);
        
        const getFieldOptions = () => {
            let opts = ['Target', 'Type', 'Pattern', 'System'];
            opts = opts.concat(projectFieldsData.fields);
            return opts;
        };
        
        const renderFieldList = (filterText = '') => {
            fieldDropdownList.innerHTML = '';
            const lowerFilter = filterText.toLowerCase();
            const opts = getFieldOptions();
            const filtered = opts.filter(t => t.toLowerCase().includes(lowerFilter));
            
            if (filtered.length === 0) {
                fieldDropdownList.style.display = 'none';
                return;
            }
            
            filtered.forEach(t => {
                const item = document.createElement('div');
                item.textContent = t;
                item.style.padding = '6px 8px';
                item.style.cursor = 'pointer';
                item.addEventListener('mouseover', () => item.style.background = 'rgba(255,255,255,0.1)');
                item.addEventListener('mouseout', () => item.style.background = 'transparent');
                item.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    const oldVal = fieldInput.value;
                    fieldInput.value = t;
                    fieldDropdownList.style.display = 'none';
                    if (oldVal !== t) {
                        populateValues();
                        valInput.value = ''; // clear when changing fields
                    }
                });
                fieldDropdownList.appendChild(item);
            });
            fieldDropdownList.style.display = 'block';
        };
        
        fieldInput.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.val-dropdown-list').forEach(d => d.style.display = 'none');
            document.querySelectorAll('.shape-dropdown-menu').forEach(d => d.style.display = 'none');
            document.querySelectorAll('.field-dropdown-list').forEach(d => d.style.display = 'none');
            renderFieldList('');
        });
        
        fieldInput.addEventListener('input', () => renderFieldList(fieldInput.value));
        
        document.addEventListener('click', () => {
            fieldDropdownList.style.display = 'none';
        });
        
        const opSelect = document.createElement('select');
        opSelect.className = 'rule-operator rule-select';
        opSelect.innerHTML = `
            <option value="==" ${rule.operator === '==' ? 'selected' : ''}>is</option>
            <option value="!=" ${rule.operator === '!=' ? 'selected' : ''}>is not</option>
        `;
        
        const valContainer = document.createElement('div');
        valContainer.style.position = 'relative';
        
        const valInput = document.createElement('input');
        valInput.type = 'text';
        valInput.className = 'rule-value rule-input';
        valInput.value = rule.value || '';
        valInput.style.padding = '4px 8px';
        valInput.style.borderRadius = '4px';
        valInput.style.border = '1px solid var(--border-color)';
        valInput.style.background = 'var(--modal-input-bg)';
        valInput.style.color = 'var(--text-primary)';
        valInput.style.width = '120px';
        valInput.autocomplete = 'off';
        
        const dropdownList = document.createElement('div');
        dropdownList.className = 'val-dropdown-list';
        dropdownList.style.position = 'absolute';
        dropdownList.style.top = '100%';
        dropdownList.style.left = '0';
        dropdownList.style.width = '100%';
        dropdownList.style.maxHeight = '150px';
        dropdownList.style.overflowY = 'auto';
        dropdownList.style.background = 'var(--modal-bg)';
        dropdownList.style.border = '1px solid var(--border-color)';
        dropdownList.style.borderRadius = '4px';
        dropdownList.style.zIndex = '1000';
        dropdownList.style.display = 'none';
        dropdownList.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';
        
        valContainer.appendChild(valInput);
        valContainer.appendChild(dropdownList);
        
        let currentOptions = [];
        
        const populateValues = () => {
            const field = fieldInput.value;
            let optionsToAdd = [];
            
            if (field === 'Target') {
                optionsToAdd = globalTargets;
            } else if (field === 'Type') {
                optionsToAdd = ['Air Outlet', 'System'];
            } else if (field === 'Pattern') {
                optionsToAdd = [...(projectFieldsData.patterns || [])];
                if (tagsConfig.uploadedStamps) {
                    tagsConfig.uploadedStamps.forEach(s => {
                        if (!optionsToAdd.includes(s)) optionsToAdd.push(s);
                    });
                }
                if (tagsConfig.rules) {
                    tagsConfig.rules.forEach(r => {
                        if (r.field === 'Pattern' && r.value && !optionsToAdd.includes(r.value)) {
                            optionsToAdd.push(r.value);
                        }
                    });
                }
            } else if (field === 'System') {
                optionsToAdd = [...(projectFieldsData.system_patterns || [])];
                if (tagsConfig.rules) {
                    tagsConfig.rules.forEach(r => {
                        if (r.field === 'System' && r.value && !optionsToAdd.includes(r.value)) {
                            optionsToAdd.push(r.value);
                        }
                    });
                }
            } else if (projectFieldsData.fields_data && projectFieldsData.fields_data[field]) {
                optionsToAdd = projectFieldsData.fields_data[field];
            }
            
            currentOptions = optionsToAdd;
        };
        
        const renderList = (filterText = '') => {
            dropdownList.innerHTML = '';
            const lowerFilter = filterText.toLowerCase();
            const filtered = currentOptions.filter(t => t.toLowerCase().includes(lowerFilter));
            
            if (filtered.length === 0) {
                dropdownList.style.display = 'none';
                return;
            }
            
            filtered.forEach(t => {
                const item = document.createElement('div');
                item.textContent = t;
                item.style.padding = '6px 8px';
                item.style.cursor = 'pointer';
                item.addEventListener('mouseover', () => item.style.background = 'rgba(255,255,255,0.1)');
                item.addEventListener('mouseout', () => item.style.background = 'transparent');
                item.addEventListener('mousedown', (e) => {
                    e.preventDefault(); // prevent blur
                    valInput.value = t;
                    dropdownList.style.display = 'none';
                });
                dropdownList.appendChild(item);
            });
            dropdownList.style.display = 'block';
        };
        
        valInput.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.val-dropdown-list').forEach(d => d.style.display = 'none');
            document.querySelectorAll('.shape-dropdown-menu').forEach(d => d.style.display = 'none');
            renderList('');
        });
        
        valInput.addEventListener('input', () => renderList(valInput.value));
        
        document.addEventListener('click', () => {
            dropdownList.style.display = 'none';
        });
        
        populateValues();
        
        const spanThen = document.createElement('span');
        spanThen.textContent = 'THEN';
        spanThen.style.fontWeight = 'bold';
        
        row.appendChild(spanIf);
        row.appendChild(fieldContainer);
        row.appendChild(opSelect);
        row.appendChild(valContainer);
        row.appendChild(spanThen);

        if (rule.type === 'shape') {
            const resultContainer = document.createElement('div');
            resultContainer.style.position = 'relative';
            
            const resultSelectDisplay = document.createElement('div');
            resultSelectDisplay.className = 'rule-result-display';
            resultSelectDisplay.style.display = 'flex';
            resultSelectDisplay.style.alignItems = 'center';
            resultSelectDisplay.style.gap = '8px';
            resultSelectDisplay.style.padding = '4px 8px';
            resultSelectDisplay.style.background = 'var(--modal-input-bg)';
            resultSelectDisplay.style.border = '1px solid var(--border-color)';
            resultSelectDisplay.style.borderRadius = '4px';
            resultSelectDisplay.style.cursor = 'pointer';
            resultSelectDisplay.style.minWidth = '140px';
            resultSelectDisplay.style.height = '32px';
            resultSelectDisplay.style.boxSizing = 'border-box';
            
            const resultImg = document.createElement('img');
            resultImg.style.width = '24px';
            resultImg.style.height = '24px';
            resultImg.style.objectFit = 'contain';
            resultImg.style.display = 'none';
            resultImg.style.background = '#fff'; // for better visibility if transparent
            resultImg.style.borderRadius = '2px';
            
            const resultText = document.createElement('span');
            resultText.textContent = '-- Select Stamp --';
            resultText.style.flex = '1';
            resultText.style.overflow = 'hidden';
            resultText.style.textOverflow = 'ellipsis';
            resultText.style.whiteSpace = 'nowrap';
            
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.className = 'rule-result';
            hiddenInput.value = rule.result || '';
            
            const updateDisplay = (val) => {
                hiddenInput.value = val;
                if (val) {
                    resultText.textContent = val;
                    resultImg.src = `/api/global_stamps/${val}.png?v=${Date.now()}`;
                    resultImg.style.display = 'block';
                } else {
                    resultText.textContent = '-- Select Stamp --';
                    resultImg.style.display = 'none';
                }
            };
            
            updateDisplay(rule.result);
            
            resultSelectDisplay.appendChild(resultImg);
            resultSelectDisplay.appendChild(resultText);
            
            const dropdown = document.createElement('div');
            dropdown.style.position = 'absolute';
            dropdown.style.top = '100%';
            dropdown.style.left = '0';
            dropdown.style.background = 'var(--modal-bg)';
            dropdown.style.border = '1px solid var(--border-color)';
            dropdown.style.borderRadius = '4px';
            dropdown.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';
            dropdown.style.display = 'none';
            dropdown.style.zIndex = '1000';
            dropdown.style.maxHeight = '200px';
            dropdown.style.overflowY = 'auto';
            dropdown.style.width = 'max-content';
            dropdown.style.minWidth = '100%';
            dropdown.style.marginTop = '4px';
            
            tagsConfig.uploadedStamps.forEach(s => {
                const opt = document.createElement('div');
                opt.style.display = 'flex';
                opt.style.alignItems = 'center';
                opt.style.gap = '8px';
                opt.style.padding = '6px 8px';
                opt.style.cursor = 'pointer';
                
                const optImg = document.createElement('img');
                optImg.src = `/api/global_stamps/${s}.png?v=${Date.now()}`;
                optImg.style.width = '24px';
                optImg.style.height = '24px';
                optImg.style.objectFit = 'contain';
                optImg.style.background = '#fff';
                optImg.style.borderRadius = '2px';
                
                const optText = document.createElement('span');
                optText.textContent = s;
                
                opt.appendChild(optImg);
                opt.appendChild(optText);
                
                opt.addEventListener('mouseover', () => opt.style.background = 'rgba(255,255,255,0.1)');
                opt.addEventListener('mouseout', () => opt.style.background = 'transparent');
                
                opt.addEventListener('click', () => {
                    updateDisplay(s);
                    dropdown.style.display = 'none';
                });
                
                dropdown.appendChild(opt);
            });
            
            resultSelectDisplay.addEventListener('click', (e) => {
                e.stopPropagation();
                const isShowing = dropdown.style.display === 'block';
                document.querySelectorAll('.shape-dropdown-menu').forEach(d => d.style.display = 'none');
                dropdown.style.display = isShowing ? 'none' : 'block';
            });
            dropdown.className = 'shape-dropdown-menu';
            
            document.addEventListener('click', () => {
                dropdown.style.display = 'none';
            });
            
            resultContainer.appendChild(resultSelectDisplay);
            resultContainer.appendChild(hiddenInput);
            resultContainer.appendChild(dropdown);
            
            row.appendChild(resultContainer);
        } else {
            const resultColor = document.createElement('input');
            resultColor.type = 'color';
            resultColor.className = 'rule-result';
            resultColor.value = rule.result || '#ff0000';
            resultColor.style.background = 'transparent';
            resultColor.style.border = 'none';
            resultColor.style.cursor = 'pointer';
            resultColor.style.padding = '0';
            resultColor.style.width = '30px';
            resultColor.style.height = '24px';
            row.appendChild(resultColor);
        }

        const btnRemove = document.createElement('button');
        btnRemove.className = 'btn btn-remove-rule';
        btnRemove.style.marginLeft = 'auto';
        btnRemove.style.background = 'transparent';
        btnRemove.style.color = '#ef4444';
        btnRemove.style.border = 'none';
        btnRemove.style.padding = '4px';
        btnRemove.textContent = '🗑';
        btnRemove.addEventListener('click', () => {
            row.remove();
        });
        row.appendChild(btnRemove);
        
        row.dataset.type = rule.type;

        if (rule.type === 'shape') {
            shapeRulesContainer.appendChild(row);
        } else {
            colorRulesContainer.appendChild(row);
        }
    }

    btnSaveConfig.addEventListener('click', async () => {
        const projectName = window.currentProject || getProjectNameFromUrl();
        if (!projectName) return;

        const rules = [];
        document.querySelectorAll('.tag-rule-row').forEach(row => {
            rules.push({
                type: row.dataset.type,
                field: row.querySelector('.rule-field').value,
                operator: row.querySelector('.rule-operator').value,
                value: row.querySelector('.rule-value').value,
                result: row.querySelector('.rule-result').value
            });
        });

        const hoverFields = [];
        document.querySelectorAll('.hover-field-checkbox:checked').forEach(cb => {
            hoverFields.push(cb.value);
        });

        const newConfig = {
            uploadedStamps: tagsConfig.uploadedStamps,
            rules: rules,
            hoverFields: hoverFields
        };
        window.globalTagsConfig = newConfig;

        try {
            const res = await fetch(`/api/manage_tags/config?project=${encodeURIComponent(projectName)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newConfig)
            });
            const data = await res.json();
            if (data.success) {
                // Apply rules to all stamps in the project
                try {
                    const applyRes = await fetch('/api/manage_tags/apply_rules', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ project: projectName })
                    });
                    const applyData = await applyRes.json();
                    if (!applyData.success) {
                        console.error('apply_rules backend error:', applyData.error || applyData);
                    }
                    if (applyData.logs && applyData.logs.length > 0) {
                        console.log("--- TAG RULES ENGINE LOGS ---");
                        applyData.logs.forEach(log => console.log(log));
                        console.log("-----------------------------");
                    }
                    const updCount = applyData.updated ?? 0;
                    const evalCount = applyData.stamps_evaluated ?? 0;
                    alert(`Configuration saved! Rules applied: ${updCount} stamp(s) updated out of ${evalCount} evaluated.`);
                    
                    // Automatically close the window on successful save
                    panel.style.display = 'none';
                } catch (applyErr) {
                    console.error('apply_rules failed:', applyErr);
                    alert('Configuration saved. (Rule application failed — check console.)');
                }
                // Refresh stamp visuals on the canvas
                if (window.refreshStampVisuals) window.refreshStampVisuals();
                // Refresh data viewer if open
                const dataViewer = document.getElementById('data-viewer-container');
                if (dataViewer && dataViewer.style.display !== 'none') {
                    const btnViewData = document.getElementById('btn-view-project-data');
                    if (btnViewData) btnViewData.click();
                }
            } else {
                alert('Save failed: ' + (data.error || 'Unknown error'));
            }
        } catch (e) {
            console.error(e);
            alert('Failed to save config.');
        }
    });

    function getProjectNameFromUrl() {
        const params = new URLSearchParams(window.location.search);
        let project = params.get('pdf') || params.get('project');
        if (project) {
            // Usually pdf is Projects/ProjectName/pdf.pdf
            const parts = project.split('/');
            if (parts[0] === 'Projects' && parts.length >= 2) {
                return parts[1];
            }
        }
        return '';
    }

    async function loadTagsConfig() {
        const projectName = window.currentProject || getProjectNameFromUrl();
        if (!projectName) return;

        try {
            const res = await fetch(`/api/manage_tags/config?project=${encodeURIComponent(projectName)}`);
            const data = await res.json();
            if (data.success) {
                tagsConfig = data.config || { uploadedStamps: [], rules: [] };
                
                // Update UI
                uploadedList.innerHTML = '';
                tagsConfig.uploadedStamps.forEach(s => {
                    const pill = document.createElement('div');
                    pill.style.background = 'rgba(59,130,246,0.2)';
                    pill.style.border = '1px solid rgba(59,130,246,0.5)';
                    pill.style.padding = '4px 8px';
                    pill.style.borderRadius = '12px';
                    pill.style.fontSize = '0.8rem';
                    pill.style.display = 'flex';
                    pill.style.alignItems = 'center';
                    pill.style.gap = '6px';
                    
                    const img = document.createElement('img');
                    img.src = `/api/global_stamps/${s}.png?v=${Date.now()}`;
                    img.style.width = '20px';
                    img.style.height = '20px';
                    img.style.objectFit = 'contain';
                    img.style.background = '#fff';
                    img.style.borderRadius = '2px';
                    
                    const text = document.createElement('span');
                    text.textContent = s;
                    
                    const delBtn = document.createElement('button');
                    delBtn.innerHTML = '&times;';
                    delBtn.style.background = 'transparent';
                    delBtn.style.border = 'none';
                    delBtn.style.color = '#ef4444';
                    delBtn.style.cursor = 'pointer';
                    delBtn.style.fontSize = '1.2rem';
                    delBtn.style.lineHeight = '1';
                    delBtn.style.padding = '0 4px';
                    delBtn.style.marginLeft = '4px';
                    delBtn.title = 'Delete stamp';
                    
                    delBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        if (confirm(`Delete stamp "${s}"? This will remove it from the global configuration.`)) {
                            try {
                                const res = await fetch('/api/manage_tags/delete_stamp', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify({stamp_name: s})
                                });
                                const data = await res.json();
                                if (data.success) {
                                    loadTagsConfig(); // reload to update UI
                                } else {
                                    alert('Failed to delete: ' + data.error);
                                }
                            } catch (err) {
                                console.error(err);
                                alert('Failed to delete stamp.');
                            }
                        }
                    });
                    
                    pill.appendChild(img);
                    pill.appendChild(text);
                    pill.appendChild(delBtn);
                    uploadedList.appendChild(pill);
                });

                shapeRulesContainer.innerHTML = '';
                colorRulesContainer.innerHTML = '';
                tagsConfig.rules.forEach(rule => addRuleRow(rule));

                // Populate Hover Fields
                const hoverContainer = document.getElementById('hover-fields-container');
                if (hoverContainer) {
                    hoverContainer.innerHTML = '';
                    const allFields = projectFieldsData.fields || [];
                    if (allFields.length === 0) {
                        hoverContainer.innerHTML = '<span style="color: var(--text-secondary); font-size: 0.85rem;">No fields available.</span>';
                    } else {
                        const orderedFields = [];
                        const configuredFields = tagsConfig.hoverFields || [];
                        configuredFields.forEach(f => {
                            if (allFields.includes(f)) orderedFields.push(f);
                        });
                        allFields.forEach(f => {
                            if (!orderedFields.includes(f)) orderedFields.push(f);
                        });

                        function updateHoverFieldsPreview() {
                            const currentHoverFields = [];
                            hoverContainer.querySelectorAll('.hover-field-checkbox:checked').forEach(c => {
                                currentHoverFields.push(c.value);
                            });
                            if (!window.globalTagsConfig) window.globalTagsConfig = { hoverFields: [] };
                            window.globalTagsConfig.hoverFields = currentHoverFields;
                            if (window.redrawStampVisuals) window.redrawStampVisuals();
                        }

                        orderedFields.forEach(f => {
                            const wrapper = document.createElement('div');
                            wrapper.className = 'hover-field-item';
                            wrapper.draggable = true;
                            wrapper.style.display = 'flex';
                            wrapper.style.alignItems = 'center';
                            wrapper.style.gap = '6px';
                            wrapper.style.padding = '4px 8px';
                            wrapper.style.margin = '2px 0';
                            wrapper.style.border = '1px solid transparent';
                            wrapper.style.borderRadius = '4px';
                            wrapper.style.cursor = 'grab';

                            wrapper.addEventListener('dragstart', (e) => {
                                e.dataTransfer.setData('text/plain', f);
                                wrapper.style.opacity = '0.5';
                                wrapper.classList.add('dragging');
                            });
                            wrapper.addEventListener('dragend', () => {
                                wrapper.style.opacity = '1';
                                wrapper.classList.remove('dragging');
                                document.querySelectorAll('.hover-field-item').forEach(el => {
                                    el.style.borderTop = '1px solid transparent';
                                    el.style.borderBottom = '1px solid transparent';
                                });
                            });
                            wrapper.addEventListener('dragover', (e) => {
                                e.preventDefault();
                                const draggingItem = hoverContainer.querySelector('.dragging');
                                if (draggingItem && draggingItem !== wrapper) {
                                    const bounding = wrapper.getBoundingClientRect();
                                    const offset = bounding.y + (bounding.height / 2);
                                    if (e.clientY - offset > 0) {
                                        wrapper.style.borderBottom = '1px solid #3b82f6';
                                        wrapper.style.borderTop = '1px solid transparent';
                                    } else {
                                        wrapper.style.borderTop = '1px solid #3b82f6';
                                        wrapper.style.borderBottom = '1px solid transparent';
                                    }
                                }
                            });
                            wrapper.addEventListener('dragleave', () => {
                                wrapper.style.borderTop = '1px solid transparent';
                                wrapper.style.borderBottom = '1px solid transparent';
                            });
                            wrapper.addEventListener('drop', (e) => {
                                e.preventDefault();
                                wrapper.style.borderTop = '1px solid transparent';
                                wrapper.style.borderBottom = '1px solid transparent';
                                const draggingItem = hoverContainer.querySelector('.dragging');
                                if (draggingItem && draggingItem !== wrapper) {
                                    const bounding = wrapper.getBoundingClientRect();
                                    const offset = bounding.y + (bounding.height / 2);
                                    if (e.clientY - offset > 0) {
                                        wrapper.after(draggingItem);
                                    } else {
                                        wrapper.before(draggingItem);
                                    }
                                    updateHoverFieldsPreview();
                                }
                            });

                            const dragHandle = document.createElement('span');
                            dragHandle.innerHTML = '&#9776;'; // Hamburger icon
                            dragHandle.style.color = 'var(--text-secondary)';
                            dragHandle.style.cursor = 'grab';
                            dragHandle.style.marginRight = '4px';

                            const lbl = document.createElement('label');
                            lbl.style.display = 'flex';
                            lbl.style.alignItems = 'center';
                            lbl.style.gap = '6px';
                            lbl.style.fontSize = '0.85rem';
                            lbl.style.cursor = 'pointer';
                            lbl.style.color = 'var(--text-primary)';
                            lbl.style.margin = '0';
                            lbl.style.flex = '1';
                            
                            const cb = document.createElement('input');
                            cb.type = 'checkbox';
                            cb.className = 'hover-field-checkbox';
                            cb.value = f;
                            if (tagsConfig.hoverFields && tagsConfig.hoverFields.includes(f)) {
                                cb.checked = true;
                            }
                            cb.addEventListener('change', () => {
                                updateHoverFieldsPreview();
                            });
                            
                            lbl.appendChild(cb);
                            lbl.appendChild(document.createTextNode(f));
                            
                            wrapper.appendChild(dragHandle);
                            wrapper.appendChild(lbl);
                            hoverContainer.appendChild(wrapper);
                        });
                    }
                }
                window.globalTagsConfig = tagsConfig;
            }
        } catch (e) {
            console.error('Error loading tags config:', e);
        }
    }

    // Close on Escape key press
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && panel.style.display === 'flex') {
            panel.style.display = 'none';
        }
    });

    // Close on click outside modal content (if clicking outside the panel itself)
    // We attach this to document.mousedown but we have to ensure we don't close it when clicking the Manage Tags button itself.
    document.addEventListener('mousedown', (e) => {
        if (panel.style.display === 'flex' && 
            !panel.contains(e.target) && 
            e.target !== btnManageTags && 
            !btnManageTags.contains(e.target)) {
            panel.style.display = 'none';
        }
    });

    // Hover Fields toggle
    const btnHoverToggle = document.getElementById('btn-hover-fields-toggle');
    const hoverContainer = document.getElementById('hover-fields-container');
    if (btnHoverToggle && hoverContainer) {
        btnHoverToggle.addEventListener('click', () => {
            if (hoverContainer.style.display === 'none') {
                hoverContainer.style.display = 'flex';
            } else {
                hoverContainer.style.display = 'none';
            }
        });
        
        // Hide hover container when clicking outside of it and toggle
        document.addEventListener('mousedown', (e) => {
            if (hoverContainer.style.display === 'flex' && !hoverContainer.contains(e.target) && e.target !== btnHoverToggle) {
                hoverContainer.style.display = 'none';
            }
        });
    }
}

// Fetch global tags config on load for renderer
fetch('/api/manage_tags/config')
    .then(res => res.json())
    .then(data => {
        if (data.success && data.config) {
            window.globalTagsConfig = data.config;
            if (window.refreshStampVisuals) window.refreshStampVisuals();
        }
    })
    .catch(err => console.error("Error fetching global tags config:", err));

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initManageTags);
} else {
    initManageTags();
}
