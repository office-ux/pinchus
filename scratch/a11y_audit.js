const fs = require('fs');

function analyzeHTML(filename, html) {
    const issues = [];
    const warnings = [];
    const good = [];

    // 1. Document-level checks
    if (html.includes('lang="en"')) good.push('✓ html[lang] present');
    else issues.push('CRITICAL: Missing lang attribute on <html>');

    if (html.includes('<title>')) good.push('✓ <title> present');
    else issues.push('CRITICAL: Missing <title> element');

    if (html.includes('meta name="viewport"')) good.push('✓ viewport meta present');
    else warnings.push('WARNING: Missing viewport meta');

    if (html.includes('meta name="description"')) good.push('✓ meta description present');
    else warnings.push('WARNING: Missing <meta name="description">');

    // 2. Heading hierarchy
    const headingRe = /<h(\d)[^>]*>/g;
    let m;
    const headingLevels = [];
    while ((m = headingRe.exec(html)) !== null) {
        headingLevels.push(parseInt(m[1]));
    }
    if (headingLevels.length === 0) {
        warnings.push('WARNING: No heading elements found');
    } else {
        if (headingLevels[0] !== 1) warnings.push('WARNING: First heading is h' + headingLevels[0] + ', should be h1');
        for (let i = 1; i < headingLevels.length; i++) {
            if (headingLevels[i] > headingLevels[i-1] + 1) {
                warnings.push('WARNING: Heading level skips from h' + headingLevels[i-1] + ' to h' + headingLevels[i]);
            }
        }
        good.push('✓ Headings: ' + headingLevels.map(l => 'h' + l).join(' → '));
    }

    // 3. Landmark regions
    if (html.includes('<main')) good.push('✓ <main> landmark present');
    else warnings.push('WARNING: Missing <main> landmark');

    if (html.includes('<nav')) good.push('✓ <nav> landmark present');
    if (html.includes('<aside')) good.push('✓ <aside> landmarks present');

    // 4. Form labels
    const inputs = html.match(/<input[^>]*>/g) || [];
    inputs.forEach(inp => {
        if (inp.includes('type="hidden"') || inp.includes('style="display: none"') || inp.includes('display:none')) return;
        const idMatch = inp.match(/id="([^"]+)"/);
        if (!idMatch) {
            if (!inp.includes('aria-label')) {
                warnings.push('WARNING: Input without id or aria-label: ' + inp.substring(0, 80));
            }
            return;
        }
        const id = idMatch[1];
        const hasLabel = html.includes('for="' + id + '"');
        const hasAriaLabel = inp.includes('aria-label');
        const hasAriaLabelledby = inp.includes('aria-labelledby');
        if (!hasLabel && !hasAriaLabel && !hasAriaLabelledby) {
            issues.push('ISSUE: Input #' + id + ' has no associated label, aria-label, or aria-labelledby');
        }
    });

    // 5. Buttons accessible names
    const btnRe = /<button[^>]*>([\s\S]*?)<\/button>/g;
    while ((m = btnRe.exec(html)) !== null) {
        const btnTag = m[0];
        const innerText = m[1].replace(/<[^>]*>/g, '').trim();
        const hasAriaLabel = btnTag.includes('aria-label');
        const hasTitle = btnTag.includes('title=');
        
        if (innerText.length <= 2 && !hasAriaLabel && !hasTitle) {
            issues.push('ISSUE: Button with short/icon-only text and no aria-label/title: "' + innerText + '" → ' + btnTag.substring(0, 120));
        }
    }

    // 6. Links accessible names
    const linkRe = /<a[^>]*>([\s\S]*?)<\/a>/g;
    while ((m = linkRe.exec(html)) !== null) {
        const linkTag = m[0];
        const innerText = m[1].replace(/<[^>]*>/g, '').trim();
        const hasAriaLabel = linkTag.includes('aria-label');
        const hasTitle = linkTag.includes('title=');
        if (!innerText && !hasAriaLabel && !hasTitle) {
            issues.push('ISSUE: Link with no accessible name: ' + linkTag.substring(0, 100));
        }
    }

    // 7. Modal ARIA attributes
    if (html.includes('class="modal"') && !html.includes('role="dialog"')) {
        issues.push('ISSUE: Modal element missing role="dialog"');
    }
    // Check for aria-modal
    const modalDivs = html.match(/<div[^>]*class="[^"]*modal[^"]*"[^>]*>/g) || [];
    modalDivs.forEach(md => {
        if (!md.includes('role="dialog"') && !md.includes('role="alertdialog"')) {
            if (!md.includes('modal-content') && !md.includes('modal-body') && 
                !md.includes('modal-header') && !md.includes('modal-footer') &&
                !md.includes('modal-box') && !md.includes('modal-close') &&
                !md.includes('modal-error')) {
                warnings.push('WARNING: Modal-like div missing role="dialog": ' + md.substring(0, 100));
            }
        }
    });

    // 8. Close buttons
    const closeRe = /<(button|span)[^>]*class="[^"]*close[^"]*"[^>]*>/g;
    while ((m = closeRe.exec(html)) !== null) {
        if (!m[0].includes('aria-label')) {
            warnings.push('WARNING: Close button/element missing aria-label: ' + m[0].substring(0, 100));
        }
    }

    // 9. Images without alt
    const imgs = html.match(/<img[^>]*>/g) || [];
    imgs.forEach(img => {
        if (!img.includes('alt=')) {
            issues.push('ISSUE: Image missing alt attribute: ' + img.substring(0, 80));
        }
    });

    // 10. Tables
    if (html.includes('<table')) {
        if (html.includes('<thead>') && html.includes('<th>')) good.push('✓ Table has proper header structure');
        if (!html.includes('<caption')) warnings.push('WARNING: Table missing <caption> element');
    }

    // 11. select without label
    const selects = html.match(/<select[^>]*>/g) || [];
    selects.forEach(sel => {
        const selId = sel.match(/id="([^"]+)"/);
        if (selId) {
            const hasLabel = html.includes('for="' + selId[1] + '"');
            if (!hasLabel && !sel.includes('aria-label')) {
                warnings.push('WARNING: <select> #' + selId[1] + ' should verify label association');
            }
        }
    });

    // 12. Color contrast potential issues (static CSS analysis)
    // Check for --text-secondary (#94a3b8) on dark backgrounds
    // #94a3b8 on #060d1a = ~5.39:1 (passes AA normal text)
    // #94a3b8 on #0f172a = ~5.08:1 (passes AA normal text)
    // But at small font sizes (< 14px bold / < 18.66px normal) it needs 4.5:1

    return { filename, issues, warnings, good };
}

// Analyze all templates
const files = [
    { name: 'login.html', path: 'c:/pinchus/web_viewer/templates/login.html' },
    { name: 'register.html', path: 'c:/pinchus/web_viewer/templates/register.html' },
    { name: 'home.html', path: 'c:/pinchus/web_viewer/templates/home.html' },
    { name: 'index.html', path: 'c:/pinchus/web_viewer/templates/index.html' },
];

files.forEach(f => {
    const html = fs.readFileSync(f.path, 'utf8');
    const result = analyzeHTML(f.name, html);
    
    console.log(`\n${'='.repeat(60)}`);
    console.log(`  ${f.name}`);
    console.log(`${'='.repeat(60)}`);
    
    console.log('\n  GOOD:');
    result.good.forEach(g => console.log('    ' + g));
    
    if (result.issues.length > 0) {
        console.log('\n  ISSUES:');
        result.issues.forEach(i => console.log('    ❌ ' + i));
    } else {
        console.log('\n  No critical issues found');
    }
    
    if (result.warnings.length > 0) {
        console.log('\n  WARNINGS:');
        result.warnings.forEach(w => console.log('    ⚠️  ' + w));
    }
});
