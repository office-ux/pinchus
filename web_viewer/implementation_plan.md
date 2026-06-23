# Optimize Hybrid 2 Vector Worker

The current Hybrid 2 engine is slow because it serializes and sends the entire drawings array (which can contain tens of thousands of objects) across the Web Worker boundary on *every single tile render request*.

## Proposed Changes

### 1. Update hybrid2_vector_worker.js
- Add a new INIT_PAGE message handler.
- When INIT_PAGE is received, the worker will build the SpatialHashGrid once and store it.
- Modify RENDER_VECTOR_TILE to no longer expect drawings or ounds. It will look up the pre-built spatial index using pageNum.

### 2. Update pp_hybrid2.js
- Send an INIT_PAGE message with the drawings array *once* per page immediately after the page data is fetched from the server.
- Add the h2UpdateWorkerVectorTiles function inside initApp (it was previously deleted due to syntax errors).
- Modify the RENDER_VECTOR_TILE dispatch in h2UpdateWorkerVectorTiles to only send lightweight coordinates (	ileX, 	ileY, etchScale, etc.), drastically reducing postMessage overhead.

This architectural shift guarantees that the main UI thread never blocks during scroll/zoom tile updates.
