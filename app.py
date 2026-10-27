from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os

import database as db
import scraper
import emailer

app = FastAPI(title="Flipkart Price Tracker & Product Intelligence UI", version="1.2.0")

# Ensure DB initialized on startup
db.init_db()

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

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

class SmtpConfigRequest(BaseModel):
    user: str
    password: str
    host: Optional[str] = "smtp.gmail.com"
    port: Optional[int] = 587
    sender: Optional[str] = ""

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    index_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Flipkart Scraper & Price Tracker UI</h1>")

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

@app.get("/api/smtp-config")
def get_smtp_status():
    cfg = emailer.get_smtp_config()
    is_conf = emailer.is_smtp_configured()
    return {
        "success": True,
        "configured": is_conf,
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "sender": cfg["sender"]
    }

@app.post("/api/smtp-config")
def update_smtp_config(req: SmtpConfigRequest):
    if not req.user or not req.password:
        raise HTTPException(status_code=400, detail="Sender email and App Password are required")
    
    host = req.host or "smtp.gmail.com"
    port = req.port or 587
    ok, verify_msg = emailer.verify_smtp_credentials(host, port, req.user, req.password)
    if not ok:
        return {"success": False, "message": verify_msg}
    
    emailer.save_smtp_config(
        user=req.user,
        password=req.password,
        host=host,
        port=port,
        sender=req.sender or req.user
    )
    return {"success": True, "message": "Email settings saved and verified successfully!"}

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
