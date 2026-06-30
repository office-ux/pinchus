const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
    
    await page.goto('http://127.0.0.1:5000/');
    await new Promise(r => setTimeout(r, 5000));
    
    const links = await page.$$('.pdf-link-zone');
    console.log('Links found:', links.length);
    
    if (links.length > 0) {
        await links[0].click();
        await new Promise(r => setTimeout(r, 1000));
        
        const modal = await page.$eval('#stamp-meta-modal', el => el.style.display);
        console.log('Modal display:', modal);
    } else {
        console.log('No links found. Please open a PDF with links.');
    }
    
    await browser.close();
})();
