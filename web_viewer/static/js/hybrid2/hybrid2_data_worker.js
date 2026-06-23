/**
 * hybrid2_data_worker.js
 * 
 * Off-thread data fetching, JSON parsing, and binary compilation.
 * Prevents the main thread from freezing when downloading dense blueprints.
 */

self.onmessage = async function(e) {
    if (e.data.type === 'FETCH_PAGE') {
        const { url, reqId } = e.data;
        
        try {
            // 1. Download JSON as raw text
            const res = await fetch(url);
            const jsonText = await res.text();
            
            // 2. Parse JSON into JS objects
            const data = JSON.parse(jsonText);
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            if (!data.drawings) data.drawings = [];

            // 3. Compile Binary Float32Array Buffer
            const bufferLen = data.drawings.reduce((acc, item) => {
                if (item.type === 'Line') return acc + 8; // type, color, thick, x1, y1, x2, y2, padding
                if (item.type === 'Rect') return acc + 7; // type, color, thick, x, y, w, h
                if (item.type === 'Polygon' || item.type === 'Arc/Curve') return acc + 4 + item.points.length * 2;
                return acc;
            }, 1);

            const buffer = new Float32Array(bufferLen);
            let offset = 0;
            
            for (let i = 0; i < data.drawings.length; i++) {
                let item = data.drawings[i];
                let typeId = 0;
                if (item.type === 'Line') typeId = 1;
                else if (item.type === 'Rect') typeId = 2;
                else if (item.type === 'Polygon') typeId = 3;
                else if (item.type === 'Arc/Curve') typeId = 4;
                else continue;

                buffer[offset++] = typeId;
                
                let colorHex = item.color_hex || '#000000';
                buffer[offset++] = parseInt(colorHex.replace('#', ''), 16);
                buffer[offset++] = item.thickness || 0.5;

                if (typeId === 1) { // Line
                    buffer[offset++] = item.start[0]; buffer[offset++] = item.start[1];
                    buffer[offset++] = item.end[0]; buffer[offset++] = item.end[1];
                    offset++; // align 8
                } else if (typeId === 2) { // Rect
                    buffer[offset++] = item.x; buffer[offset++] = item.y;
                    buffer[offset++] = item.width; buffer[offset++] = item.height;
                } else if (typeId === 3 || typeId === 4) { // Polygon / Arc
                    buffer[offset++] = item.points.length;
                    for (let p = 0; p < item.points.length; p++) {
                        buffer[offset++] = item.points[p][0];
                        buffer[offset++] = item.points[p][1];
                    }
                }
            }
            buffer[offset++] = 0; // EOF marker

            // 4. Return the parsed data and binary buffer back to main thread
            // We pass data back, main thread will still structured-clone it, 
            // but the HEAVY JSON parsing and HEAVY binary compilation is off-thread.
            self.postMessage({
                type: 'FETCH_SUCCESS',
                reqId: reqId,
                data: data,
                buffer: buffer
            }, [buffer.buffer]); // Transfer buffer ownership instantly

        } catch (err) {
            self.postMessage({
                type: 'FETCH_ERROR',
                reqId: reqId,
                error: err.toString()
            });
        }
    }
};
