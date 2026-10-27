from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os

import database as db
import scraper
import emailer

app = FastAPI(title="Flipkart Price Tracker & Product Intelligence UI", version="1.3.1")

# Initialize database
try:
    db.init_db()
except Exception as e:
    print(f"Warning: db.init_db() error: {e}")

# Safely mount static files if directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
try:
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception:
    pass

@app.middleware("http")
async def vercel_routing_middleware(request: Request, call_next):
    """Handle Vercel serverless rewrite paths seamlessly"""
    fwd_path = request.headers.get("x-matched-path") or request.headers.get("x-forwarded-uri") or request.headers.get("x-vercel-rewrite-path")
    if fwd_path:
        clean_path = fwd_path.split("?")[0]
        if request.scope["path"] in ["/api/index.py", "/api/index", "/api/index/"] and clean_path:
            request.scope["path"] = clean_path
    return await call_next(request)

class TrackProductRequest(BaseModel):
    title: str
    link: str
    img_url: Optional[str] = "https://rukminim2.flixcart.com/image/312/312/xif0q/mobile/j/z/3/-original-imagtc5fqyz8tu4c.jpeg?q=70"
    current_price: int
    mrp: Optional[int] = None
    rating: Optional[float] = 4.2
    discount: Optional[int] = 0
    target_price: Optional[int] = None
    user_email: Optional[str] = None

class TargetPriceRequest(BaseModel):
    product_id: int
    target_price: int
    user_email: Optional[str] = None

class TestEmailRequest(BaseModel):
    email: str
    product_title: Optional[str] = "Apple iPhone 17 (256 GB)"

def load_index_html():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "templates", "index.html"),
        os.path.join(base_dir, "api", "templates", "index.html"),
        os.path.join(os.getcwd(), "templates", "index.html"),
        os.path.join(os.getcwd(), "api", "templates", "index.html"),
        "/var/task/templates/index.html",
        "/var/task/api/templates/index.html"
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    return "<h1>Flipkart Scraper & Price Tracker UI</h1>"

@app.get("/", response_class=HTMLResponse)
@app.get("/api/index.py", response_class=HTMLResponse)
@app.get("/api/index", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/api/", response_class=HTMLResponse)
def get_dashboard():
    return HTMLResponse(content=load_index_html())

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Flipkart Price Tracker"}

@app.get("/api/search")
def search_products(q: str = Query(..., min_length=1, description="Product search query")):
    try:
        results = scraper.search_flipkart(q)
        return {"success": True, "count": len(results), "query": q, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tracked")
def get_tracked():
    products = db.get_all_tracked_products()
    return {"success": True, "count": len(products), "products": products}

@app.get("/api/tracked/{product_id}")
def get_tracked_item(product_id: int):
    p = db.get_product_details(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "product": p}

@app.post("/api/track")
def track_product(req: TrackProductRequest):
    mrp = req.mrp if req.mrp else int(req.current_price * 1.15)
    product_id = db.add_tracked_product(
        title=req.title,
        product_url=req.link,
        image_url=req.img_url,
        current_price=req.current_price,
        mrp=mrp,
        rating=req.rating,
        discount=req.discount,
        target_price=req.target_price,
        user_email=req.user_email
    )
    return {"success": True, "message": "Product tracked successfully", "product_id": product_id}

@app.delete("/api/track/{product_id}")
def untrack_product(product_id: int):
    db.delete_tracked_product(product_id)
    return {"success": True, "message": "Product removed from tracking"}

@app.post("/api/set-target-price")
def set_target_price(req: TargetPriceRequest):
    db.update_target_price(req.product_id, req.target_price, req.user_email)
    return {"success": True, "message": "Target price and alert email updated"}

@app.post("/api/test-email")
def test_email(req: TestEmailRequest):
    success, msg = emailer.send_price_drop_email(
        recipient_email=req.email,
        product_title=req.product_title,
        old_price=99900,
        new_price=79900,
        target_price=80000,
        product_url="https://www.flipkart.com",
        image_url="https://rukminim2.flixcart.com/image/312/312/xif0q/mobile/j/z/3/-original-imagtc5fqyz8tu4c.jpeg?q=70"
    )
    return {"success": success, "message": msg}

@app.post("/api/refresh/{product_id}")
def refresh_product_price(product_id: int):
    product = db.get_product_details(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    old_price = product["current_price"]
    new_price = scraper.fetch_live_price(product["title"], product["product_url"])
    if not new_price:
        new_price = old_price

    db.update_product_price(product_id, new_price)
    updated = db.get_product_details(product_id)

    # Email Alert check condition
    email_sent = False
    email_msg = None
    target_price = updated.get("target_price") or int(old_price * 0.95)
    user_email = updated.get("user_email")

    if user_email and (new_price <= target_price or new_price < old_price):
        email_sent, email_msg = emailer.send_price_drop_email(
            recipient_email=user_email,
            product_title=updated["title"],
            old_price=old_price,
            new_price=new_price,
            target_price=target_price,
            product_url=updated["product_url"],
            image_url=updated["image_url"]
        )

    return {
        "success": True, 
        "message": f"Updated price to ₹{new_price:,}" + (f" | 📧 {email_msg}" if email_sent else ""),
        "product": updated
    }

@app.post("/api/refresh-all")
def refresh_all_products():
    products = db.get_all_tracked_products()
    updated_count = 0
    email_alerts_sent = 0

    for p in products:
        old_price = p["current_price"]
        new_price = scraper.fetch_live_price(p["title"], p["product_url"])
        if new_price:
            db.update_product_price(p["id"], new_price)
            updated_count += 1
            
            target_price = p.get("target_price") or int(old_price * 0.95)
            user_email = p.get("user_email")
            if user_email and (new_price <= target_price or new_price < old_price):
                sent, _ = emailer.send_price_drop_email(
                    recipient_email=user_email,
                    product_title=p["title"],
                    old_price=old_price,
                    new_price=new_price,
                    target_price=target_price,
                    product_url=p["product_url"],
                    image_url=p["image_url"]
                )
                if sent:
                    email_alerts_sent += 1

    return {"success": True, "message": f"Refreshed {updated_count} products ({email_alerts_sent} email alerts sent)"}
