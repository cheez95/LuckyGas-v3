# Quick Backend-Frontend Integration Plan

## Current Situation
- **Minimal Backend**: Running on port 8000 with auth + customers working
- **Frontend**: Running on port 5173, expecting multiple API endpoints
- **Gap**: Frontend calling APIs that return 404

## Immediate Actions (Next 30 minutes)

### Step 1: Add Mock Endpoints to Minimal Backend
Add these endpoints to `minimal_backend.py` to stop 404 errors:

```python
# Orders endpoint
@app.get("/api/v1/orders")
async def get_orders(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Return empty orders list for now"""
    return []

# Routes endpoint  
@app.get("/api/v1/routes")
async def get_routes(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Return empty routes list for now"""
    return []

# Products endpoint
@app.get("/api/v1/products")
async def get_products(
    current_user: dict = Depends(get_current_user)
):
    """Return sample products"""
    return [
        {"id": 1, "name": "20kg 瓦斯桶", "price": 800},
        {"id": 2, "name": "16kg 瓦斯桶", "price": 650}
    ]

# Predictions endpoint
@app.get("/api/v1/predictions/summary")
async def get_prediction_summary(
    current_user: dict = Depends(get_current_user)
):
    """Return mock prediction data"""
    return {
        "total": 0,
        "urgent": 0,
        "average_confidence": 0.85
    }

# WebSocket endpoint (basic)
@app.websocket("/api/v1/websocket/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except:
        pass
```

### Step 2: Copy Working Code from Complex Backend

1. **Order Management**
   - Copy order models and schemas
   - Simplify order service
   - Add basic CRUD operations

2. **Route Planning**  
   - Copy route models
   - Add basic route listing
   - Mock optimization for now

3. **Real Data Loading**
   - Query actual database tables
   - Return real customer data (already working)
   - Add real order data

### Step 3: Test Integration

1. Restart minimal backend with new endpoints
2. Refresh frontend dashboard
3. Verify no more 404 errors
4. Check that UI shows data (even if empty)

## File Changes Needed

### 1. `minimal_backend.py`
- Add mock endpoints (5 minutes)
- Import WebSocket from fastapi
- Add get_current_user dependency

### 2. Frontend (No changes needed initially)
- Already configured correctly
- Will automatically use new endpoints

### 3. Database Queries
- Use existing asyncpg connection
- Simple SELECT queries initially
- Add filtering/pagination later

## Expected Results

### Before Integration
- Dashboard shows errors
- Console full of 404s
- Only login works

### After Integration  
- Dashboard loads cleanly
- Stats show zeros (expected)
- Customer list shows data
- No console errors

## Next Steps After Mock Works

1. **Add Real Order Data**
   ```sql
   SELECT * FROM orders 
   WHERE created_at >= $1 
   LIMIT 100
   ```

2. **Add Real Route Data**
   ```sql
   SELECT * FROM routes
   WHERE date >= CURRENT_DATE
   ```

3. **Enable WebSocket Events**
   - Order status updates
   - New order notifications
   - Driver location updates

## Success Criteria

✅ Frontend dashboard loads without errors  
✅ API calls return 200 status  
✅ UI displays data (even if empty)  
✅ WebSocket connects successfully  
✅ User can navigate all pages

This plan gets the system functional in 30 minutes, then we can add real functionality incrementally.