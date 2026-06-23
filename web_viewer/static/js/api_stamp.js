// api_stamp.js
// Handles communication with the Stamp DB endpoints

const stampAPI = {
    async getStampMeta(project_name, pdf_name, page, xref) {
        const response = await fetch(`/api/stamps/${encodeURIComponent(project_name)}/${encodeURIComponent(pdf_name)}/${page}/${xref}`);
        if (!response.ok) throw new Error("Failed to fetch stamp metadata");
        return await response.json();
    },

    async updateStampMeta(project_name, pdf_name, page, xref, fields, group_id, stamp_type, pattern_name) {
        const payload = { fields };
        if (group_id !== undefined) payload.group_id = group_id;
        if (stamp_type !== undefined) payload.stamp_type = stamp_type;
        if (pattern_name !== undefined) payload.pattern_name = pattern_name;

        const response = await fetch(`/api/stamps/${encodeURIComponent(project_name)}/${encodeURIComponent(pdf_name)}/${page}/${xref}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error("Failed to update stamp metadata");
        return await response.json();
    },

    async getGroups(project_name) {
        const response = await fetch(`/api/groups/${encodeURIComponent(project_name)}`);
        if (!response.ok) throw new Error("Failed to fetch groups");
        return await response.json();
    },

    async createGroup(project_name, name, color) {
        const response = await fetch(`/api/groups/${encodeURIComponent(project_name)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, color })
        });
        if (!response.ok) throw new Error("Failed to create group");
        return await response.json();
    }
};

window.stampAPI = stampAPI;

/**
 * Switch the visible toolbar panel smoothly (no display-swap blink).
 * Deactivates all .toolbar-panel elements, then activates the one with the given id.
 * @param {string} activeId - The id of the toolbar panel to show.
 */
window.switchToolbarPanel = function(activeId) {
    const panels = document.querySelectorAll('.toolbar-panel');
    panels.forEach(p => {
        if (p.id === activeId) {
            p.classList.add('toolbar-panel--active');
        } else {
            p.classList.remove('toolbar-panel--active');
        }
    });
};

// Modal Logic
function initStampAPI() {
    const modal = document.getElementById("stamp-meta-modal");
    const groupModal = document.getElementById("new-group-modal");
    
    const closeBtn = document.getElementById("btn-close-stamp-modal");
    const cancelBtn = document.getElementById("btn-cancel-stamp");
    const saveBtn = document.getElementById("btn-save-stamp");
    const deleteBtn = document.getElementById("btn-delete-stamp");
    const addFieldBtn = document.getElementById("btn-add-field");
    const groupSelect = document.getElementById("stamp-group-select");
    const newGroupBtn = document.getElementById("btn-new-group");
    
    const closeGroupBtn = document.getElementById("btn-cancel-group");
    const saveGroupBtn = document.getElementById("btn-save-group");
    
    let currentStamp = null;
    let currentSettings = {
        system_fields: [],
        air_outlet_fields: [],
        system_column_order: [],
        air_outlet_column_order: []
    };

    function closeModal() {
        modal.style.display = "none";
        currentStamp = null;

        // Clear hash fragment from browser URL
        if (window.location.hash) {
            const url = new URL(window.location.href);
            url.hash = "";
            window.history.replaceState({}, document.title, url.pathname + url.search);
        }
    }

    // Close on Escape key press
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal.style.display === "flex") {
            closeModal();
        }
    });

    // Close when clicking outside of the modal dialog box
    modal.addEventListener("click", (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    closeBtn.addEventListener("click", closeModal);
    cancelBtn.addEventListener("click", closeModal);

    // Dynamic field creation
    const fieldsContainer = document.getElementById("stamp-fields-container");
    
    // --- Formula Modal Setup ---
    let formulaModal = document.getElementById("formula-editor-modal");
    if (!formulaModal) {
        formulaModal = document.createElement("div");
        formulaModal.id = "formula-editor-modal";
        formulaModal.className = "modal";
        formulaModal.style.display = "none";
        formulaModal.style.zIndex = "2000";
        formulaModal.innerHTML = `
            <div class="modal-content glass-modal" style="max-width: 500px; width: 100%;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0;">Edit Formula</h3>
                    <span id="btn-close-formula-modal" class="close-btn" style="cursor: pointer;">&times;</span>
                </div>
                <div class="modal-body" style="display: flex; gap: 10px; align-items: center; margin-top: 15px;">
                    <datalist id="formula-fields-datalist"></datalist>
                    
                    <div style="flex: 1;">
                        <label style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px; display: block;">Operand 1</label>
                        <input type="text" id="formula-op1" list="formula-fields-datalist" placeholder="Field or Value" style="width: 100%; padding: 6px; border-radius: 4px; border: 1px solid var(--modal-input-border); background: var(--modal-input-bg); color: var(--text-primary); box-sizing: border-box;">
                    </div>
                    
                    <div>
                        <label style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px; display: block;">Function</label>
                        <select id="formula-operator" style="padding: 6px; border-radius: 4px; border: 1px solid var(--modal-input-border); background: var(--modal-input-bg); color: var(--text-primary); height: 31px; box-sizing: border-box;">
                            <option value="+">+</option>
                            <option value="-">-</option>
                            <option value="*">*</option>
                            <option value="/">/</option>
                            <option value="%">%</option>
                        </select>
                    </div>
                    
                    <div style="flex: 1;">
                        <label style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px; display: block;">Operand 2</label>
                        <input type="text" id="formula-op2" list="formula-fields-datalist" placeholder="Field or Value" style="width: 100%; padding: 6px; border-radius: 4px; border: 1px solid var(--modal-input-border); background: var(--modal-input-bg); color: var(--text-primary); box-sizing: border-box;">
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px;">
                    <button id="btn-cancel-formula" class="btn">Cancel</button>
                    <button id="btn-save-formula" class="btn primary-btn">Apply</button>
                </div>
            </div>
        `;
        document.body.appendChild(formulaModal);
        
        document.getElementById("btn-close-formula-modal").addEventListener("click", () => formulaModal.style.display = "none");
        document.getElementById("btn-cancel-formula").addEventListener("click", () => formulaModal.style.display = "none");
        
        formulaModal.addEventListener("click", (e) => {
            if (e.target === formulaModal) {
                formulaModal.style.display = "none";
            }
        });
    }

    let currentFormulaInput = null;
    let currentFormulaRow = null;

    async function openFormulaEditor(valueInput, row) {
        currentFormulaInput = valueInput;
        currentFormulaRow = row;
        const projectName = window.currentProject || (document.getElementById("current-project-label") ? document.getElementById("current-project-label").textContent : "");
        let availableFields = [];
        if (projectName) {
            try {
                const res = await fetch(`/api/projects/${encodeURIComponent(projectName)}/fields_data`);
                const data = await res.json();
                if (data.success) {
                    availableFields = data.fields || [];
                }
            } catch (e) {
                console.error("Error fetching fields for formula:", e);
            }
        }
        
        const datalist = document.getElementById("formula-fields-datalist");
        datalist.innerHTML = "";
        availableFields.forEach(f => {
            const opt = document.createElement("option");
            opt.value = f;
            datalist.appendChild(opt);
        });
        
        let op1 = "";
        let op = "+";
        let op2 = "";
        
        const val = row && row.dataset.formula ? row.dataset.formula.trim() : "";
        const match = val.match(/^(.*?)\s+([\+\-\*\/\%])\s+(.*)$/);
        if (match) {
            op1 = match[1];
            op = match[2];
            op2 = match[3];
        } else if (val) {
            op1 = val;
        }
        
        document.getElementById("formula-op1").value = op1;
        document.getElementById("formula-operator").value = op;
        document.getElementById("formula-op2").value = op2;
        
        formulaModal.style.display = "flex";
    }

    const saveFormulaHandler = () => {
        if (currentFormulaInput && currentFormulaRow) {
            const op1 = document.getElementById("formula-op1").value.trim();
            const op = document.getElementById("formula-operator").value;
            const op2 = document.getElementById("formula-op2").value.trim();
            
            let expr = "";
            if (op1 && op2) {
                expr = `${op1} ${op} ${op2}`;
            } else if (op1) {
                expr = op1;
            } else if (op2) {
                expr = op2;
            }
            
            currentFormulaRow.dataset.formula = expr;
            
            // evaluate immediately for immediate feedback
            let evalVal = "";
            const fieldMap = {};
            const fieldsContainer = document.getElementById("stamp-fields-container");
            if (fieldsContainer) {
                fieldsContainer.querySelectorAll(".stamp-field-row").forEach(r => {
                    const inputs = r.querySelectorAll("input");
                    const select = r.querySelector("select");
                    if (inputs.length >= 2) {
                        const fname = inputs[0].value.trim().toLowerCase();
                        const fval = inputs[1].value.trim();
                        const ftype = select ? select.value : "string";
                        if (fname && ftype !== "formula") {
                            fieldMap[fname] = fval;
                        }
                    }
                });
            }
            
            const match = expr.match(/^(.*?)\s+([\+\-\*\/\%])\s+(.*)$/);
            if (match) {
                let p1 = match[1].trim();
                let p = match[2].trim();
                let p2 = match[3].trim();
                let val1 = isNaN(parseFloat(p1)) ? (fieldMap[p1.toLowerCase()] || 0) : parseFloat(p1);
                let val2 = isNaN(parseFloat(p2)) ? (fieldMap[p2.toLowerCase()] || 0) : parseFloat(p2);
                val1 = parseFloat(val1) || 0;
                val2 = parseFloat(val2) || 0;
                switch(p) {
                    case '+': evalVal = val1 + val2; break;
                    case '-': evalVal = val1 - val2; break;
                    case '*': evalVal = val1 * val2; break;
                    case '/': evalVal = val2 !== 0 ? val1 / val2 : 0; break;
                    case '%': evalVal = val2 !== 0 ? val1 % val2 : 0; break;
                }
                evalVal = Math.round(evalVal * 100) / 100;
            } else {
                let single = expr.trim();
                evalVal = fieldMap[single.toLowerCase()] || single;
            }
            
            currentFormulaInput.value = evalVal !== "" ? evalVal : expr;
            currentFormulaRow.dataset.loadedValue = currentFormulaInput.value;
        }
        formulaModal.style.display = "none";
    };
    
    // Remove existing listener to avoid duplicates if initStampAPI is called multiple times
    const btnSaveForm = document.getElementById("btn-save-formula");
    if (btnSaveForm) {
        const newBtnSaveForm = btnSaveForm.cloneNode(true);
        btnSaveForm.parentNode.replaceChild(newBtnSaveForm, btnSaveForm);
        newBtnSaveForm.addEventListener("click", saveFormulaHandler);
    }
    // --- End Formula Modal Setup ---

    // --- Conditional Formatting Modal Setup ---
    let condFormatModal = document.getElementById("cond-format-modal");
    if (!condFormatModal) {
        condFormatModal = document.createElement("div");
        condFormatModal.id = "cond-format-modal";
        condFormatModal.className = "modal";
        condFormatModal.style.display = "none";
        condFormatModal.style.zIndex = "2000";
        condFormatModal.innerHTML = `
            <div class="modal-content glass-modal" style="max-width: 600px; width: 100%;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0;">Conditional Formatting</h3>
                    <span id="btn-close-cond-modal" class="close-btn" style="cursor: pointer;">&times;</span>
                </div>
                <div class="modal-body" style="margin-top: 15px;">
                    <div id="cond-format-rules-container" style="display: flex; flex-direction: column; gap: 10px;"></div>
                    <button id="btn-add-cond-rule" class="btn" style="margin-top: 10px;">+ Add Condition</button>
                </div>
                <div class="modal-footer" style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px;">
                    <button id="btn-cancel-cond" class="btn">Cancel</button>
                    <button id="btn-save-cond" class="btn primary-btn">Apply</button>
                </div>
            </div>
        `;
        document.body.appendChild(condFormatModal);
        
        document.getElementById("btn-close-cond-modal").addEventListener("click", () => condFormatModal.style.display = "none");
        document.getElementById("btn-cancel-cond").addEventListener("click", () => condFormatModal.style.display = "none");
        
        condFormatModal.addEventListener("click", (e) => {
            if (e.target === condFormatModal) {
                condFormatModal.style.display = "none";
            }
        });
    }

    let currentCondRow = null;
    let currentCondInput = null;

    function renderCondFormatRules(rules) {
        const container = document.getElementById("cond-format-rules-container");
        container.innerHTML = "";
        rules.forEach((rule, idx) => {
            const ruleDiv = document.createElement("div");
            ruleDiv.style.display = "flex";
            ruleDiv.style.gap = "10px";
            ruleDiv.style.alignItems = "center";
            ruleDiv.className = "cond-format-rule-row";
            ruleDiv.innerHTML = `
                <span style="font-size: 0.8rem; color: var(--text-secondary); width: 20px;">${idx + 1}.</span>
                <select class="cond-operator" style="padding: 6px; border-radius: 4px; border: 1px solid var(--modal-input-border); background: var(--modal-input-bg); color: var(--text-primary);">
                    <option value="==" ${rule.operator === '==' ? 'selected' : ''}>=</option>
                    <option value="<" ${rule.operator === '<' ? 'selected' : ''}>&lt;</option>
                    <option value=">" ${rule.operator === '>' ? 'selected' : ''}>&gt;</option>
                    <option value="!=" ${rule.operator === '!=' ? 'selected' : ''}>!=</option>
                </select>
                <input type="text" class="cond-target" list="formula-fields-datalist" placeholder="Value or Field" value="${rule.target || ''}" style="flex: 1; padding: 6px; border-radius: 4px; border: 1px solid var(--modal-input-border); background: var(--modal-input-bg); color: var(--text-primary); box-sizing: border-box;">
                <input type="color" class="cond-color" value="${rule.color || '#ff0000'}" style="padding: 0; border: none; background: transparent; cursor: pointer; width: 30px; height: 30px; border-radius: 4px;">
                <button class="btn small-btn btn-remove-cond-rule" style="color: #ef4444; border: none; background: transparent;" title="Remove">🗑</button>
            `;
            ruleDiv.querySelector(".btn-remove-cond-rule").addEventListener("click", () => {
                ruleDiv.remove();
            });
            container.appendChild(ruleDiv);
        });
    }

    document.getElementById("btn-add-cond-rule").addEventListener("click", () => {
        const container = document.getElementById("cond-format-rules-container");
        if (container.children.length >= 5) {
            alert("Maximum 5 conditions allowed.");
            return;
        }
        const rules = [];
        container.querySelectorAll(".cond-format-rule-row").forEach(row => {
            rules.push({
                operator: row.querySelector(".cond-operator").value,
                target: row.querySelector(".cond-target").value,
                color: row.querySelector(".cond-color").value
            });
        });
        rules.push({ operator: "==", target: "", color: "#ff0000" });
        renderCondFormatRules(rules);
    });

    document.getElementById("btn-save-cond").addEventListener("click", () => {
        if (!currentCondRow) return;
        const container = document.getElementById("cond-format-rules-container");
        const rules = [];
        container.querySelectorAll(".cond-format-rule-row").forEach(row => {
            const target = row.querySelector(".cond-target").value.trim();
            if (target) {
                rules.push({
                    operator: row.querySelector(".cond-operator").value,
                    target: target,
                    color: row.querySelector(".cond-color").value
                });
            }
        });
        currentCondRow.dataset.conditionalFormatting = JSON.stringify(rules);
        condFormatModal.style.display = "none";
        evaluateRowConditionalFormatting(currentCondRow);
    });

    function openCondFormatEditor(row, valueInput) {
        currentCondRow = row;
        currentCondInput = valueInput;
        let rules = [];
        try {
            if (row.dataset.conditionalFormatting) {
                rules = JSON.parse(row.dataset.conditionalFormatting);
            }
        } catch(e) { console.error("Error parsing conditional formatting:", e); }
        renderCondFormatRules(rules);
        condFormatModal.style.display = "flex";
    }

    // Evaluator
    function evaluateRowConditionalFormatting(row) {
        if (!row) return;
        const valueInput = row.querySelector("td:nth-child(3) input");
        if (!valueInput) return;
        
        valueInput.style.backgroundColor = "transparent";
        valueInput.style.color = "var(--text-primary)";
        
        const condStr = row.dataset.conditionalFormatting;
        if (!condStr) return;
        
        let rules = [];
        try {
            rules = JSON.parse(condStr);
        } catch(e) { return; }
        if (!rules.length) return;
        
        const myVal = valueInput.value.trim();
        const myNum = parseFloat(myVal);
        const myIsNum = !isNaN(myNum);

        // Build context of all fields to resolve targets
        const context = {};
        document.querySelectorAll("#stamp-fields-tbody .stamp-field-row").forEach(r => {
            const inputs = r.querySelectorAll("input");
            if (inputs.length >= 2) {
                const k = inputs[0].value.trim();
                const v = inputs[1].value.trim();
                context[k] = v;
            }
        });

        for (const rule of rules) {
            let targetVal = rule.target;
            if (context.hasOwnProperty(targetVal)) {
                targetVal = context[targetVal];
            }
            
            let matched = false;
            const tNum = parseFloat(targetVal);
            const tIsNum = !isNaN(tNum);
            
            if (rule.operator === "==") {
                matched = myVal === targetVal;
            } else if (rule.operator === "<") {
                if (myIsNum && tIsNum) matched = myNum < tNum;
            } else if (rule.operator === ">") {
                if (myIsNum && tIsNum) matched = myNum > tNum;
            } else if (rule.operator === "!=") {
                matched = myVal !== targetVal;
            }
            
            if (matched) {
                valueInput.style.backgroundColor = rule.color + "33"; // 20% opacity
                valueInput.style.color = rule.color;
                break; // First match wins
            }
        }
    }

    window.evaluateConditionalFormattingRaw = function(fieldValue, rules, allFieldsObj) {
        if (!rules || !rules.length) return null;
        const myVal = String(fieldValue).trim();
        const myNum = parseFloat(myVal);
        const myIsNum = !isNaN(myNum);
        
        for (const rule of rules) {
            let targetVal = rule.target;
            if (allFieldsObj && allFieldsObj.hasOwnProperty(targetVal)) {
                targetVal = allFieldsObj[targetVal];
            }
            
            let matched = false;
            const tNum = parseFloat(targetVal);
            const tIsNum = !isNaN(tNum);
            
            if (rule.operator === "==") {
                matched = myVal === String(targetVal).trim();
            } else if (rule.operator === "<") {
                if (myIsNum && tIsNum) matched = myNum < tNum;
            } else if (rule.operator === ">") {
                if (myIsNum && tIsNum) matched = myNum > tNum;
            } else if (rule.operator === "!=") {
                matched = myVal !== String(targetVal).trim();
            }
            
            if (matched) {
                return rule.color;
            }
        }
        return null;
    };
    // --- End Conditional Formatting Setup ---

    function createFieldRow(name = "", value = "", type = "string", isHidden = false, isReadOnly = false, formula_expression = "", conditional_formatting = "") {
        if (formula_expression) {
            type = "formula";
        }
        
        const row = document.createElement("tr");
        row.className = "stamp-field-row";
        row.dataset.loadedValue = value;
        if (formula_expression) {
            row.dataset.formula = formula_expression;
        }
        if (conditional_formatting) {
            row.dataset.conditionalFormatting = conditional_formatting;
        }
        if (isHidden) {
            row.style.display = "none";
            row.dataset.hidden = "true";
        }
        
        // Name column
        const tdName = document.createElement("td");
        const nameInput = document.createElement("input");
        nameInput.type = "text";
        nameInput.placeholder = "Field Name";
        nameInput.value = name;
        if (isReadOnly) {
            nameInput.readOnly = true;
            nameInput.style.backgroundColor = "transparent";
            nameInput.style.border = "none";
            nameInput.style.color = "var(--text-secondary)";
            nameInput.style.cursor = "default";
        }
        tdName.appendChild(nameInput);
        
        // Type column
        const tdType = document.createElement("td");
        const typeSelect = document.createElement("select");
        typeSelect.innerHTML = `<option value="string" ${type==='string'?'selected':''}>String</option><option value="number" ${type==='number'?'selected':''}>Number</option><option value="formula" ${type==='formula'?'selected':''}>Formula</option>`;
        if (isReadOnly) {
            typeSelect.disabled = true;
            typeSelect.style.appearance = "none";
            typeSelect.style.border = "none";
            typeSelect.style.backgroundColor = "transparent";
            typeSelect.style.color = "var(--text-secondary)";
            typeSelect.style.cursor = "default";
        }
        tdType.appendChild(typeSelect);
        
        // Value column
        const tdValue = document.createElement("td");
        tdValue.style.display = "flex";
        tdValue.style.gap = "4px";
        
        const valueInput = document.createElement("input");
        valueInput.type = "text";
        valueInput.placeholder = "Value";
        valueInput.value = value;
        valueInput.style.flex = "1";
        if (isReadOnly) {
            valueInput.readOnly = true;
            valueInput.style.backgroundColor = "transparent";
            valueInput.style.border = "none";
            valueInput.style.color = "var(--text-secondary)";
            valueInput.style.cursor = "default";
        }
        valueInput.addEventListener("input", () => {
            evaluateRowConditionalFormatting(row);
        });
        tdValue.appendChild(valueInput);
        
        const btnFormula = document.createElement("button");
        btnFormula.className = "btn small-btn";
        btnFormula.textContent = "fx";
        btnFormula.style.display = type === "formula" ? "inline-block" : "none";
        btnFormula.style.margin = "0";
        btnFormula.title = "Edit Formula";
        if (isReadOnly) btnFormula.style.display = "none";
        
        btnFormula.onclick = (e) => {
            e.preventDefault();
            if (typeof openFormulaEditor === "function") {
                openFormulaEditor(valueInput, row);
            }
        };
        tdValue.appendChild(btnFormula);
        
        typeSelect.addEventListener("change", (e) => {
            if (e.target.value === "formula") {
                btnFormula.style.display = "inline-block";
            } else {
                btnFormula.style.display = "none";
            }
        });
        
        // Actions column
        const tdDel = document.createElement("td");
        tdDel.style.textAlign = "center";
        tdDel.style.width = "40px";
        if (!isReadOnly) {
            const actionsWrapper = document.createElement("div");
            actionsWrapper.style.display = "inline-block";

            const menuBtn = document.createElement("button");
            menuBtn.innerHTML = "⋮";
            menuBtn.title = "Options";
            menuBtn.style.cssText = "background: transparent; border: none; cursor: pointer; color: var(--text-primary); font-size: 1.2rem; padding: 0 5px; outline: none;";

            const dropdown = document.createElement("div");
            dropdown.className = "field-actions-dropdown";
            dropdown.style.display = "none";
            dropdown.style.position = "fixed"; // Float over everything
            dropdown.style.backgroundColor = "var(--modal-bg)";
            dropdown.style.border = "1px solid var(--border-color)";
            dropdown.style.borderRadius = "4px";
            dropdown.style.zIndex = "9999";
            dropdown.style.minWidth = "200px";
            dropdown.style.boxShadow = "0 2px 8px rgba(0,0,0,0.4)";
            dropdown.style.textAlign = "left";

            const delOpt = document.createElement("div");
            delOpt.innerHTML = "🗑 Delete";
            delOpt.style.padding = "8px 12px";
            delOpt.style.cursor = "pointer";
            delOpt.style.color = "var(--text-primary)";
            delOpt.onmouseover = () => delOpt.style.backgroundColor = "rgba(255,255,255,0.1)";
            delOpt.onmouseout = () => delOpt.style.backgroundColor = "transparent";
            delOpt.onclick = () => {
                row.remove();
                dropdown.style.display = "none";
            };

            const condOpt = document.createElement("div");
            condOpt.innerHTML = "🎨 Conditional Formatting";
            condOpt.style.padding = "8px 12px";
            condOpt.style.cursor = "pointer";
            condOpt.style.color = "var(--text-primary)";
            condOpt.onmouseover = () => condOpt.style.backgroundColor = "rgba(255,255,255,0.1)";
            condOpt.onmouseout = () => condOpt.style.backgroundColor = "transparent";
            condOpt.onclick = () => {
                dropdown.style.display = "none";
                openCondFormatEditor(row, valueInput);
            };

            dropdown.appendChild(condOpt);
            dropdown.appendChild(delOpt);

            menuBtn.onclick = (e) => {
                e.stopPropagation();
                const isShowing = dropdown.style.display === "block";
                document.querySelectorAll(".field-actions-dropdown").forEach(d => d.style.display = "none");
                if (!isShowing) {
                    const rect = menuBtn.getBoundingClientRect();
                    dropdown.style.top = (rect.bottom + 2) + "px";
                    // Align dropdown's right edge with button's right edge
                    dropdown.style.right = (window.innerWidth - rect.right) + "px";
                    dropdown.style.left = "auto";
                    dropdown.style.display = "block";
                }
            };

            document.addEventListener("click", () => {
                dropdown.style.display = "none";
            });

            // Append dropdown to document.body to ensure it's not clipped by table overflow
            document.body.appendChild(dropdown);
            
            // Clean up dropdown when row is destroyed
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.removedNodes.forEach((node) => {
                        if (node === row) {
                            dropdown.remove();
                        }
                    });
                });
            });
            if (row.parentNode) observer.observe(row.parentNode, { childList: true });
            else {
                // If not attached yet, wait a bit and observe tbody
                setTimeout(() => {
                    if (row.parentNode) observer.observe(row.parentNode, { childList: true });
                }, 100);
            }

            actionsWrapper.appendChild(menuBtn);
            tdDel.appendChild(actionsWrapper);
        }
        
        const handleEnterKey = (e) => {
            if (e.key === "Enter" || e.keyCode === 13) {
                e.preventDefault();
                console.log("Enter key pressed on element:", e.target);
                
                const tbody = document.getElementById("stamp-fields-tbody");
                if (!tbody) {
                    console.error("stamp-fields-tbody not found!");
                    return;
                }
                
                const rows = Array.from(tbody.querySelectorAll("tr.stamp-field-row"));
                let currentIndex = rows.indexOf(row);
                if (currentIndex === -1) {
                    const activeRow = e.target.closest("tr.stamp-field-row");
                    if (activeRow) {
                        currentIndex = rows.indexOf(activeRow);
                    }
                }
                
                console.log("Row index:", currentIndex, "Total rows:", rows.length);
                
                // Find next visible row
                let nextRow = null;
                for (let i = currentIndex + 1; i < rows.length; i++) {
                    if (rows[i].style.display !== "none") {
                        nextRow = rows[i];
                        break;
                    }
                }
                
                if (nextRow) {
                    console.log("Found next visible row:", nextRow);
                    // Try to focus the same column first
                    const currentTd = e.target.closest("td");
                    if (currentTd) {
                        const tdIndex = Array.from(row.children).indexOf(currentTd);
                        console.log("Current column index:", tdIndex);
                        if (tdIndex !== -1) {
                            const nextTd = nextRow.children[tdIndex];
                            let nextInput = nextTd ? nextTd.querySelector("input, select") : null;
                            
                            // If the same column input is readOnly/disabled, find the first editable one in that row
                            if (!nextInput || nextInput.readOnly || nextInput.disabled) {
                                console.log("Same column input is readOnly/disabled or missing. Locating first editable field in row.");
                                nextInput = Array.from(nextRow.querySelectorAll("input, select")).find(el => !el.readOnly && !el.disabled);
                            }
                            
                            if (nextInput) {
                                console.log("Focusing next input:", nextInput);
                                try {
                                    nextInput.focus();
                                    if (nextInput.select && typeof nextInput.select === "function") {
                                        nextInput.select();
                                    }
                                } catch (focusErr) {
                                    console.error("Error focusing/selecting input:", focusErr);
                                }
                                return;
                            }
                        }
                    }
                }
                
                // No more visible rows -> Save!
                console.log("No more visible rows. Triggering save...");
                const saveBtn = document.getElementById("btn-save-stamp");
                if (saveBtn) {
                    saveBtn.click();
                } else {
                    console.error("btn-save-stamp not found!");
                }
            }
        };

        nameInput.addEventListener("keydown", handleEnterKey);
        typeSelect.addEventListener("keydown", handleEnterKey);
        valueInput.addEventListener("keydown", handleEnterKey);

        row.appendChild(tdName);
        row.appendChild(tdType);
        row.appendChild(tdValue);
        row.appendChild(tdDel);
        
        return row;
    }

    addFieldBtn.addEventListener("click", () => {
        const tbody = document.getElementById("stamp-fields-tbody");
        if (tbody) {
            tbody.appendChild(createFieldRow("", "", "string", false));
        } else {
            fieldsContainer.appendChild(createFieldRow()); // fallback
        }
    });

    // Populate Modal
    window.openStampMetaEditor = async function(projectOrStamps, pdf_path, page, xref, title, stampName, stampsArray) {
        let stamps = [];
        let project = "";
        if (Array.isArray(projectOrStamps)) {
            stamps = projectOrStamps;
            project = window.currentProject || '';
        } else {
            project = projectOrStamps || window.currentProject || '';
            stamps = [{ project, pdf_path, page, xref, title, stampName }];
        }
        
        const isMulti = stamps.length > 1;
        document.getElementById("stamp-meta-title").textContent = "Loading Metadata...";
        fieldsContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #94a3b8;">Loading...</div>';
        
        currentStamp = stamps[0];
        window.currentStampsArray = stamps;
        
        // Show modal immediately so the user knows the click registered
        modal.style.display = "flex";
        
        try {
            // Load groups
            const groupRes = await stampAPI.getGroups(project);
            groupSelect.innerHTML = '<option value="">-- No System --</option>';
            groupRes.groups.forEach(g => {
                const opt = document.createElement("option");
                opt.value = g.id;
                opt.textContent = g.name;
                opt.style.color = g.color; // visual hint
                groupSelect.appendChild(opt);
            });
            
            // Load unique system pattern names for the Air Outlet dropdown
            const dataRes = await fetch(`/api/projects/${encodeURIComponent(project)}/data`);
            if (dataRes.ok) {
                const data = await dataRes.json();
                const systems = data.systems || [];
                const uniquePatterns = new Set();
                systems.forEach(s => {
                    let pat = s.pattern_name || s.name || "";
                    if (pat) {
                        const match = pat.match(/^(.*)[_\s\-]([^_\s\-]+)$/);
                        if (match) pat = match[1];
                        if (pat) uniquePatterns.add(pat);
                    }
                });
                
                const patSelect = document.getElementById("stamp-system-pattern-select");
                if (patSelect) {
                    patSelect.innerHTML = '<option value="">-- No System Pattern --</option>';
                    Array.from(uniquePatterns).sort().forEach(pat => {
                        const opt = document.createElement("option");
                        opt.value = pat;
                        opt.textContent = pat;
                        patSelect.appendChild(opt);
                    });
                }
            }

            // Load stamp meta for the first stamp
            const metaRes = await stampAPI.getStampMeta(project, currentStamp.pdf_path, currentStamp.page, currentStamp.xref);
            const meta = metaRes.metadata;
            
            if (isMulti) {
                document.getElementById("stamp-meta-title").textContent = `${stamps.length} stamps selected`;
                if (deleteBtn) deleteBtn.textContent = "Delete Stamps";
            } else {
                let pattern = meta.pattern_name;
                let number = "";
                if (meta.fields) {
                    const numField = meta.fields.find(f => f.name === "#");
                    if (numField) number = numField.value;
                }
                
                let singleName = "";
                if (pattern && number) {
                    singleName = `${pattern} ${number}`;
                } else if (pattern) {
                    singleName = pattern;
                } else {
                    singleName = currentStamp.title || currentStamp.stampName || currentStamp.xref;
                }

                document.getElementById("stamp-meta-title").textContent = "Name: " + singleName;
                if (deleteBtn) deleteBtn.textContent = "Delete Stamp";
            }
            
            fieldsContainer.innerHTML = "";
            
            const uuidDisplay = document.getElementById("stamp-meta-uuid");
            if (uuidDisplay) {
                if (isMulti) {
                    uuidDisplay.textContent = "";
                } else {
                    const hashStr = window.location.hash || "";
                    if (hashStr.startsWith("#stamp-")) {
                        uuidDisplay.textContent = "ID: " + decodeURIComponent(hashStr.substring(7));
                    } else {
                        uuidDisplay.textContent = "";
                    }
                }
            }
            
            let stampDisplayName = currentStamp.pattern_name || currentStamp.stampName || currentStamp.title || String(currentStamp.xref);
            let extractedStampNumber = stampDisplayName;
            if (typeof stampDisplayName === 'string') {
                const match = stampDisplayName.match(/^(.*)[_\s\-]([^_\s\-]+)$/);
                if (match) {
                    extractedStampNumber = match[2];
                }
            }
            
            const pdfNameVal = document.getElementById("stamp-pdf-name-value");
            const pdfUuidVal = document.getElementById("stamp-pdf-uuid-value");
            if (pdfNameVal) {
                pdfNameVal.textContent = isMulti ? "Multiple PDFs" : (meta.pdf_name || "Not Found");
            }
            if (pdfUuidVal) {
                pdfUuidVal.textContent = isMulti ? "Multiple UUIDs" : (meta.pdf_uuid || "Not Found");
            }
            
            if (meta.group) {
                groupSelect.value = meta.group.id;
            } else {
                groupSelect.value = "";
            }
            
            const typeSelect = document.getElementById("select-stamp-type");
            const patGroup = document.getElementById("stamp-system-pattern-group");
            const patSelect = document.getElementById("stamp-system-pattern-select");
            const aoTypeGroup = document.getElementById("stamp-air-outlet-type-group");
            const aoTypeSelect = document.getElementById("stamp-air-outlet-type-select");
            
            if (typeSelect) {
                typeSelect.value = meta.stamp_type || "air_outlet";
                if (patGroup) {
                    patGroup.style.display = typeSelect.value === "air_outlet" ? "block" : "none";
                }
                if (aoTypeGroup) {
                    aoTypeGroup.style.display = typeSelect.value === "air_outlet" ? "block" : "none";
                }
                typeSelect.addEventListener("change", (e) => {
                    if (patGroup) {
                        patGroup.style.display = e.target.value === "air_outlet" ? "block" : "none";
                    }
                    if (aoTypeGroup) {
                        aoTypeGroup.style.display = e.target.value === "air_outlet" ? "block" : "none";
                    }
                });
            }

            if (patSelect) {
                const patField = meta.fields ? meta.fields.find(f => f.name === "System Pattern") : null;
                patSelect.value = patField ? patField.value : "";
            }
            
            if (aoTypeSelect) {
                const basePat = meta.pattern_name || "";
                aoTypeSelect.value = basePat;
                if (basePat && !Array.from(aoTypeSelect.options).some(o => o.value === basePat)) {
                    const opt = document.createElement("option");
                    opt.value = basePat;
                    opt.textContent = basePat;
                    aoTypeSelect.appendChild(opt);
                    aoTypeSelect.value = basePat;
                }
            }
            
            if (isMulti) {
                let unionFields = [];
                let unionFieldNames = new Set();
                
                stamps.forEach(s => {
                    if (s.fields) {
                        Object.entries(s.fields).forEach(([k, v]) => {
                            if (!unionFieldNames.has(k)) {
                                unionFieldNames.add(k);
                                unionFields.push({ name: k, value: v, type: "string", _values: new Set([v]), formula_expression: "", conditional_formatting: "" });
                            } else {
                                let existing = unionFields.find(f => f.name === k);
                                if (existing && existing._values) {
                                    existing._values.add(v);
                                    if (existing._values.size > 1) {
                                        existing.value = "<Multiple Values>";
                                    }
                                }
                            }
                        });
                    }
                });
                
                meta.fields.forEach(f => {
                    if (!unionFieldNames.has(f.name)) {
                        unionFieldNames.add(f.name);
                        unionFields.push({ ...f, _values: new Set([f.value]), formula_expression: f.formula_expression || "", conditional_formatting: f.conditional_formatting || "" });
                    } else {
                        let existing = unionFields.find(uf => uf.name === f.name);
                        if (existing && existing._values) {
                            existing._values.add(f.value);
                            if (existing._values.size > 1) {
                                existing.value = "<Multiple Values>";
                            }
                        }
                    }
                });
                
                meta.fields = unionFields;
            }
            
            fieldsContainer.innerHTML = `
                <div class="stamp-fields-scroll-wrapper">
                    <table class="stamp-fields-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th style="width: 80px;">Type</th>
                                <th>Value</th>
                                <th style="width: 40px;"></th>
                            </tr>
                        </thead>
                        <tbody id="stamp-fields-tbody"></tbody>
                    </table>
                </div>
            `;
            
            const tbody = document.getElementById("stamp-fields-tbody");
            const showMoreDiv = document.getElementById("stamp-fields-show-more");
            const showMoreBtn = showMoreDiv ? showMoreDiv.querySelector("span") : null;
            
            if (showMoreDiv) {
                showMoreDiv.style.display = "none";
            }
            if (showMoreBtn) {
                showMoreBtn.textContent = "Show more";
            }
            
            let hiddenCount = 0;
            for (const f of meta.fields) {
                const isHiddenField = f.name === "#" && !f.value && !f.formula_expression;
                if (!isHiddenField) {
                    const r = createFieldRow(f.name, f.value, f.type, false, f.name === "#", f.formula_expression || "", f.conditional_formatting || "");
                    tbody.appendChild(r);
                    if (f.conditional_formatting) {
                        evaluateRowConditionalFormatting(r);
                    }
                } else {
                    hiddenCount++;
                }
            }
            
            if (hiddenCount === 1) {
                const numRow = createFieldRow("#", "", "string", true, true);
                numRow.dataset.permanentHidden = "true";
                tbody.insertBefore(numRow, tbody.firstChild);
            }
            
            if (meta.fields.length === 0) {
                tbody.appendChild(createFieldRow("", "", "string", false, false, "", ""));
            }

            if (hiddenCount > 0 && showMoreDiv && showMoreBtn) {
                showMoreDiv.style.display = "block";
                showMoreBtn.onclick = () => {
                    const isExpanded = showMoreBtn.textContent === "Show less";
                    const visibleRows = Array.from(tbody.querySelectorAll("tr.stamp-field-row")).filter(r => r.dataset.permanentHidden !== "true");
                    visibleRows.forEach((row, idx) => {
                        if (idx >= 5) {
                            row.style.display = isExpanded ? "none" : "";
                        }
                    });
                    showMoreBtn.textContent = isExpanded ? "Show more" : "Show less";
                };
            }
            
        } catch (e) {
            document.getElementById("stamp-meta-title").textContent = "Error";
            fieldsContainer.innerHTML = `<div style="color:red; padding: 10px;">Error loading metadata: ${e.message}</div>`;
        }
    };

    saveBtn.addEventListener("click", async () => {
        if (!currentStamp) return;
        
        const fields = [];
        const fieldNames = new Set();
        let valid = true;
        let duplicateName = "";
        
        const rowsData = [];
        
        fieldsContainer.querySelectorAll(".stamp-field-row").forEach(row => {
            const inputs = row.querySelectorAll("input");
            const select = row.querySelector("select");
            const name = inputs[0].value.trim();
            const value = inputs[1].value.trim();
            const type = select.value;
            let formula_expression = row.dataset.formula || "";
            
            if (type === "formula") {
                if (!formula_expression || (value !== "(Formula)" && value !== "<Multiple Values>" && value !== row.dataset.loadedValue)) {
                    formula_expression = value;
                    row.dataset.formula = value;
                }
            }
            
            if (name) {
                if (fieldNames.has(name.toLowerCase())) {
                    valid = false;
                    duplicateName = name;
                }
                fieldNames.add(name.toLowerCase());
                rowsData.push({ 
                    name, 
                    value, 
                    type, 
                    formula_expression, 
                    conditional_formatting: row.dataset.conditionalFormatting || "",
                    inputElem: inputs[1] 
                });
            }
        });
        
        if (!valid) {
            alert(`Duplicate Field Error: The field "${duplicateName}" already exists. Please remove or rename the duplicate field.`);
            return;
        }
               const fieldsToProcess = rowsData;
        
        let groupId = groupSelect.value ? parseInt(groupSelect.value) : null;
        
        const typeSelect = document.getElementById("select-stamp-type");
        const stampType = typeSelect ? typeSelect.value : "air_outlet";
        
        const patSelect = document.getElementById("stamp-system-pattern-select");
        if (stampType === "air_outlet" && patSelect && patSelect.value) {
            const existingPatField = fieldsToProcess.find(f => f.name === "System Pattern");
            if (existingPatField) {
                existingPatField.value = patSelect.value;
            } else {
                fieldsToProcess.push({ name: "System Pattern", value: patSelect.value, type: "string" });
            }
        }
        
        const aoTypeSelect = document.getElementById("stamp-air-outlet-type-select");
        let newPatternName = undefined;
        if (stampType === "air_outlet" && aoTypeSelect && aoTypeSelect.value) {
            newPatternName = aoTypeSelect.value;
        }
        
        try {
            const stamps = window.currentStampsArray || [currentStamp];
            
            // 1. Calculate local updates instantly
            const updatesToPush = [];
            
            for (const stamp of stamps) {
                const proj = stamp.project || currentStamp.project || window.currentProject || document.getElementById("current-project-label")?.textContent || "";
                
                let currentNum = "";
                let stampSpecificFields = fieldsToProcess.map(f => {
                    let val = f.value;
                    if (f.name === '#') {
                        let num = stamp.stampName || stamp.xref || "";
                        if (stamp.fields && stamp.fields['#']) {
                            num = stamp.fields['#'];
                        } else {
                            const m = String(num).match(/^(.*)[_\s\-]([^_\s\-]+)$/);
                            if (m) num = m[2];
                        }
                        currentNum = num;
                        val = num;
                    } else if (f.value === "<Multiple Values>") {
                        if (stamp.fields && stamp.fields[f.name] !== undefined) {
                            val = stamp.fields[f.name];
                        } else {
                            val = "";
                        }
                    }
                    return { ...f, value: val };
                });
                
                // Evaluate formulas per stamp
                const fieldMap = {};
                stampSpecificFields.forEach(r => { if (r.type !== 'formula') fieldMap[r.name.toLowerCase()] = r.value; });
                
                stampSpecificFields = stampSpecificFields.map(r => {
                    if (r.type === 'formula' && r.formula_expression) {
                        const match = r.formula_expression.match(/^(.*?)\s+([\+\-\*\/\%])\s+(.*)$/);
                        let evalVal = "";
                        if (match) {
                            let op1 = match[1].trim();
                            let op = match[2].trim();
                            let op2 = match[3].trim();
                            
                            let val1 = isNaN(parseFloat(op1)) ? (fieldMap[op1.toLowerCase()] || 0) : parseFloat(op1);
                            let val2 = isNaN(parseFloat(op2)) ? (fieldMap[op2.toLowerCase()] || 0) : parseFloat(op2);
                            
                            val1 = parseFloat(val1) || 0;
                            val2 = parseFloat(val2) || 0;
                            
                            switch (op) {
                                case '+': evalVal = val1 + val2; break;
                                case '-': evalVal = val1 - val2; break;
                                case '*': evalVal = val1 * val2; break;
                                case '/': evalVal = val2 !== 0 ? val1 / val2 : 0; break;
                                case '%': evalVal = val2 !== 0 ? val1 % val2 : 0; break;
                            }
                            evalVal = Math.round(evalVal * 100) / 100;
                        } else {
                            let single = r.formula_expression.trim();
                            evalVal = fieldMap[single.toLowerCase()] || single;
                        }
                        
                        // Update UI input as well if editing single stamp
                        if (stamps.length === 1 && r.inputElem) {
                            r.inputElem.value = evalVal;
                        }
                        
                        return { name: r.name, value: String(evalVal), type: r.type, formula_expression: r.formula_expression, conditional_formatting: r.conditional_formatting };
                    }
                    return { name: r.name, value: String(r.value), type: r.type, formula_expression: r.formula_expression, conditional_formatting: r.conditional_formatting };
                });
                
                let finalPatternName = newPatternName;
                if (finalPatternName && currentNum) {
                    finalPatternName = `${finalPatternName}_${currentNum}`;
                }
                
                // Update local memory instantly
                if (window.currentPdfStamps) {
                    const localStamp = window.currentPdfStamps.find(s => s.xref === stamp.xref);
                    if (localStamp) {
                        localStamp.fields = stampSpecificFields;
                    }
                }
                
                updatesToPush.push({ proj, pdf_path: stamp.pdf_path, page: stamp.page, xref: stamp.xref, fields: stampSpecificFields, groupId, stampType, finalPatternName });
            }

            // Instantly redraw visual and close modal
            if (window.redrawStampVisuals) window.redrawStampVisuals();
            closeModal();

            // 2. Perform API calls in the background without blocking the UI
            (async () => {
                try {
                    for (const up of updatesToPush) {
                        await stampAPI.updateStampMeta(up.proj, up.pdf_path, up.page, up.xref, up.fields, up.groupId, up.stampType, up.finalPatternName);
                    }
                    
                    // Apply tag rules to update stamp shapes/colors based on saved changes
                    const projectForRules = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
                    if (projectForRules) {
                        try {
                            await fetch('/api/manage_tags/apply_rules', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ project: projectForRules })
                            });
                        } catch (rulesErr) {
                            console.warn('apply_rules after stamp save failed:', rulesErr);
                        }
                    }
                    
                    // Trigger visual update if needed to fetch updated colors/shapes from apply_rules
                    if (window.refreshStampVisuals) window.refreshStampVisuals();

                    // Refresh data viewer if it is active (after API update)
                    const dataViewer = document.getElementById("data-viewer-container");
                    if (dataViewer && dataViewer.style.display !== "none") {
                        const btnViewData = document.getElementById("btn-view-project-data");
                        if (btnViewData) btnViewData.click();
                    }
                } catch (apiErr) {
                    console.error("Background save failed:", apiErr);
                }
            })();

        } catch (e) {
            alert("Error saving metadata: " + e.message);
        }
    });


    if (deleteBtn) {
        deleteBtn.addEventListener("click", async () => {
            if (!currentStamp) return;
            
            const stamps = window.currentStampsArray || [currentStamp];
            const isMulti = stamps.length > 1;
            
            if (!confirm(`Are you sure you want to delete ${isMulti ? stamps.length + ' selected stamps' : 'this stamp'}?`)) return;
            
            let forceAll = false;
            let deletedCount = 0;
            
            for (const stamp of stamps) {
                const pdfToUse = stamp.pdf_path || currentStamp.pdf_path;
                if (window.deleteStampByXref && !isMulti) {
                    const deleted = await window.deleteStampByXref(stamp.xref, true);
                    if (deleted) deletedCount++;
                } else {
                    const useForce = forceAll;
                    const url = `/api/pdf/${encodeURIComponent(pdfToUse)}/stamps/${stamp.xref}` + (useForce ? "?force=true" : "");
                    try {
                        let res = await fetch(url, { method: "DELETE" });
                        if (!res.ok) {
                            const data = await res.json();
                            let shouldForce = forceAll;
                            if (!shouldForce) {
                                shouldForce = confirm(`Failed to delete stamp from PDF (${data.error || 'Not found'}). Force-delete this and automatically force-delete any other failing stamps?`);
                                if (shouldForce) forceAll = true;
                            }
                            if (shouldForce && !useForce) {
                                const forceRes = await fetch(`/api/pdf/${encodeURIComponent(pdfToUse)}/stamps/${stamp.xref}?force=true`, { method: "DELETE" });
                                if (forceRes.ok) deletedCount++;
                            }
                        } else {
                            deletedCount++;
                        }
                    } catch (err) {
                        console.error(err);
                    }
                }
            }
            
            if (deletedCount > 0) {
                closeModal();
                if (window.refreshStampVisuals) window.refreshStampVisuals();
                
                // Refresh data viewer if it is active
                const dataViewer = document.getElementById("data-viewer-container");
                if (dataViewer && dataViewer.style.display !== "none") {
                    const btnViewData = document.getElementById("btn-view-project-data");
                    if (btnViewData) btnViewData.click();
                }
            }
        });
    }

    // New Group Modal
    newGroupBtn.addEventListener("click", () => {
        groupModal.style.display = "flex";
    });
    
    closeGroupBtn.addEventListener("click", () => {
        groupModal.style.display = "none";
    });
    
    saveGroupBtn.addEventListener("click", async () => {
        const name = document.getElementById("new-group-name").value.trim();
        const color = document.getElementById("new-group-color").value;
        if (!name || !currentStamp) return;
        
        try {
            const res = await stampAPI.createGroup(currentStamp.project, name, color);
            
            // add to select and select it
            const opt = document.createElement("option");
            opt.value = res.group_id;
            opt.textContent = name;
            opt.style.color = color;
            groupSelect.appendChild(opt);
            groupSelect.value = res.group_id;
            
            groupModal.style.display = "none";
            document.getElementById("new-group-name").value = "";
        } catch(e) {
            alert("Error creating group: " + e.message);
        }
    });

    // --- Word Report Generator Integration ---
    const tplSelect = document.getElementById("select-report-template");
    const uploadTplBtn = document.getElementById("btn-upload-template");
    const uploadTplInput = document.getElementById("template-upload-input");
    const generateReportBtn = document.getElementById("btn-generate-report");
    const btnMapTemplate = document.getElementById("btn-map-template");



    window.loadTemplates = async function() {
        const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
        if (!project || project === "—") {
            tplSelect.innerHTML = '<option value="">-- Select Template --</option>';
            generateReportBtn.disabled = true;
            btnMapTemplate.disabled = true;
            return;
        }

        if (window.location.hash === '#Project%20Data' || window.location.hash === '#Project Data') {
            setTimeout(() => {
                const btnViewData = document.getElementById("btn-view-project-data");
                if (btnViewData) btnViewData.click();
            }, 200);
        }

        const selectedVal = tplSelect.value;

        try {
            const res = await fetch(`/api/projects/${encodeURIComponent(project)}/templates`);
            if (!res.ok) throw new Error("Failed to load templates");
            const templates = await res.json();
            
            if (templates.length === 0) {
                tplSelect.innerHTML = '<option value="">-- No Templates Uploaded --</option>';
                generateReportBtn.disabled = true;
                btnMapTemplate.disabled = true;
            } else {
                tplSelect.innerHTML = '<option value="">-- Select Template --</option>';
                templates.forEach(t => {
                    const opt = document.createElement("option");
                    opt.value = t.name;
                    opt.textContent = t.name;
                    tplSelect.appendChild(opt);
                });
                
                // Restore selection if it still exists, otherwise select first
                if (selectedVal && templates.some(t => t.name === selectedVal)) {
                    tplSelect.value = selectedVal;
                } else if (templates.length > 0) {
                    tplSelect.value = templates[0].name;
                }
                
                generateReportBtn.disabled = !tplSelect.value;
                btnMapTemplate.disabled = !tplSelect.value;

                if ((window.location.hash === '#Template%20Preview' || window.location.hash === '#Template Preview') && tplSelect.value) {
                    setTimeout(() => {
                        openTemplatePreview();
                    }, 200);
                }
            }
        } catch (e) {
            console.error("Error loading templates:", e);
        }
    }

    // Enable/disable generate button based on selection
    tplSelect.addEventListener("change", () => {
        generateReportBtn.disabled = !tplSelect.value;
        btnMapTemplate.disabled = !tplSelect.value;
    });

    // Load templates only when the dropdown gains focus (fallback)
    tplSelect.addEventListener("focus", window.loadTemplates);

    // Trigger file selection for template upload
    uploadTplBtn.addEventListener("click", () => {
        uploadTplInput.click();
    });

    // Handle template file upload
    uploadTplInput.addEventListener("change", async () => {
        const file = uploadTplInput.files[0];
        if (!file) return;

        const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
        if (!project || project === "—") {
            alert("Please select a project first.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch(`/api/projects/${encodeURIComponent(project)}/templates/upload`, {
                method: "POST",
                body: formData
            });
            if (!res.ok) throw new Error("Upload failed");
            const data = await res.json();
            alert(`Template '${data.name}' uploaded successfully!`);
            await window.loadTemplates();
            tplSelect.value = data.name;
            generateReportBtn.disabled = false;
            btnMapTemplate.disabled = false;
        } catch (e) {
            alert("Error uploading template: " + e.message);
        } finally {
            uploadTplInput.value = ""; // clear input
        }
    });

    // Handle report generation click
    if (btnMapTemplate) {
        btnMapTemplate.addEventListener("click", () => {
            openTemplatePreview();
        });
    }

    generateReportBtn.addEventListener("click", async () => {
        const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
        const pdf = window.currentPdf;
        const templateName = tplSelect.value;

        if (!project || !pdf || !templateName) {
            alert("Please select a project, PDF, and report template first.");
            return;
        }

        generateReportBtn.disabled = true;
        const originalText = generateReportBtn.innerHTML;
        generateReportBtn.innerHTML = "⏳ Generating...";

        try {
            const res = await fetch(`/api/projects/${encodeURIComponent(project)}/pdf/${encodeURIComponent(pdf)}/render`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ template_name: templateName })
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || "Failed to generate report");
            }

            // Stream download to client
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `Report_${pdf.split("/").pop().replace(".pdf", "")}.docx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

        } catch (e) {
            alert("Error generating report: " + e.message);
        } finally {
            generateReportBtn.disabled = false;
            generateReportBtn.innerHTML = originalText;
        }
    });

    // --- Visual Schema Mapper ---
    const viewerContainer = document.getElementById("viewer-container");
    const schemaMapperContainer = document.getElementById("schema-mapper-container");
    const btnCloseMapper = document.getElementById("btn-close-mapper");
    const btnSaveMapping = document.getElementById("btn-save-mapping");
    const mapperDbFields = document.getElementById("mapper-db-fields");
    const mapperTemplateColumns = document.getElementById("mapper-template-columns");

    let currentMapping = {};
    let availableDbFields = [];

    btnMapTemplate.addEventListener("click", async () => {
        const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
        const templateName = tplSelect.value;

        if (!project || project === "—" || !templateName) {
            alert("Please select a template to map.");
            return;
        }

        // Hide viewer, show mapper
        viewerContainer.style.display = "none";
        schemaMapperContainer.style.display = "flex";
        
        switchToolbarPanel('toolbar-schema-mapper');

        try {
            // Fetch DB Fields
            const fieldsRes = await fetch(`/api/projects/${encodeURIComponent(project)}/fields`);
            const fieldsData = await fieldsRes.json();
            availableDbFields = fieldsData.fields || [];

            // Fetch Template Columns
            const colsRes = await fetch(`/api/projects/${encodeURIComponent(project)}/templates/${encodeURIComponent(templateName)}/columns`);
            const colsData = await colsRes.json();
            const templateColumns = colsData.columns || [];

            // Fetch current mapping
            const mapRes = await fetch(`/api/projects/${encodeURIComponent(project)}/templates/${encodeURIComponent(templateName)}/mapping`);
            const mapData = await mapRes.json();
            currentMapping = mapData.mapping || {};

            renderMapperUI(templateColumns);
        } catch (e) {
            alert("Error loading schema mapper: " + e.message);
        }
    });

    btnCloseMapper.addEventListener("click", () => {
        schemaMapperContainer.style.display = "none";
        viewerContainer.style.display = "block";
        
        switchToolbarPanel('toolbar-pdf-tools');
    });

    function renderMapperUI(templateColumns) {
        mapperDbFields.innerHTML = "";
        mapperTemplateColumns.innerHTML = "";

        // Render draggable DB Fields
        availableDbFields.forEach(field => {
            const pill = document.createElement("div");
            pill.className = "db-field-pill";
            pill.textContent = field;
            pill.draggable = true;
            pill.style.padding = "8px 12px";
            pill.style.background = "rgba(59,130,246,0.2)";
            pill.style.border = "1px solid rgba(59,130,246,0.5)";
            pill.style.borderRadius = "16px";
            pill.style.cursor = "grab";
            pill.style.userSelect = "none";

            pill.addEventListener("dragstart", (e) => {
                e.dataTransfer.setData("text/plain", field);
                pill.style.opacity = "0.5";
            });
            pill.addEventListener("dragend", () => {
                pill.style.opacity = "1";
            });

            mapperDbFields.appendChild(pill);
        });

        // Render Template Column drop zones
        templateColumns.forEach(col => {
            const row = document.createElement("div");
            row.style.display = "flex";
            row.style.alignItems = "center";
            row.style.justifyContent = "space-between";
            row.style.padding = "10px";
            row.style.background = "rgba(255,255,255,0.05)";
            row.style.border = "1px solid rgba(255,255,255,0.1)";
            row.style.borderRadius = "6px";

            const colNameSpan = document.createElement("span");
            colNameSpan.textContent = col;
            colNameSpan.style.fontWeight = "bold";
            colNameSpan.style.flex = "1";

            const arrowSpan = document.createElement("span");
            arrowSpan.textContent = "⬅️ mapped to ⬅️";
            arrowSpan.style.color = "var(--text-secondary)";
            arrowSpan.style.margin = "0 15px";

            // Drop zone / Select box
            const selectBox = document.createElement("select");
            selectBox.className = "project-select";
            selectBox.style.flex = "1";
            selectBox.style.padding = "6px";

            const optDefault = document.createElement("option");
            optDefault.value = "";
            optDefault.textContent = "-- Map to Field --";
            selectBox.appendChild(optDefault);

            availableDbFields.forEach(f => {
                const opt = document.createElement("option");
                opt.value = f;
                opt.textContent = f;
                selectBox.appendChild(opt);
            });

            // Set current mapped value or default to matching name
            if (currentMapping[col]) {
                selectBox.value = currentMapping[col];
            } else if (availableDbFields.includes(col)) {
                selectBox.value = col; // auto-map
                currentMapping[col] = col;
            }

            selectBox.addEventListener("change", (e) => {
                currentMapping[col] = e.target.value;
            });

            // Make the row a drop zone
            row.addEventListener("dragover", (e) => {
                e.preventDefault();
                row.style.borderColor = "var(--neon-cyan)";
                row.style.background = "rgba(0, 255, 255, 0.1)";
            });

            row.addEventListener("dragleave", () => {
                row.style.borderColor = "rgba(255,255,255,0.1)";
                row.style.background = "rgba(255,255,255,0.05)";
            });

            row.addEventListener("drop", (e) => {
                e.preventDefault();
                row.style.borderColor = "rgba(255,255,255,0.1)";
                row.style.background = "rgba(255,255,255,0.05)";
                const droppedField = e.dataTransfer.getData("text/plain");
                if (availableDbFields.includes(droppedField)) {
                    selectBox.value = droppedField;
                    currentMapping[col] = droppedField;
                }
            });

            row.appendChild(colNameSpan);
            row.appendChild(arrowSpan);
            row.appendChild(selectBox);

            mapperTemplateColumns.appendChild(row);
        });
    }

    btnSaveMapping.addEventListener("click", async () => {
        const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
        const templateName = tplSelect.value;
        if (!project || !templateName) return;

        btnSaveMapping.textContent = "Saving...";
        btnSaveMapping.disabled = true;

        // Clean up empty mappings
        const cleanedMapping = {};
        for (const [k, v] of Object.entries(currentMapping)) {
            if (v) cleanedMapping[k] = v;
        }

        try {
            const res = await fetch(`/api/projects/${encodeURIComponent(project)}/templates/${encodeURIComponent(templateName)}/mapping`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mapping: cleanedMapping })
            });

            if (!res.ok) throw new Error("Failed to save mapping");
            
            // Show success briefly
            btnSaveMapping.textContent = "Saved!";
            btnSaveMapping.style.background = "var(--neon-cyan)";
            btnSaveMapping.style.color = "#000";
            
            setTimeout(() => {
                btnSaveMapping.textContent = "Save Mapping";
                btnSaveMapping.style.background = "";
                btnSaveMapping.style.color = "";
                btnSaveMapping.disabled = false;
            }, 1500);

        } catch (e) {
            alert("Error saving mapping: " + e.message);
            btnSaveMapping.textContent = "Save Mapping";
            btnSaveMapping.disabled = false;
        }
    });

    // --- Template Preview Overlay ---
    const btnPreviewTemplate = document.getElementById("btn-preview-template");

    // The live overlay element — created on demand and appended to body
    let tplPreviewOverlay = null;

    /**
     * Build and show the fullscreen template preview overlay.
     * Fetches /preview endpoint, renders the DOCX table, wires up drag-and-drop.
     */
    async function openTemplatePreview() {
        window.location.hash = 'Template%20Preview';
        const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
        const templateName = tplSelect.value;
        if (!project || project === "—" || !templateName) {
            alert("Please select a template to preview.");
            return;
        }

        if (btnPreviewTemplate) {
            btnPreviewTemplate.disabled = true;
            btnPreviewTemplate.innerHTML = "<span>⏳</span> Loading…";
        }

        let previewData;
        try {
            // Fetch DB Fields if they are empty
            if (!availableDbFields || availableDbFields.length === 0) {
                const fieldsRes = await fetch(`/api/projects/${encodeURIComponent(project)}/fields`);
                if (fieldsRes.ok) {
                    const fData = await fieldsRes.json();
                    availableDbFields = fData.fields || [];
                }
            }

            const res = await fetch(`/api/projects/${encodeURIComponent(project)}/templates/${encodeURIComponent(templateName)}/preview`);
            if (!res.ok) throw new Error(await res.text());
            const json = await res.json();
            if (!json.success) throw new Error(json.error || "Unknown error");
            previewData = json.preview;
        } catch (e) {
            alert("Error loading template preview: " + e.message);
            if (btnPreviewTemplate) {
                btnPreviewTemplate.disabled = false;
                btnPreviewTemplate.innerHTML = "<span>🔲</span> Preview Template";
            }
            return;
        }

        // Remove existing overlay if any
        if (tplPreviewOverlay) tplPreviewOverlay.remove();

        // Build overlay
        tplPreviewOverlay = document.createElement("div");
        tplPreviewOverlay.className = "tpl-preview-overlay";
        tplPreviewOverlay.id = "tpl-preview-overlay";

        // ── Header ──
        const hdr = document.createElement("div");
        hdr.className = "tpl-preview-header";

        // Home button
        const homeBtn = document.createElement("a");
        homeBtn.href = "/home";
        homeBtn.title = "Back to Projects";
        homeBtn.textContent = "← Home";
        homeBtn.style.cssText = `
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px;
            color: #94a3b8;
            font-family: 'Inter', sans-serif;
            font-size: 0.82rem;
            font-weight: 500;
            text-decoration: none;
            margin-left: 8px;
            margin-right: 14px;
            transition: background 0.2s, color 0.2s, border-color 0.2s;
            white-space: nowrap;
            flex-shrink: 0;
        `;
        homeBtn.addEventListener("mouseover", () => {
            homeBtn.style.background = "rgba(59,130,246,0.15)";
            homeBtn.style.color = "#93c5fd";
            homeBtn.style.borderColor = "rgba(59,130,246,0.35)";
        });
        homeBtn.addEventListener("mouseout", () => {
            homeBtn.style.background = "rgba(255,255,255,0.06)";
            homeBtn.style.color = "#94a3b8";
            homeBtn.style.borderColor = "rgba(255,255,255,0.1)";
        });
        hdr.appendChild(homeBtn);

        // Project Name
        const projName = document.createElement("h1");
        projName.style.cssText = `
            font-family: 'Outfit', sans-serif;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--neon-cyan);
            margin: 0 14px 0 0;
            white-space: nowrap;
            flex-shrink: 0;
        `;
        projName.textContent = document.getElementById("logo-project-name")?.textContent || project || "Vector PDF Inspector";
        hdr.appendChild(projName);

        // Divider
        const divider = document.createElement("span");
        divider.className = "divider";
        divider.style.margin = "0 14px 0 0";
        hdr.appendChild(divider);

        const title = document.createElement("h2");
        title.textContent = `🔲 Template Preview — ${templateName}`;
        hdr.appendChild(title);

        // Sync & close button
        const syncBtn = document.createElement("button");
        syncBtn.className = "btn primary-btn";
        syncBtn.textContent = "✔ Apply & Close";
        syncBtn.addEventListener("click", () => {
            closeTplPreview(true);
        });
        hdr.appendChild(syncBtn);

        const discardBtn = document.createElement("button");
        discardBtn.className = "btn";
        discardBtn.style.marginLeft = "8px";
        discardBtn.textContent = "✕ Discard";
        discardBtn.addEventListener("click", () => {
            closeTplPreview(false);
        });
        hdr.appendChild(discardBtn);

        tplPreviewOverlay.appendChild(hdr);

        // ── Body ──
        const body = document.createElement("div");
        body.className = "tpl-preview-body";

        // ── Left: field pills ──
        const fieldsPanel = document.createElement("div");
        fieldsPanel.className = "tpl-preview-fields";

        const fieldsPanelTitle = document.createElement("h3");
        fieldsPanelTitle.textContent = "DB Fields";
        fieldsPanel.appendChild(fieldsPanelTitle);

        const fieldsList = document.createElement("div");
        fieldsList.className = "tpl-preview-fields-list";

        availableDbFields.forEach(field => {
            const pill = document.createElement("div");
            pill.className = "tpl-field-pill";
            pill.textContent = field;
            pill.draggable = true;

            pill.addEventListener("dragstart", (e) => {
                e.dataTransfer.setData("text/tpl-field", field);
                e.dataTransfer.effectAllowed = "copy";
                pill.classList.add("dragging");
            });
            pill.addEventListener("dragend", () => {
                pill.classList.remove("dragging");
            });

            fieldsList.appendChild(pill);
        });

        fieldsPanel.appendChild(fieldsList);
        body.appendChild(fieldsPanel);

        // ── Right: table wrapper ──
        const tableWrap = document.createElement("div");
        tableWrap.className = "tpl-preview-table-wrap tpl-doc-page-wrap";

        const docPage = document.createElement("div");
        docPage.className = "tpl-doc-page";

        // Build the interactive table first so we have the element
        if (previewData.blocks) {
            // New MS Word COM HTML integration
            docPage.style.padding = "0";
            docPage.style.background = "transparent";
            docPage.style.boxShadow = "none";
            docPage.style.width = "max-content"; // Let it size to the iframe
            docPage.style.minHeight = "0";
            docPage.innerHTML = `<iframe id="tpl-html-iframe" scrolling="no" style="width:8.5in; height:11in; border:none; background:white; box-shadow: 0 0 10px rgba(0,0,0,0.5); display:block; margin: 0 auto; transform-origin: top center;"></iframe>`;
            const iframe = docPage.querySelector("#tpl-html-iframe");
            iframe.dataset.userZoom = "1";
            
            tableWrap.appendChild(docPage);
            body.appendChild(tableWrap);
            tplPreviewOverlay.appendChild(body);
            document.body.appendChild(tplPreviewOverlay);

            try {
                const docxRes = await fetch(`/api/projects/${encodeURIComponent(project)}/templates/${encodeURIComponent(templateName)}/preview_html`);
                if (!docxRes.ok) throw new Error("Failed to generate raw template HTML");
                const htmlData = await docxRes.json();
                if (!htmlData.success) throw new Error(htmlData.error || "Failed to generate HTML");

                // Load iframe
                await new Promise((resolve, reject) => {
                    iframe.onload = () => {
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        // Inject CSS into iframe to style our drag/drop hitboxes
                        const style = iframeDoc.createElement('style');
                        style.textContent = `
                            html, body { margin: 0 !important; padding: 0 !important; }
                            div.WordSection1 { display: inline-block; min-width: 100%; padding: 0.4in 0.6in 0.2in 0.6in !important; box-sizing: border-box; }
                            .tpl-mappable-header { transition: background-color 0.2s, box-shadow 0.2s; cursor: crosshair; position: relative; }
                            .tpl-mappable-header:hover { background-color: rgba(59, 130, 246, 0.1) !important; box-shadow: inset 0 0 0 2px #22d3ee; }
                            .tpl-mapped-badge {
                                position: absolute; bottom: 2px; right: 2px; font-size: 9px;
                                background: #0ea5e9; color: white; padding: 1px 4px; border-radius: 4px;
                                display: flex; gap: 4px; align-items: center; z-index: 10;
                            }
                            .tpl-badge-remove { cursor: pointer; color: #ffcccc; font-weight: bold; }
                            .tpl-badge-remove:hover { color: white; }
                        `;
                        iframeDoc.head.appendChild(style);
                        
                        let baseScale = 1;

                        // Auto-resize iframe to fit the exact document height
                        window.recalcTemplateScale = () => {
                            // Find out true scrollWidth by temporarily disabling hidden overflow
                            iframeDoc.body.style.overflow = 'auto';
                            iframeDoc.documentElement.style.overflow = 'auto';
                            
                            const maxTableWidth = Math.max(0, ...Array.from(iframeDoc.querySelectorAll('table')).map(t => t.scrollWidth));
                            const scrollW = Math.max(iframeDoc.documentElement.scrollWidth, iframeDoc.body.scrollWidth, maxTableWidth);
                            const scrollH = Math.max(iframeDoc.documentElement.scrollHeight, iframeDoc.body.scrollHeight);
                            
                            // 8.5in at 96 DPI
                            const targetW = 816; 
                            if (scrollW > targetW) {
                                baseScale = targetW / scrollW;
                                iframe.style.width = scrollW + "px";
                                iframe.style.height = scrollH + "px";
                                docPage.style.width = targetW + "px";
                                docPage.style.height = (scrollH * baseScale) + "px";
                            } else {
                                baseScale = 1;
                                if (scrollH > 100) iframe.style.height = scrollH + "px";
                                if (scrollW > 100) iframe.style.width = scrollW + "px";
                                docPage.style.width = Math.max(targetW, scrollW) + "px";
                                docPage.style.height = scrollH + "px";
                            }
                            
                            // Re-apply overflow hidden to clip any stray elements and prevent iframe internal scrollbars
                            iframeDoc.body.style.overflow = 'hidden';
                            iframeDoc.documentElement.style.overflow = 'hidden';
                            
                            applyZoom();
                        };

                        // Apply initial zoom slider value
                        const applyZoom = () => {
                            const userZoom = parseFloat(iframe.dataset.userZoom);
                            const finalScale = baseScale * userZoom;
                            iframe.style.transform = `scale(${finalScale})`;
                            
                            // Adjust docPage height so the container grows/shrinks with zoom
                            const trueH = parseInt(iframe.style.height) || 1000;
                            const trueW = parseInt(iframe.style.width) || 816;
                            docPage.style.height = (trueH * finalScale) + "px";
                            docPage.style.width = (trueW * finalScale) + "px";
                        };

                        setTimeout(() => {
                            window.recalcTemplateScale();
                            
                            // Wheel Zoom
                            tableWrap.addEventListener("wheel", (e) => {
                                if (e.ctrlKey || e.metaKey) {
                                    e.preventDefault();
                                    const delta = e.deltaY > 0 ? -0.1 : 0.1;
                                    let userZoom = parseFloat(iframe.dataset.userZoom);
                                    userZoom = Math.max(0.2, Math.min(5, userZoom + delta));
                                    iframe.dataset.userZoom = userZoom.toString();
                                    applyZoom();
                                }
                            });
                            
                            // Also attach to iframe document
                            iframeDoc.addEventListener("wheel", (e) => {
                                if (e.ctrlKey || e.metaKey) {
                                    e.preventDefault();
                                    const delta = e.deltaY > 0 ? -0.1 : 0.1;
                                    let userZoom = parseFloat(iframe.dataset.userZoom);
                                    userZoom = Math.max(0.2, Math.min(5, userZoom + delta));
                                    iframe.dataset.userZoom = userZoom.toString();
                                    applyZoom();
                                }
                            }, { passive: false });

                        }, 50);

                        resolve();
                    };
                    iframe.onerror = reject;
                    iframe.src = htmlData.url;
                });

                // Now find the target table in the rendered iframe DOM
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

                const tables = Array.from(iframeDoc.querySelectorAll("table"));
                let targetDomTable = null;
                for (const t of tables) {
                    if (t.innerText.toUpperCase().replace(/\s+/g, " ").includes("UNIT AIR OUTLETS")) {
                        targetDomTable = t;
                        break;
                    }
                }

                if (targetDomTable) {
                    targetDomTable.classList.add("tpl-doc-table");
                    // Important: We attach mapping UI directly to the DOM table
                    const headerIndices = previewData.target_table.header_row_indices || [];
                    const detailRowIdx = headerIndices.length > 0 ? headerIndices[headerIndices.length - 1] : -1;
                    
                    if (detailRowIdx >= 0) {
                        const trs = targetDomTable.querySelectorAll("tr");
                        const targetTr = trs[detailRowIdx];
                        if (targetTr) {
                            const colMapping = previewData.target_table.col_mapping || {};
                            
                            // Map logic col index to physical DOM td
                            for (const [logicalColIdxStr, fieldName] of Object.entries(colMapping)) {
                                const logicalColIdx = parseInt(logicalColIdxStr);
                                let currentLogical = 0;
                                let targetTd = null;
                                for (const td of targetTr.children) {
                                    if (currentLogical === logicalColIdx) {
                                        targetTd = td;
                                        break;
                                    }
                                    if (currentLogical > logicalColIdx) break; // Missed it (merged over)
                                    currentLogical += td.colSpan || 1;
                                }

                                if (targetTd) {
                                    targetTd.classList.add("tpl-mappable-header");
                                    targetTd.dataset.docField = fieldName;
                                    
                                    // Make it a drop zone
                                    targetTd.addEventListener("dragover", (e) => {
                                        e.preventDefault();
                                        targetTd.style.borderColor = "var(--neon-cyan)";
                                    });
                                    targetTd.addEventListener("dragleave", () => {
                                        targetTd.style.borderColor = "";
                                    });
                                    targetTd.addEventListener("drop", (e) => {
                                        e.preventDefault();
                                        targetTd.style.borderColor = "";
                                        const droppedField = e.dataTransfer.getData("text/tpl-field");
                                        if (droppedField) {
                                            currentMapping[fieldName] = droppedField;
                                            renderMapperUI(Array.from(targetDomTable.querySelectorAll(".tpl-mappable-header")).map(td => td.dataset.docField));
                                            
                                            // Optional: highlight mapped
                                            let badge = targetTd.querySelector(".tpl-mapped-badge");
                                            if (!badge) {
                                                badge = document.createElement("div");
                                                badge.className = "tpl-mapped-badge";
                                                targetTd.appendChild(badge);
                                            }
                                            badge.innerHTML = `Mapped: ${droppedField} <span class="tpl-badge-remove">✕</span>`;
                                            badge.querySelector(".tpl-badge-remove").addEventListener("click", (evt) => {
                                                evt.stopPropagation();
                                                delete currentMapping[fieldName];
                                                badge.remove();
                                                renderMapperUI(Array.from(targetDomTable.querySelectorAll(".tpl-mappable-header")).map(td => td.dataset.docField));
                                            });
                                        }
                                    });
                                    
                                    // Also apply existing mapping if present
                                    if (currentMapping[fieldName]) {
                                        const badge = document.createElement("div");
                                        badge.className = "tpl-mapped-badge";
                                        badge.innerHTML = `Mapped: ${currentMapping[fieldName]} <span class="tpl-badge-remove">✕</span>`;
                                        badge.querySelector(".tpl-badge-remove").addEventListener("click", (evt) => {
                                            evt.stopPropagation();
                                            delete currentMapping[fieldName];
                                            badge.remove();
                                            renderMapperUI(Array.from(targetDomTable.querySelectorAll(".tpl-mappable-header")).map(td => td.dataset.docField));
                                        });
                                        targetTd.appendChild(badge);
                                    }
                                }
                            }
                        }
                    }
                    
                    // Attach the fill-down highlights if needed (optional for native render)
                    targetDomTable._previewMapping = currentMapping; 
                } else {
                    console.warn("Could not locate interactive table in natively rendered DOCX");
                }
            } catch (err) {
                docPage.innerHTML = `<div style="color:red; padding: 20px;">Error rendering native docx: ${err.message}</div>`;
            }

        } else {
            // Fallback
            const interactiveTable = buildPreviewTable(previewData.target_table, templateName);
            docPage.appendChild(interactiveTable);
            tableWrap.appendChild(docPage);
            body.appendChild(tableWrap);
            tplPreviewOverlay.appendChild(body);
            document.body.appendChild(tplPreviewOverlay);
        }

        if (btnPreviewTemplate) {
            btnPreviewTemplate.classList.add("tpl-preview-active");
            btnPreviewTemplate.disabled = false;
            btnPreviewTemplate.innerHTML = "<span>🔲</span> Preview Template";
        }
    }

    /**
     * Build the interactive HTML table from previewData JSON.
     * Returns the table element.
     */
    function buildPreviewTable(previewData, templateName) {
        // Work with a local copy of the mapping so we can discard on cancel
        // previewMapping is keyed by document column name (same as currentMapping)
        const previewMapping = Object.assign({}, currentMapping);

        const table = document.createElement("table");
        table.className = "tpl-doc-table";
        table.dataset.templateName = templateName;

        const colMapping = previewData.col_mapping || {}; // "colIdx" -> field name
        // Build reverse: field name -> col indices
        const fieldToColIdx = {};
        for (const [colIdx, fieldName] of Object.entries(colMapping)) {
            if (!fieldToColIdx[fieldName]) fieldToColIdx[fieldName] = [];
            fieldToColIdx[fieldName].push(parseInt(colIdx));
        }

        const dataStart = previewData.data_start_row;
        const MAX_DATA_ROWS_SHOWN = 8;

        // Track rendered cells by [row][col] for fill-down highlighting
        // cellRegistry[colIdx] = array of data td elements in that column
        const cellRegistry = {}; // colIdx -> [td elements]

        // Track mappable header cells: docFieldName -> td element
        const mappableHeaderCells = {}; // docFieldName -> td

        let dataRowsRendered = 0;
        let hiddenRows = [];

        previewData.rows.forEach((row, rowIdx) => {
            const tr = document.createElement("tr");

            if (row.is_data) {
                dataRowsRendered++;
                if (dataRowsRendered > MAX_DATA_ROWS_SHOWN) {
                    tr.classList.add("tpl-hidden-row");
                    hiddenRows.push(tr);
                }
            }

            row.cells.forEach(cell => {
                const td = document.createElement("td");
                const colIdx = cell.col_index;

                if (cell.colspan > 1) td.setAttribute("colspan", cell.colspan);
                if (cell.rowspan > 1) td.setAttribute("rowspan", cell.rowspan);

                td.dataset.colIndex = colIdx;

                if (cell.is_header) {
                    td.classList.add("tpl-header-cell");

                    if (cell.mapped_field) {
                        // This is a detected-header cell (mappable)
                        td.classList.add("tpl-mappable-header");
                        td.dataset.docField = cell.mapped_field;
                        mappableHeaderCells[cell.mapped_field] = td;

                        // Header label
                        const label = document.createElement("div");
                        label.textContent = cell.text || cell.mapped_field;
                        label.style.fontWeight = "700";
                        label.style.marginBottom = "2px";
                        td.appendChild(label);

                        // Mapping badge container
                        const badgeWrap = document.createElement("div");
                        badgeWrap.dataset.badgeFor = cell.mapped_field;
                        td.appendChild(badgeWrap);

                        // Render existing mapping if any
                        if (previewMapping[cell.mapped_field]) {
                            renderMappedBadge(badgeWrap, cell.mapped_field, previewMapping[cell.mapped_field], previewMapping, table, colIdx);
                        }

                        // Drag-and-drop handlers on the header cell
                        td.addEventListener("dragover", (e) => {
                            e.preventDefault();
                            e.dataTransfer.dropEffect = "copy";
                            td.classList.add("drag-over");
                        });
                        td.addEventListener("dragleave", () => {
                            td.classList.remove("drag-over");
                        });
                        td.addEventListener("drop", (e) => {
                            e.preventDefault();
                            td.classList.remove("drag-over");
                            const droppedField = e.dataTransfer.getData("text/tpl-field");
                            if (!droppedField || !availableDbFields.includes(droppedField)) return;

                            const docField = td.dataset.docField;
                            previewMapping[docField] = droppedField;

                            // Update badge
                            renderMappedBadge(badgeWrap, docField, droppedField, previewMapping, table, colIdx);

                            // Fill-down highlight
                            applyColumnHighlight(table, colIdx, true);
                        });
                    } else {
                        // Non-mappable header (e.g. above-group row or unlabelled)
                        td.textContent = cell.text;
                    }

                } else if (cell.is_data) {
                    td.classList.add("tpl-data-cell");
                    td.textContent = cell.text || "";

                    // Register for column highlight
                    if (!cellRegistry[colIdx]) cellRegistry[colIdx] = [];
                    cellRegistry[colIdx].push(td);

                } else {
                    // Pre-header row (title rows, etc.)
                    td.textContent = cell.text;
                    td.classList.add("tpl-header-cell");
                }

                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

        // Apply highlight for any existing mapped columns
        for (const [docField, dbField] of Object.entries(previewMapping)) {
            if (dbField) {
                // Find which col indices this docField maps to
                if (fieldToColIdx[docField]) {
                    fieldToColIdx[docField].forEach(ci => applyColumnHighlight(table, ci, true));
                } else {
                    // Try by searching mappableHeaderCells
                    const hCell = mappableHeaderCells[docField];
                    if (hCell) applyColumnHighlight(table, parseInt(hCell.dataset.colIndex), true);
                }
            }
        }

        // Show-more button if rows were hidden
        if (hiddenRows.length > 0) {
            let expanded = false;
            const showMoreBtn = document.createElement("button");
            showMoreBtn.className = "tpl-show-more-rows";
            showMoreBtn.textContent = `▾ Show ${hiddenRows.length} more data rows`;
            showMoreBtn.addEventListener("click", () => {
                expanded = !expanded;
                hiddenRows.forEach(r => r.classList.toggle("tpl-hidden-row", !expanded));
                showMoreBtn.textContent = expanded
                    ? "▴ Hide extra rows"
                    : `▾ Show ${hiddenRows.length} more data rows`;
            });
            // Wrap table in a div so we can append the button below it
            const wrapper = document.createElement("div");
            wrapper.style.display = "inline-flex";
            wrapper.style.flexDirection = "column";
            wrapper.style.minWidth = "fit-content";
            wrapper.appendChild(table);
            wrapper.appendChild(showMoreBtn);

            // Store previewMapping reference on wrapper for Apply
            wrapper._previewMapping = previewMapping;
            return wrapper;
        }

        table._previewMapping = previewMapping;
        return table;
    }

    /** Render or update a mapping badge inside a header cell's badge container */
    function renderMappedBadge(badgeWrap, docField, dbField, previewMapping, table, colIdx) {
        badgeWrap.innerHTML = "";
        const badge = document.createElement("div");
        badge.className = "tpl-mapped-badge";

        const nameSpan = document.createElement("span");
        nameSpan.textContent = dbField;
        badge.appendChild(nameSpan);

        const removeBtn = document.createElement("span");
        removeBtn.className = "tpl-badge-remove";
        removeBtn.title = "Remove mapping";
        removeBtn.textContent = "✕";
        removeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            delete previewMapping[docField];
            badgeWrap.innerHTML = "";
            applyColumnHighlight(table, colIdx, false);
            if (window.recalcTemplateScale) window.recalcTemplateScale();
        });
        badge.appendChild(removeBtn);

        badgeWrap.appendChild(badge);
        if (window.recalcTemplateScale) window.recalcTemplateScale();
    }

    /** Highlight or de-highlight all data cells in a given column index */
    function applyColumnHighlight(table, colIdx, highlight) {
        const dataCells = table.querySelectorAll(`td.tpl-data-cell[data-col-index="${colIdx}"]`);
        dataCells.forEach(td => {
            td.classList.toggle("tpl-col-highlight", highlight);
        });
    }

    /** Close the preview overlay; if apply=true, sync previewMapping -> currentMapping and re-render list */
    function closeTplPreview(apply) {
        if (!tplPreviewOverlay) return;

        if (apply) {
            // Extract previewMapping from the table or wrapper element
            const inner = tplPreviewOverlay.querySelector(".tpl-doc-table") ||
                          tplPreviewOverlay.querySelector("[data-template-name]");
            let wrapper = tplPreviewOverlay.querySelector(".tpl-preview-table-wrap > *");
            const pm = wrapper?._previewMapping;
            if (pm) {
                // Merge into currentMapping (preview only has mapped entries; don't overwrite unmapped)
                for (const [k, v] of Object.entries(pm)) {
                    currentMapping[k] = v;
                }
                // For keys in currentMapping not in pm, clear them if user removed them
                // (previewMapping has complete state)
                for (const k of Object.keys(currentMapping)) {
                    if (!(k in pm)) delete currentMapping[k];
                }
                // Re-render the column list view so dropdowns are in sync
                const templateColumns = Array.from(
                    tplPreviewOverlay.querySelectorAll(".tpl-mappable-header")
                ).map(td => td.dataset.docField).filter(Boolean);

                // Deduplicate
                const seen = new Set();
                const uniqueCols = [];
                for (const c of templateColumns) {
                    if (!seen.has(c)) { seen.add(c); uniqueCols.push(c); }
                }
                if (uniqueCols.length > 0) {
                    renderMapperUI(uniqueCols);
                }
            }
        }

        tplPreviewOverlay.remove();
        tplPreviewOverlay = null;

        if (window.location.hash === '#Template%20Preview') {
            window.history.pushState('', document.title, window.location.pathname + window.location.search);
        }

        if (btnPreviewTemplate) {
            btnPreviewTemplate.classList.remove("tpl-preview-active");
            btnPreviewTemplate.innerHTML = "<span>🔲</span> Preview Template";
        }
    }

    if (btnPreviewTemplate) {
        btnPreviewTemplate.addEventListener("click", () => {
            if (tplPreviewOverlay) {
                closeTplPreview(false);
            } else {
                openTemplatePreview();
            }
        });
    }

    // --- Data Viewer Logic ---

    const btnViewData = document.getElementById("btn-view-project-data");
    const dataViewerContainer = document.getElementById("data-viewer-container");
    const btnCloseDataViewer = document.getElementById("btn-close-data-viewer");
    const btnResetColumns = document.getElementById("btn-reset-data-columns");

    if (btnViewData && dataViewerContainer && btnCloseDataViewer) {
        btnViewData.addEventListener("click", async () => {
            const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
            if (!project || project === "—") {
                alert("Please select a project first.");
                return;
            }

            window.location.hash = 'Project%20Data';

            // Show data viewer, hide PDF viewer and mapper
            document.getElementById("schema-mapper-container").style.display = "none";
            dataViewerContainer.style.display = "flex";
            
            switchToolbarPanel('toolbar-data-viewer');

            await loadProjectData(project);
        });

        btnCloseDataViewer.addEventListener("click", () => {
            dataViewerContainer.style.display = "none";
            
            if (window.location.hash === '#Project%20Data' || window.location.hash === '#Project Data') {
                window.history.pushState('', document.title, window.location.pathname + window.location.search);
            }
            
            switchToolbarPanel('toolbar-pdf-tools');
        });

        if (btnResetColumns) {
            btnResetColumns.addEventListener("click", () => {
                if (confirm("Reset all column orders and widths to default?")) {
                    localStorage.removeItem("dataViewerColOrder_table-air-outlets");
                    localStorage.removeItem("dataViewerColWidths_table-air-outlets");
                    localStorage.removeItem("dataViewerColOrder_table-systems");
                    localStorage.removeItem("dataViewerColWidths_table-systems");
                    
                    const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
                    if (project && project !== "—") {
                        loadProjectData(project);
                    }
                }
            });
        }

        // --- Sync from PDF button ---
        const btnSyncFromPdf = document.getElementById("btn-sync-from-pdf");
        if (btnSyncFromPdf) {
            btnSyncFromPdf.addEventListener("click", async () => {
                const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
                if (!project || project === "—") {
                    alert("Please select a project first.");
                    return;
                }

                const originalHtml = btnSyncFromPdf.innerHTML;
                const originalStyle = btnSyncFromPdf.style.cssText;
                btnSyncFromPdf.disabled = true;
                btnSyncFromPdf.innerHTML = "⏳ Syncing...";

                try {
                    const res = await fetch(`/api/projects/${encodeURIComponent(project)}/sync-from-pdf`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" }
                    });

                    const data = await res.json();

                    if (!res.ok) {
                        alert("Sync failed: " + (data.error || "Unknown error"));
                        return;
                    }

                    const { added, updated, not_found_marked, duplicates_removed, total_pdf_stamps, total_db_stamps } = data;
                    let msg = `✅ Sync complete!\n\n`;
                    msg += `📄 PDF stamps found: ${total_pdf_stamps}\n`;
                    msg += `🗃️ DB stamps before sync: ${total_db_stamps}\n\n`;
                    msg += `➕ New stamps added to DB: ${added}\n`;
                    msg += `🔄 Stamps updated (pattern/type changed): ${updated}\n`;
                    if (duplicates_removed > 0) {
                        msg += `🧹 Duplicate DB rows removed: ${duplicates_removed}\n`;
                    }
                    if (not_found_marked > 0) {
                        msg += `⚠️ Stamps in DB not found in any PDF (marked NOT FOUND): ${not_found_marked}`;
                    }
                    alert(msg);

                    // Reload the data viewer table to show updated values
                    await loadProjectData(project);
                } catch (err) {
                    alert("Sync error: " + err.message);
                } finally {
                    btnSyncFromPdf.disabled = false;
                    btnSyncFromPdf.innerHTML = originalHtml;
                    btnSyncFromPdf.style.cssText = originalStyle;
                }
            });
        }
        
        // --- Settings Modal Logic ---

        const btnSettings = document.getElementById("btn-data-viewer-settings");
        const settingsModal = document.getElementById("data-viewer-settings-modal");
        const closeSettingsBtn = document.getElementById("close-dv-settings-btn");
        const cancelSettingsBtn = document.getElementById("btn-dv-settings-cancel");
        const saveSettingsBtn = document.getElementById("btn-dv-settings-save");
        
        currentSettings = {
            system_fields: [], air_outlet_fields: [],
            system_column_order: [], air_outlet_column_order: []
        };
        
        function renderSettingsList(containerId, fields, order) {
            const container = document.getElementById(containerId);
            container.innerHTML = "";
            
            // First, order the fields according to `order` array, then append the rest
            const orderedFields = [];
            const remainingFields = [...fields];
            if (order && order.length > 0) {
                order.forEach(colName => {
                    const idx = remainingFields.findIndex(f => f.name === colName);
                    if (idx !== -1) {
                        orderedFields.push(remainingFields.splice(idx, 1)[0]);
                    }
                });
            }
            orderedFields.push(...remainingFields);
            
            const fixedFieldNames = ["UUID", "PDF File", "Page", "Pattern", "#"];
            
            orderedFields.forEach((f, index) => {
                const item = document.createElement("div");
                item.style.cssText = "display: flex; gap: 8px; align-items: center; padding: 6px; background: var(--btn-bg); border: 1px solid var(--border-color); border-radius: 4px; cursor: grab;";
                item.draggable = true;
                
                // Drag handle icon
                const dragHandle = document.createElement("span");
                dragHandle.textContent = "☰";
                dragHandle.style.cssText = "color: var(--text-secondary); margin-right: 4px; font-size: 14px; user-select: none;";
                item.appendChild(dragHandle);
                
                // Name input
                const nameInput = document.createElement("input");
                nameInput.type = "text";
                nameInput.value = f.name;
                nameInput.style.cssText = "flex: 1; min-width: 0; padding: 4px 8px; background: var(--modal-input-bg); border: 1px solid var(--modal-input-border); color: var(--text-primary); border-radius: 4px; font-size: 13px;";
                nameInput.onchange = (e) => { f.name = e.target.value.trim(); };
                
                const isFixed = fixedFieldNames.includes(f.name);
                if (isFixed) {
                    nameInput.disabled = true;
                }
                item.appendChild(nameInput);
                
                // Delete button
                const btnDel = document.createElement("button");
                btnDel.innerHTML = "✕";
                btnDel.className = "btn small-btn";
                btnDel.style.color = "#ef4444";
                if (isFixed) {
                    btnDel.disabled = true;
                    btnDel.style.opacity = "0.3";
                }
                btnDel.onclick = () => {
                    const idx = fields.indexOf(f);
                    if (idx !== -1) fields.splice(idx, 1);
                    renderSettingsList(containerId, fields, fields.map(x => x.name));
                };
                item.appendChild(btnDel);
                
                // Drag & Drop Listeners
                item.addEventListener("dragstart", (e) => {
                    e.dataTransfer.setData("text/plain", index);
                    item.style.opacity = "0.5";
                });
                
                item.addEventListener("dragend", () => {
                    item.style.opacity = "1";
                });
                
                item.addEventListener("dragover", (e) => {
                    e.preventDefault();
                });
                
                item.addEventListener("drop", (e) => {
                    e.preventDefault();
                    const dragIndex = parseInt(e.dataTransfer.getData("text/plain"), 10);
                    if (dragIndex !== index) {
                        const draggedField = orderedFields[dragIndex];
                        orderedFields.splice(dragIndex, 1);
                        orderedFields.splice(index, 0, draggedField);
                        
                        fields.length = 0;
                        fields.push(...orderedFields);
                        renderSettingsList(containerId, fields, fields.map(x => x.name));
                    }
                });
                
                container.appendChild(item);
            });
        }
        
        if (btnSettings && settingsModal) {
            const closeFn = () => settingsModal.style.display = "none";
            closeSettingsBtn.onclick = closeFn;
            cancelSettingsBtn.onclick = closeFn;
            
            // Helper to merge dynamic and fixed fields for editing UI
            const prepareFieldsForEditor = (dynamicFields) => {
                const fixedFields = [
                    { name: "UUID", value: "", type: "string" },
                    { name: "PDF File", value: "", type: "string" },
                    { name: "Page", value: "", type: "string" },
                    { name: "Pattern", value: "", type: "string" },
                    { name: "#", value: "", type: "string" }
                ];
                const filteredDynamic = (dynamicFields || []).filter(df => 
                    !fixedFields.some(ff => ff.name.toLowerCase() === df.name.toLowerCase())
                );
                return [...fixedFields, ...filteredDynamic];
            };
            
            btnSettings.addEventListener("click", async () => {
                settingsModal.style.display = "flex";
                
                try {
                    const res = await fetch("/api/config/data_viewer");
                    const data = await res.json();
                    
                    const rawSystemFields = data.system_fields || [{name: "#", value: "", type: "string"}, {name: "SYSTEM TYPE", value: "", type: "string"}, {name: "DESIGN CFM", value: "", type: "string"}];
                    const rawAirOutletFields = data.air_outlet_fields || [{name: "#", value: "", type: "string"}, {name: "TYPE", value: "", type: "string"}, {name: "SIZE", value: "", type: "string"}, {name: "DESIGN CFM", value: "", type: "string"}];
                    
                    currentSettings.system_fields = prepareFieldsForEditor(rawSystemFields);
                    currentSettings.air_outlet_fields = prepareFieldsForEditor(rawAirOutletFields);
                    
                    currentSettings.system_column_order = data.system_column_order || ["UUID", "PDF File", "Page", "Pattern", "#", "SYSTEM TYPE", "DESIGN CFM"];
                    currentSettings.air_outlet_column_order = data.air_outlet_column_order || ["UUID", "PDF File", "Page", "Pattern", "#", "TYPE", "SIZE", "DESIGN CFM"];
                    
                    renderSettingsList("dv-settings-systems-list", currentSettings.system_fields, currentSettings.system_column_order);
                    renderSettingsList("dv-settings-air-outlets-list", currentSettings.air_outlet_fields, currentSettings.air_outlet_column_order);
                    
                } catch (err) {
                    console.error("Failed to load settings", err);
                }
            });
            
            const showAddColumnModal = (callback) => {
                const addColModal = document.getElementById("add-column-modal");
                const input = document.getElementById("new-col-name-input");
                const error = document.getElementById("add-col-error");
                const btnConfirm = document.getElementById("btn-add-col-confirm");
                const btnCancel = document.getElementById("btn-add-col-cancel");
                const btnClose = document.getElementById("close-add-col-btn");
                
                input.value = "";
                error.style.display = "none";
                addColModal.style.display = "flex";
                input.focus();
                
                const close = () => {
                    addColModal.style.display = "none";
                };
                
                const confirm = () => {
                    const name = input.value.trim().toUpperCase();
                    if (!name) {
                        error.textContent = "Please enter a column name.";
                        error.style.display = "block";
                        return;
                    }
                    callback(name);
                    close();
                };
                
                btnConfirm.onclick = confirm;
                btnCancel.onclick = close;
                btnClose.onclick = close;
                
                input.onkeydown = (e) => {
                    if (e.key === "Enter") {
                        confirm();
                    } else if (e.key === "Escape") {
                        close();
                    }
                };
            };
            
            document.getElementById("btn-dv-settings-add-system").onclick = () => {
                showAddColumnModal((name) => {
                    if (currentSettings.system_fields.some(f => f.name.toLowerCase() === name.toLowerCase())) {
                        alert("Column already exists.");
                        return;
                    }
                    currentSettings.system_fields.push({name: name, value: "", type: "string"});
                    renderSettingsList("dv-settings-systems-list", currentSettings.system_fields, currentSettings.system_fields.map(f => f.name));
                });
            };
            
            document.getElementById("btn-dv-settings-add-air-outlet").onclick = () => {
                showAddColumnModal((name) => {
                    if (currentSettings.air_outlet_fields.some(f => f.name.toLowerCase() === name.toLowerCase())) {
                        alert("Column already exists.");
                        return;
                    }
                    currentSettings.air_outlet_fields.push({name: name, value: "", type: "string"});
                    renderSettingsList("dv-settings-air-outlets-list", currentSettings.air_outlet_fields, currentSettings.air_outlet_fields.map(f => f.name));
                });
            };
            
            saveSettingsBtn.onclick = async () => {
                // Update orders to exactly match the current UI array layout
                currentSettings.system_column_order = currentSettings.system_fields.map(f => f.name);
                currentSettings.air_outlet_column_order = currentSettings.air_outlet_fields.map(f => f.name);
                
                // When saving fields back, dynamic/database value fields are saved (including "#"),
                // but stamp properties like UUID, PDF File, Page, Pattern are excluded as they are not dynamic DB fields.
                const systemDynamicOnly = currentSettings.system_fields.filter(f => 
                    !["UUID", "PDF File", "Page", "Pattern"].includes(f.name)
                );
                const airOutletDynamicOnly = currentSettings.air_outlet_fields.filter(f => 
                    !["UUID", "PDF File", "Page", "Pattern"].includes(f.name)
                );
                
                const payload = {
                    system_fields: systemDynamicOnly,
                    air_outlet_fields: airOutletDynamicOnly,
                    system_column_order: currentSettings.system_column_order,
                    air_outlet_column_order: currentSettings.air_outlet_column_order
                };
                
                try {
                    saveSettingsBtn.textContent = "Saving...";
                    await fetch("/api/config/data_viewer", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });
                    
                    // Clear local storage for orders so new config takes effect
                    localStorage.removeItem("dataViewerColOrder_table-air-outlets");
                    localStorage.removeItem("dataViewerColOrder_table-systems");
                    
                    closeFn();
                    
                    // Reload data
                    const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
                    if (project && project !== "—") {
                        loadProjectData(project);
                    }
                } catch (err) {
                    console.error("Failed to save settings", err);
                    alert("Failed to save settings.");
                } finally {
                    saveSettingsBtn.textContent = "Save Settings";
                }
            };
        }

        const btnCsvAirOutlets = document.getElementById("btn-csv-air-outlets");
        if (btnCsvAirOutlets) {
            btnCsvAirOutlets.addEventListener("click", () => {
                downloadTableToCSV("air-outlets-tables-container", "air_outlets.csv");
            });
        }
        
        const btnCsvSystems = document.getElementById("btn-csv-systems");
        if (btnCsvSystems) {
            btnCsvSystems.addEventListener("click", () => {
                downloadTableToCSV("table-systems", "systems.csv");
            });
        }
    }

    function downloadTableToCSV(elementId, filename) {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        let tables = el.tagName === "TABLE" ? [el] : Array.from(el.querySelectorAll("table.data-table"));
        if (tables.length === 0) return;
        
        let csvContent = "";
        
        // Headers from first table
        const ths = tables[0].querySelectorAll("thead th");
        const headers = [];
        ths.forEach(th => {
            if (th.textContent !== "Actions") {
                headers.push(th.dataset.colName || th.textContent.trim());
            }
        });
        csvContent += headers.map(h => `"${h.replace(/"/g, '""')}"`).join(",") + "\r\n";
        
        // Rows
        tables.forEach(table => {
            const trs = table.querySelectorAll("tbody tr");
            trs.forEach(tr => {
                const tds = tr.querySelectorAll("td");
                if (tds.length === 1 && tds[0].colSpan > 1) return; // e.g. Loading... or Error
                if (tds.length === 0) return;
                
                const rowData = [];
                // Last column is Actions, we exclude it
                for (let i = 0; i < tds.length - 1; i++) {
                    rowData.push(`"${tds[i].textContent.replace(/"/g, '""')}"`);
                }
                csvContent += rowData.join(",") + "\r\n";
            });
        });
        
        const blob = new Blob(["\ufeff" + csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    let allProjectAirOutlets = [];
    let allProjectSystems = [];

    // Use event delegation for input events to guarantee timing safety
    document.addEventListener("input", (e) => {
        if (e.target && e.target.id === "search-project-data") {
            filterAndRenderProjectData();
        }
    });

    document.addEventListener("focusin", (e) => {
        if (e.target && e.target.id === "search-project-data") {
            document.body.classList.add("search-active");
        }
    });
    
    document.addEventListener("focusout", (e) => {
        if (e.target && e.target.id === "search-project-data") {
            document.body.classList.remove("search-active");
        }
    });

    const highlightStyle = document.createElement("style");
    highlightStyle.textContent = `
        body.search-active .search-highlight {
            background-color: rgba(250, 204, 21, 0.4);
            color: #fff;
            border-radius: 2px;
            font-weight: bold;
        }
    `;
    document.head.appendChild(highlightStyle);

    function filterAndRenderProjectData() {
        const sInput = document.getElementById("search-project-data");
        const query = sInput ? sInput.value.toLowerCase().trim() : "";
        const tableSystems = document.getElementById("table-systems");

        let filteredAirOutlets = allProjectAirOutlets;
        let filteredSystems = allProjectSystems;

        if (query) {
            const matchesQuery = (item) => {
                if (String(item.id).toLowerCase().includes(query)) return true;
                if (item.stamp_uuid && String(item.stamp_uuid).toLowerCase().includes(query)) return true;
                if (item.pattern_name && item.pattern_name.toLowerCase().includes(query)) return true;
                if (String(item.page).toLowerCase().includes(query)) return true;
                if (String(item.xref).toLowerCase().includes(query)) return true;
                if (item.pdf_path && item.pdf_path.toLowerCase().includes(query)) return true;
                
                if (item.fields) {
                    for (const [key, value] of Object.entries(item.fields)) {
                        if (key.toLowerCase().includes(query) || String(value).toLowerCase().includes(query)) {
                            return true;
                        }
                    }
                }
                return false;
            };

            filteredAirOutlets = allProjectAirOutlets.filter(matchesQuery);
            filteredSystems = allProjectSystems.filter(matchesQuery);
        }

        const airOutletsContainer = document.getElementById("air-outlets-tables-container");
        if (airOutletsContainer) {
            airOutletsContainer.innerHTML = "";
            
            if (filteredAirOutlets.length === 0) {
                airOutletsContainer.innerHTML = "<div style='padding: 20px; text-align: center; color: var(--text-secondary);'>No air outlets found.</div>";
            } else {
                const grouped = {};
                filteredAirOutlets.forEach(item => {
                    const patName = (item.fields && (item.fields["System Pattern"] || item.fields["System"])) ? 
                                    (item.fields["System Pattern"] || item.fields["System"]) : 
                                    "Unknown System";
                    if (!grouped[patName]) grouped[patName] = [];
                    grouped[patName].push(item);
                });
                
                const patternNames = Object.keys(grouped).sort();
                
                patternNames.forEach((patName, idx) => {
                    const header = document.createElement("h4");
                    header.textContent = patName === "Unknown System" ? "Unknown System" : `System: ${patName}`;
                    header.style.cssText = "margin: 0; padding: 10px 0; height: 40px; box-sizing: border-box; display: flex; align-items: center; color: var(--text-secondary); font-weight: bold; font-size: 1.1rem; position: sticky; top: 40px; background: var(--bg-dark); z-index: 10;";
                    airOutletsContainer.appendChild(header);
                    
                    const scrollContainer = document.createElement("div");
                    scrollContainer.className = "table-scroll-container";
                    
                    const table = document.createElement("table");
                    table.id = `table-air-outlets-${idx}`;
                    table.dataset.tableType = "air-outlets";
                    table.className = "data-table";
                    table.innerHTML = "<thead></thead><tbody></tbody>";
                    
                    scrollContainer.appendChild(table);
                    airOutletsContainer.appendChild(scrollContainer);
                    
                    renderDataTable(table, grouped[patName], query);
                });
            }
        }

        if (tableSystems) {
            renderDataTable(tableSystems, filteredSystems, query);
        }
    }

    async function loadProjectData(project) {
        const airOutletsContainer = document.getElementById("air-outlets-tables-container");
        const tableSystems = document.getElementById("table-systems");
        
        if (airOutletsContainer) {
            airOutletsContainer.innerHTML = "<div style='padding: 20px; text-align: center; color: var(--text-secondary);'>Loading...</div>";
        }
        if (tableSystems) {
            tableSystems.querySelector("thead").innerHTML = "";
            tableSystems.querySelector("tbody").innerHTML = "<tr><td>Loading...</td></tr>";
        }

        const sInput = document.getElementById("search-project-data");
        if (sInput) sInput.value = "";

        try {
            const [res, configRes] = await Promise.all([
                fetch(`/api/projects/${encodeURIComponent(project)}/data`),
                fetch(`/api/config/data_viewer`)
            ]);
            
            if (!res.ok) throw new Error("Failed to fetch project data");
            const data = await res.json();
            
            if (configRes.ok) {
                const cfg = await configRes.json();
                currentSettings.system_fields = cfg.system_fields || [];
                currentSettings.air_outlet_fields = cfg.air_outlet_fields || [];
                currentSettings.system_column_order = cfg.system_column_order || [];
                currentSettings.air_outlet_column_order = cfg.air_outlet_column_order || [];
            }

            allProjectAirOutlets = data.air_outlets || [];
            allProjectSystems = data.systems || [];

            filterAndRenderProjectData();
        } catch (e) {
            alert("Error loading data: " + e.message);
            const airOutletsContainer = document.getElementById("air-outlets-tables-container");
            const tableSystems = document.getElementById("table-systems");
            if (airOutletsContainer) airOutletsContainer.innerHTML = `<div style="color:red; padding: 20px;">Error: ${e.message}</div>`;
            if (tableSystems) tableSystems.querySelector("tbody").innerHTML = `<tr><td style="color:red">Error: ${e.message}</td></tr>`;
        }
    }


    // --- MULTI SELECTION GLOBALS ---
    const selectedRows = new Set();
    let lastSelectedRowIndex = -1;
    let currentSortColumn = null;
    let currentSortDir = 1; // 1 for asc, -1 for desc
    
    function setupMarqueeSelection(container) {
        let isSelecting = false;
        let startX = 0;
        let startY = 0;
        let marquee = null;
        
        container.addEventListener("mousedown", (e) => {
            if (e.button !== 0) return;
            if (e.target.closest("button, input, a, .col-resizer, th, select, span.close, span.close-btn") || (e.target.tagName === 'SPAN' && e.target.textContent === '⋮')) return;
            
            if (!e.ctrlKey && !e.metaKey && !e.shiftKey) {
                selectedRows.clear();
                document.querySelectorAll(".data-table tr.selected").forEach(r => r.classList.remove("selected"));
            }
            
            isSelecting = true;
            const rect = container.getBoundingClientRect();
            startX = e.clientX - rect.left + container.scrollLeft;
            startY = e.clientY - rect.top + container.scrollTop;
            
            marquee = document.createElement("div");
            marquee.style.cssText = "position: absolute; border: 1px dashed var(--neon-cyan); background: rgba(0, 255, 255, 0.15); pointer-events: none; z-index: 1000;";
            marquee.style.left = `${startX}px`;
            marquee.style.top = `${startY}px`;
            marquee.style.width = "0px";
            marquee.style.height = "0px";
            
            container.style.position = "relative";
            container.appendChild(marquee);
            
            e.preventDefault();
        });
        
        window.addEventListener("mousemove", (e) => {
            if (!isSelecting || !marquee) return;
            
            const rect = container.getBoundingClientRect();
            const currentX = e.clientX - rect.left + container.scrollLeft;
            const currentY = e.clientY - rect.top + container.scrollTop;
            
            const x = Math.min(startX, currentX);
            const y = Math.min(startY, currentY);
            const w = Math.abs(startX - currentX);
            const h = Math.abs(startY - currentY);
            
            marquee.style.left = `${x}px`;
            marquee.style.top = `${y}px`;
            marquee.style.width = `${w}px`;
            marquee.style.height = `${h}px`;
            
            const marqueeRect = {
                left: x,
                right: x + w,
                top: y,
                bottom: y + h
            };
            
            const rows = container.querySelectorAll("tbody tr");
            rows.forEach(row => {
                const rowTop = row.offsetTop;
                const rowBottom = rowTop + row.offsetHeight;
                const rowLeft = row.offsetLeft;
                const rowRight = rowLeft + row.offsetWidth;
                
                const intersects = !(marqueeRect.left > rowRight ||
                                     marqueeRect.right < rowLeft ||
                                     marqueeRect.top > rowBottom ||
                                     marqueeRect.bottom < rowTop);
                                     
                const rid = row.getAttribute("data-id");
                if (intersects) {
                    row.classList.add("selected");
                    selectedRows.add(rid);
                } else {
                    if (!e.ctrlKey && !e.metaKey && !e.shiftKey) {
                        row.classList.remove("selected");
                        selectedRows.delete(rid);
                    }
                }
            });
        });
        
        window.addEventListener("mouseup", () => {
            if (!isSelecting) return;
            isSelecting = false;
            if (marquee) {
                marquee.remove();
                marquee = null;
            }
        });
    }
    
    // Initialize marquee selection on all table-scroll-containers
    document.querySelectorAll(".table-scroll-container").forEach(setupMarqueeSelection);
    
    // --- COLUMN RESIZING GLOBALS ---
    let isResizing = false;
    let currentResizer = null;
    let currentTh = null;
    let startX = 0;
    let startWidth = 0;

    // Global Event Handlers
    document.addEventListener('mousemove', (e) => {
        if (!isResizing || !currentTh) return;
        const newWidth = startWidth + (e.clientX - startX);
        if (newWidth > 30) {
            currentTh.style.width = `${newWidth}px`;
            currentTh.style.minWidth = `${newWidth}px`;
            currentTh.style.maxWidth = `${newWidth}px`;
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            if (currentResizer) currentResizer.classList.remove('col-resizing');
            isResizing = false;
            
            // Save width
            if (currentTh && currentTh.dataset.colName) {
                const tableElem = currentTh.closest('table');
                if (tableElem) {
                    const widthKeyBase = tableElem.dataset.tableType === "air-outlets" ? "table-air-outlets" : tableElem.id;
                    const widthsKey = `dataViewerColWidths_${widthKeyBase}`;
                    let widths = {};
                    try { widths = JSON.parse(localStorage.getItem(widthsKey) || '{}'); } catch(err){}
                    widths[currentTh.dataset.colName] = currentTh.style.width;
                    localStorage.setItem(widthsKey, JSON.stringify(widths));
                }
            }
            
            currentTh = null;
            currentResizer = null;
        }
    });

    async function performDeleteRows(rowsToDelete) {
        rowsToDelete.forEach(tr => {
            tr.style.opacity = "0.5";
            tr.style.pointerEvents = "none";
        });
        
        // Group stamps by pdf_path
        const byPdf = {};
        for (const tr of rowsToDelete) {
            const metaStr = tr.getAttribute("data-meta");
            if (!metaStr) continue;
            const item = JSON.parse(metaStr);
            if (!byPdf[item.pdf_path]) {
                byPdf[item.pdf_path] = [];
            }
            byPdf[item.pdf_path].push({ item, tr });
        }
        
        for (const [pdf_path, stamps] of Object.entries(byPdf)) {
            const xrefs = stamps.map(s => s.item.xref);
            try {
                const res = await fetch(`/api/pdf/${encodeURIComponent(pdf_path)}/stamps/bulk-delete`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ xrefs })
                });
                
                if (res.ok) {
                    stamps.forEach(({ item, tr }) => {
                        tr.remove();
                        selectedRows.delete(String(item.id));
                        allProjectAirOutlets = allProjectAirOutlets.filter(x => x.id !== item.id);
                        allProjectSystems = allProjectSystems.filter(x => x.id !== item.id);
                        window.dispatchEvent(new CustomEvent('stamp-deleted', { detail: { xref: item.xref } }));
                    });
                } else {
                    const data = await res.json();
                    alert(`Failed to delete stamps from ${pdf_path}: ${data.error}`);
                    stamps.forEach(({ tr }) => {
                        tr.style.opacity = "1";
                        tr.style.pointerEvents = "auto";
                    });
                }
            } catch (err) {
                alert(`Error deleting stamps from ${pdf_path}: ${err.message}`);
                stamps.forEach(({ tr }) => {
                    tr.style.opacity = "1";
                    tr.style.pointerEvents = "auto";
                });
            }
        }
        
        document.getElementById("selection-count").textContent = 
            selectedRows.size > 0 ? `${selectedRows.size} selected` : "";
    }

    document.addEventListener("keydown", async (e) => {
        const dvContainer = document.getElementById("data-viewer-container");
        if (!dvContainer || dvContainer.style.display === "none") return;
        
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        if (e.key === "Escape") {
            selectedRows.clear();
            document.querySelectorAll(".data-table tr.selected").forEach(r => r.classList.remove("selected"));
        } else if ((e.ctrlKey || e.metaKey) && (e.key === "a" || e.key === "A")) {
            e.preventDefault();
            document.querySelectorAll(".data-table tbody tr").forEach(row => {
                const rid = row.getAttribute("data-id");
                if (rid) {
                    selectedRows.add(rid);
                    row.classList.add("selected");
                }
            });
        } else if (e.key === "Delete" || e.key === "Backspace") {
            e.preventDefault();
            if (selectedRows.size === 0) return;
            
            if (!confirm(`Are you sure you want to delete ${selectedRows.size} selected stamp(s)?`)) return;
            
            const rowsToDelete = Array.from(document.querySelectorAll(".data-table tbody tr.selected"));
            performDeleteRows(rowsToDelete);
        }
    });

    window.dropColumn = function(tableId, dragCol, dropCol, allFieldsArr) {
        if (dragCol === dropCol) return;
        const orderKey = `dataViewerColOrder_${tableId}`;
        let order = [];
        try { order = JSON.parse(localStorage.getItem(orderKey) || '[]'); } catch(e){}
        
        allFieldsArr.forEach(c => { if (!order.includes(c)) order.push(c); });
        
        const dragIdx = order.indexOf(dragCol);
        const dropIdx = order.indexOf(dropCol);
        
        if (dragIdx > -1 && dropIdx > -1) {
            order.splice(dragIdx, 1);
            const newDropIdx = order.indexOf(dropCol);
            order.splice(newDropIdx, 0, dragCol);
            localStorage.setItem(orderKey, JSON.stringify(order));
            
            const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
            loadProjectData(project);
        }
    };
    
    window.sortColumn = function(tableId, colName) {
        if (currentSortColumn === colName) {
            currentSortDir = currentSortDir === 1 ? -1 : 1;
        } else {
            currentSortColumn = colName;
            currentSortDir = 1;
        }
        const project = window.currentProject || document.getElementById("current-project-label")?.textContent || "";
        loadProjectData(project);
    };

    function renderDataTable(tableElement, items, query = "") {
        const thead = tableElement.querySelector("thead");
        const tbody = tableElement.querySelector("tbody");
        
        thead.innerHTML = "";
        tbody.innerHTML = "";

        if (!items || items.length === 0) {
            tbody.innerHTML = "<tr><td style='text-align: center; color: var(--text-secondary);'>No data found.</td></tr>";
            return;
        }

        const dynamicFieldsSet = new Set();
        items.forEach(item => {
            if (item.fields) Object.keys(item.fields).forEach(k => dynamicFieldsSet.add(k));
        });
        
        let fixedCols = [];
        if (tableElement.id === "table-systems") {
            fixedCols = ["UUID", "PDF File", "Page", "System"];
        } else {
            fixedCols = ["UUID", "PDF File", "Page", "Pattern", "System"];
        }
        
        const dynamicCols = Array.from(dynamicFieldsSet)
                                 .filter(c => !fixedCols.includes(c))
                                 .sort();
        const allFieldsArr = fixedCols.concat(dynamicCols);

        const orderKeyBase = tableElement.dataset.tableType === "air-outlets" ? "table-air-outlets" : tableElement.id;
        const orderKey = `dataViewerColOrder_${orderKeyBase}`;
        
        // 1. Get baseline order from settings
        let configOrder = [];
        if (tableElement.id === "table-systems") {
            configOrder = currentSettings.system_column_order || [];
        } else if (tableElement.dataset.tableType === "air-outlets") {
            configOrder = currentSettings.air_outlet_column_order || [];
        }
        
        // Fallback default order if no config order exists
        if (configOrder.length === 0) {
            if (tableElement.id === "table-systems") {
                configOrder = ["UUID", "PDF File", "Page", "System", "#", "SYSTEM TYPE", "DESIGN CFM"];
            } else {
                configOrder = ["UUID", "PDF File", "Page", "Pattern", "System", "#", "TYPE", "SIZE", "DESIGN CFM"];
            }
        }
        
        // 2. Check local storage
        let savedOrder = [];
        try { savedOrder = JSON.parse(localStorage.getItem(orderKey) || '[]'); } catch(e){}
        
        // 3. Prefer local storage, fallback to config
        let baseOrder = savedOrder.length > 0 ? savedOrder : configOrder;
        
        let sortedFields = [];
        baseOrder.forEach(col => { if (allFieldsArr.includes(col)) sortedFields.push(col); });
        const remaining = allFieldsArr.filter(c => !sortedFields.includes(c));
        sortedFields = sortedFields.concat(remaining);
        
        if (savedOrder.length > 0) {
            localStorage.setItem(orderKey, JSON.stringify(sortedFields));
        }

        // Sorting logic
        if (currentSortColumn) {
            items.sort((a, b) => {
                let valA = "";
                let valB = "";
                if (fixedCols.includes(currentSortColumn)) {
                    if (currentSortColumn === "UUID") { valA = a.stamp_uuid || a.id; valB = b.stamp_uuid || b.id; }
                    else if (currentSortColumn === "Pattern") { valA = a.pattern_name || ""; valB = b.pattern_name || ""; }
                    else if (currentSortColumn === "System") {
                        if (tableElement.dataset.tableType === "air-outlets") {
                            valA = (a.fields && (a.fields["System Pattern"] || a.fields["System"])) || "";
                            valB = (b.fields && (b.fields["System Pattern"] || b.fields["System"])) || "";
                        } else {
                            valA = a.pattern_name || ""; valB = b.pattern_name || "";
                        }
                    }
                    else if (currentSortColumn === "PDF File") { valA = a.pdf_path || ""; valB = b.pdf_path || ""; }
                    else if (currentSortColumn === "Page") { valA = a.page; valB = b.page; }
                } else {
                    valA = a.fields && a.fields[currentSortColumn] ? a.fields[currentSortColumn] : "";
                    valB = b.fields && b.fields[currentSortColumn] ? b.fields[currentSortColumn] : "";
                }
                
                const numA = Number(valA);
                const numB = Number(valB);
                if (!isNaN(numA) && !isNaN(numB) && valA !== "" && valB !== "") {
                    return (numA - numB) * currentSortDir;
                }
                
                return String(valA).localeCompare(String(valB)) * currentSortDir;
            });
        }

        const trHead = document.createElement("tr");
        const widthKeyBase = tableElement.dataset.tableType === "air-outlets" ? "table-air-outlets" : tableElement.id;
        const widthsKey = `dataViewerColWidths_${widthKeyBase}`;
        let savedWidths = {};
        try { savedWidths = JSON.parse(localStorage.getItem(widthsKey) || '{}'); } catch(err){}
        
        const createSortableHeader = (colName) => {
            const th = document.createElement("th");
            th.dataset.colName = colName;
            
            // Apply saved width
            if (savedWidths[colName]) {
                th.style.width = savedWidths[colName];
                th.style.minWidth = savedWidths[colName];
                th.style.maxWidth = savedWidths[colName];
            }
            
            const div = document.createElement("div");
            div.style.display = "flex";
            div.style.alignItems = "center";
            div.style.gap = "6px";
            div.style.width = "100%";
            div.style.overflow = "hidden";
            
            // Make all columns draggable
            th.draggable = true;
            th.style.cursor = "grab";
            th.style.userSelect = "none";
            
            th.addEventListener("dragstart", (e) => {
                e.dataTransfer.setData("text/plain", colName);
                e.dataTransfer.effectAllowed = "move";
                th.style.opacity = "0.5";
            });
            
            th.addEventListener("dragend", () => {
                th.style.opacity = "1";
                document.querySelectorAll(".data-table th").forEach(t => t.style.borderLeft = "");
            });
            
            th.addEventListener("dragover", (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                th.style.borderLeft = "2px solid var(--neon-cyan)";
            });
            
            th.addEventListener("dragleave", () => {
                th.style.borderLeft = "";
            });
            
            th.addEventListener("drop", (e) => {
                e.preventDefault();
                th.style.borderLeft = "";
                const draggedColName = e.dataTransfer.getData("text/plain");
                if (draggedColName) {
                    dropColumn(tableElement.id, draggedColName, colName, sortedFields);
                }
            });
            
            const span = document.createElement("span");
            span.textContent = colName;
            span.style.cursor = "pointer";
            span.style.flex = "1";
            span.style.overflow = "hidden";
            span.style.textOverflow = "ellipsis";
            span.onclick = (e) => { e.stopPropagation(); sortColumn(tableElement.id, colName); };
            div.appendChild(span);
            
            if (currentSortColumn === colName) {
                const sortIcon = document.createElement("span");
                sortIcon.textContent = currentSortDir === 1 ? "▲" : "▼";
                sortIcon.style.fontSize = "10px";
                div.appendChild(sortIcon);
            }
            
            th.appendChild(div);
            
            // Add resizer handle
            const resizer = document.createElement('div');
            resizer.className = 'col-resizer';
            resizer.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                isResizing = true;
                currentResizer = resizer;
                currentTh = th;
                startX = e.clientX;
                startWidth = th.offsetWidth;
                resizer.classList.add('col-resizing');
            });
            th.appendChild(resizer);
            
            return th;
        };
        
        sortedFields.forEach((col) => trHead.appendChild(createSortableHeader(col)));
        
        const thAction = document.createElement("th");
        thAction.textContent = "";
        trHead.appendChild(thAction);
        thead.appendChild(trHead);

        // Build Body
        items.forEach((item, rowIndex) => {
            const tr = document.createElement("tr");
            tr.setAttribute("data-id", item.id);
            tr.setAttribute("data-meta", JSON.stringify(item));
            
            const strId = String(item.id);
            if (selectedRows.has(strId)) tr.classList.add("selected");
            
            tr.addEventListener("click", (e) => {
                if (e.target.tagName === 'SPAN' && e.target.textContent === '⋮') return;
                
                const allRows = Array.from(tbody.querySelectorAll("tr"));
                if (e.shiftKey && lastSelectedRowIndex !== -1) {
                    const start = Math.min(lastSelectedRowIndex, rowIndex);
                    const end = Math.max(lastSelectedRowIndex, rowIndex);
                    document.getSelection().removeAllRanges();
                    
                    if (!e.ctrlKey && !e.metaKey) {
                        selectedRows.clear();
                        tbody.querySelectorAll("tr.selected").forEach(r => r.classList.remove("selected"));
                    }
                    
                    for (let i = start; i <= end; i++) {
                        const row = allRows[i];
                        if (row) {
                            const rid = row.getAttribute("data-id");
                            selectedRows.add(rid);
                            row.classList.add("selected");
                        }
                    }
                } else if (e.ctrlKey || e.metaKey) {
                    if (selectedRows.has(strId)) {
                        selectedRows.delete(strId);
                        tr.classList.remove("selected");
                    } else {
                        selectedRows.add(strId);
                        tr.classList.add("selected");
                    }
                    lastSelectedRowIndex = rowIndex;
                } else {
                    selectedRows.clear();
                    document.querySelectorAll(".data-table tr.selected").forEach(r => r.classList.remove("selected"));
                    selectedRows.add(strId);
                    tr.classList.add("selected");
                    lastSelectedRowIndex = rowIndex;
                }
            });
            
            tr.addEventListener("dblclick", (e) => {
                if (e.target.tagName === 'SPAN' && e.target.textContent === '⋮') return;
                if (window.navigateToStamp) {
                    window.navigateToStamp(item.pdf_path, item.xref, item.page);
                }
            });
            
            const addTd = (text, title, colName, fieldColor = null) => {
                const td = document.createElement("td");
                
                if (fieldColor) {
                    td.style.color = fieldColor;
                    td.style.backgroundColor = fieldColor + "33";
                    td.style.fontWeight = "bold";
                }
                
                if (query && text !== undefined && text !== null && String(text).toLowerCase().includes(query)) {
                    const strText = String(text);
                    const lowerText = strText.toLowerCase();
                    const index = lowerText.indexOf(query);
                    const before = strText.substring(0, index);
                    const match = strText.substring(index, index + query.length);
                    const after = strText.substring(index + query.length);
                    
                    if (before) td.appendChild(document.createTextNode(before));
                    const span = document.createElement("span");
                    span.className = "search-highlight";
                    span.textContent = match;
                    td.appendChild(span);
                    if (after) td.appendChild(document.createTextNode(after));
                } else {
                    td.textContent = text;
                }
                
                if (title) td.title = title;
                
                if (savedWidths[colName]) {
                    td.style.maxWidth = savedWidths[colName];
                    td.style.overflow = "hidden";
                    td.style.textOverflow = "ellipsis";
                }
                tr.appendChild(td);
            };
            
            sortedFields.forEach(field => {
                if (field === "UUID") addTd(item.stamp_uuid || item.id, null, field);
                else if (field === "Pattern") addTd(item.pattern_name ? "Pattern: " + item.pattern_name : "", null, field);
                else if (field === "System") {
                    if (tableElement.dataset.tableType === "air-outlets") {
                        addTd((item.fields && (item.fields["System Pattern"] || item.fields["System"])) ? (item.fields["System Pattern"] || item.fields["System"]) : "", null, field);
                    } else {
                        addTd(item.pattern_name || "", null, field);
                    }
                }
                else if (field === "PDF File") addTd(item.pdf_path ? item.pdf_path.split('/').pop().replace(/\\/g, '/').split('/').pop() : 'Unknown', item.pdf_path, field);
                else if (field === "Page") addTd(item.page, null, field);
                else {
                    const textVal = item.fields ? (item.fields[field] || "") : "";
                    let color = null;
                    if (item.conditional_formatting && item.conditional_formatting[field] && window.evaluateConditionalFormattingRaw) {
                        try {
                            const rules = JSON.parse(item.conditional_formatting[field]);
                            color = window.evaluateConditionalFormattingRaw(textVal, rules, item.fields);
                        } catch(e) {}
                    }
                    addTd(textVal, null, field, color);
                }
            });
            
            const tdAction = document.createElement("td");
            tdAction.style.textAlign = "center";
            const btnAction = document.createElement("span");
            btnAction.textContent = "⋮";
            btnAction.style.cursor = "pointer";
            btnAction.style.padding = "4px 8px";
            btnAction.style.fontWeight = "bold";
            btnAction.style.userSelect = "none";
            btnAction.style.fontSize = "16px";
            btnAction.title = "Edit Stamp(s)";
            btnAction.onclick = (e) => {
                e.stopPropagation();
                
                let stampsToEdit = [];
                if (selectedRows.has(strId) && selectedRows.size > 1) {
                    const selectedIds = Array.from(selectedRows);
                    stampsToEdit = items.filter(x => selectedIds.includes(String(x.id)));
                } else {
                    stampsToEdit = [item];
                }
                
                window.openStampMetaEditor(stampsToEdit);
            };
            tdAction.appendChild(btnAction);
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
                const match = name.match(/^(.*?)[ _]?\d+$/);
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
                const match = name.match(/^(.*?)[ _]?\d+$/);
                const bn = match ? match[1].trim() : name.trim();
                return bn === baseName;
            });
            
            if (stamps.length === 0) return;
            
            let maxNum = 0;
            stamps.forEach(s => {
                const name = s.pattern_name || s.name || s.title || "";
                const match = name.match(/\d+$/);
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

    const btnMoveStampPanel = document.getElementById('btn-move-stamp-panel');
    if (btnMoveStampPanel) {
        btnMoveStampPanel.addEventListener('click', () => {
            if (!window.currentPdfStamps || window.currentPdfStamps.length === 0) {
                alert('No stamps on this page.');
                return;
            }
            // Find the currently selected stamp (first selected one)
            const selected = window.currentPdfStamps.find(s =>
                document.querySelector(`.stamp-highlight-rect.selected[data-xref="${s.xref}"]`) ||
                document.querySelector(`#stamps-list .stamp-row.selected[data-xref="${s.xref}"]`)
            );
            if (!selected) {
                alert('Please select a stamp first (click a stamp row or stamp on the canvas).');
                return;
            }
            startStampMoveMode(selected);
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
                        source_page: srcStamp.page_num || srcStamp.page,
                        new_name: newName,
                        new_uuid: newUuid,
                        page_num: currentPageNum,
                        center_x: currentPdfX,
                        center_y: currentPdfY
                    })
                });
                
                const data = await res.json();
                if (!data.success) throw new Error(data.error || "Failed to copy stamp");
                
                if (window.reloadStampsAndPage) {
                    window.reloadStampsAndPage(currentPageNum);
                } else {
                    window.location.reload(); 
                }
                
                cleanup();
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

    function startStampMoveMode(stamp) {
        // Build a ghost matching the stamp's visual size
        const ghost = document.createElement('div');
        ghost.className = 'stamp-ghost stamp-move-ghost';

        // Compute visual dimensions from rect (already screen-space from app.js)
        let width = 40, height = 40;
        if (stamp.rect && stamp.rect.length === 4) {
            width  = Math.abs(stamp.rect[2] - stamp.rect[0]);
            height = Math.abs(stamp.rect[3] - stamp.rect[1]);
        }
        width  = Math.max(width,  20);
        height = Math.max(height, 20);

        ghost.style.position        = 'fixed';
        ghost.style.width           = width  + 'px';
        ghost.style.height          = height + 'px';
        ghost.style.border          = '2px dashed #f59e0b';
        ghost.style.backgroundColor = 'rgba(245,158,11,0.2)';
        ghost.style.borderRadius    = '4px';
        ghost.style.pointerEvents   = 'none';
        ghost.style.zIndex          = '99999';
        ghost.style.transform       = 'translate(-50%, -50%)';
        ghost.style.display         = 'none';
        ghost.style.cursor          = 'crosshair';

        // Label inside ghost
        const label = document.createElement('div');
        label.textContent = '✏️ Move';
        label.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:10px;color:#92400e;pointer-events:none;white-space:nowrap;';
        ghost.appendChild(label);

        document.body.appendChild(ghost);

        let currentPdfX   = null;
        let currentPdfY   = null;
        let currentPageNum = null;
        let isActive = true;

        const onMouseMove = (e) => {
            if (!isActive) return;
            ghost.style.display = 'block';

            const hitTarget = document.elementFromPoint(e.clientX, e.clientY);
            const wrapper   = hitTarget ? hitTarget.closest('.page-wrapper') : null;

            let snappedX = e.clientX;
            let snappedY = e.clientY;

            if (wrapper) {
                currentPageNum = parseInt(wrapper.dataset.page);
                const rect  = wrapper.getBoundingClientRect();
                const scale = rect.width / wrapper.offsetWidth;

                let pdfX = (e.clientX - rect.left) / scale;
                let pdfY = (e.clientY - rect.top)  / scale;

                // Snap to vector line
                if (window.canvasRenderers) {
                    const renderer = window.canvasRenderers.get(currentPageNum);
                    if (renderer) {
                        const snapItem = renderer.queryPoint(pdfX, pdfY, 20);
                        if (snapItem && snapItem.type === 'Line') {
                            const nearest = getClosestPointOnSegment(pdfX, pdfY,
                                snapItem.start[0], snapItem.start[1],
                                snapItem.end[0],   snapItem.end[1]);
                            pdfX = nearest.x;
                            pdfY = nearest.y;
                            snappedX = rect.left + pdfX * scale;
                            snappedY = rect.top  + pdfY * scale;
                        }
                    }
                }

                currentPdfX = pdfX;
                currentPdfY = pdfY;
            }

            ghost.style.left = snappedX + 'px';
            ghost.style.top  = snappedY + 'px';
        };

        const onClick = async (e) => {
            if (!isActive) return;
            e.preventDefault();
            e.stopPropagation();

            if (currentPdfX === null || currentPdfY === null || currentPageNum === null) {
                cleanup();
                return;
            }

            isActive = false;
            ghost.style.backgroundColor = 'rgba(0,200,100,0.35)';
            ghost.style.border          = '2px solid #16a34a';

            try {
                const title = stamp.pattern_name || stamp.name || stamp.title || 'Stamp ' + stamp.xref;
                if (window.appendScannerLog) window.appendScannerLog("> Moving stamp: " + title);

                const res = await fetch(
                    `/api/pdf/${encodeURIComponent(window.currentPdf)}/stamps/${stamp.xref}/move`,
                    {
                        method:  'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            page_num: currentPageNum,
                            center_x: currentPdfX,
                            center_y: currentPdfY,
                        }),
                    }
                );

                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Failed to move stamp');

                // Update in-memory stamp record
                if (window.currentPdfStamps) {
                    const idx = window.currentPdfStamps.findIndex(s => s.xref === stamp.xref);
                    if (idx !== -1) {
                        window.currentPdfStamps[idx].rect     = data.rect;
                        window.currentPdfStamps[idx].page_num = data.page_num;
                        window.currentPdfStamps[idx].xref     = data.xref;
                    }
                }

                // Re-render stamps list + canvas highlights
                if (window.renderStampsList)      window.renderStampsList();
                if (window.renderStampHighlights) window.renderStampHighlights();

                cleanup();
            } catch (err) {
                alert('Error moving stamp: ' + err.message);
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

        setTimeout(() => {
            window.addEventListener('click', onClick, true);
        }, 100);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('keydown', onKeyDown);
    }

    // Expose move mode globally so app.js stamp rows can trigger it
    window.startStampMoveMode = startStampMoveMode;
});
