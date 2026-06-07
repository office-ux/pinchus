importScripts('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js');

// Set up worker
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

const documentCache = new Map();

self.onmessage = async function(e) {
    const { type, url, pageNum, scale, canvas } = e.data;

    if (type === 'RENDER_PAGE') {
        try {
            let doc = documentCache.get(url);
            if (!doc) {
                doc = await pdfjsLib.getDocument(url).promise;
                documentCache.set(url, doc);
            }

            const page = await doc.getPage(pageNum);
            const viewport = page.getViewport({ scale: scale });

            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const ctx = canvas.getContext('2d');
            
            // Fill white background for transparent PDFs
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            const renderContext = {
                canvasContext: ctx,
                viewport: viewport,
                background: 'white'
            };

            await page.render(renderContext).promise;

            self.postMessage({ type: 'RENDER_COMPLETE', pageNum });
        } catch (err) {
            console.error('Worker render error:', err);
            self.postMessage({ type: 'RENDER_ERROR', pageNum, error: err.toString() });
        }
    } else if (type === 'CLEAR_CACHE') {
        documentCache.clear();
    }
};
