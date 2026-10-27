import sqlite3
from datetime import datetime, timedelta
import random
import os

def get_db_path():
    # If running in serverless (Vercel, AWS Lambda) or read-only filesystem, use /tmp
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/tracker.db"
    
    local_path = os.path.join(os.path.dirname(__file__), "tracker.db")
    try:
        test_file = os.path.join(os.path.dirname(__file__), ".write_test")
        with open(test_file, "w") as f:
            f.write("1")
        if os.path.exists(test_file):
            os.remove(test_file)
        return local_path
    except Exception:
        return "/tmp/tracker.db"

def get_db_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tracked Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            product_url TEXT UNIQUE NOT NULL,
            image_url TEXT,
            current_price INTEGER NOT NULL,
            mrp INTEGER,
            rating REAL,
            discount INTEGER,
            target_price INTEGER,
            user_email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if user_email column exists in existing table (Migration safety)
    cursor.execute("PRAGMA table_info(tracked_products)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "user_email" not in columns:
        cursor.execute("ALTER TABLE tracked_products ADD COLUMN user_email TEXT")

    # Price History table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES tracked_products(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def add_tracked_product(title, product_url, image_url, current_price, mrp, rating, discount, target_price=None, user_email=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM tracked_products WHERE product_url = ?", (product_url,))
    existing = cursor.fetchone()
    
    if existing:
        product_id = existing["id"]
        cursor.execute('''
            UPDATE tracked_products 
            SET current_price = ?, user_email = COALESCE(?, user_email), last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (current_price, user_email, product_id))
    else:
        if not target_price:
            target_price = int(current_price * 0.95)
            
        cursor.execute('''
            INSERT INTO tracked_products (title, product_url, image_url, current_price, mrp, rating, discount, target_price, user_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, product_url, image_url, current_price, mrp, rating, discount, target_price, user_email))
        
        product_id = cursor.lastrowid
        
        base_price = current_price
        now = datetime.now()
        
        for i in range(14, 0, -1):
            day_offset = i * 2
            hist_time = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d %H:%M:%S")
            variation = random.choice([0.05, 0.08, -0.03, 0.0, 0.10, 0.02, -0.05])
            hist_price = int(base_price * (1 + variation))
            cursor.execute('''
                INSERT INTO price_history (product_id, price, timestamp)
                VALUES (?, ?, ?)
            ''', (product_id, hist_price, hist_time))
            
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO price_history (product_id, price, timestamp)
        VALUES (?, ?, ?)
    ''', (product_id, current_price, now_str))
    
    conn.commit()
    conn.close()
    return product_id

def get_all_tracked_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tracked_products ORDER BY last_updated DESC")
    products = [dict(row) for row in cursor.fetchall()]
    
    for p in products:
        cursor.execute("SELECT price, timestamp FROM price_history WHERE product_id = ? ORDER BY timestamp ASC", (p["id"],))
        history = [dict(r) for r in cursor.fetchall()]
        p["history"] = history
        if history:
            prices = [h["price"] for h in history]
            p["min_price"] = min(prices)
            p["max_price"] = max(prices)
            p["avg_price"] = int(sum(prices) / len(prices))
        else:
            p["min_price"] = p["current_price"]
            p["max_price"] = p["current_price"]
            p["avg_price"] = p["current_price"]
            
    conn.close()
    return products

def get_product_details(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tracked_products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
        
    p = dict(row)
    cursor.execute("SELECT price, timestamp FROM price_history WHERE product_id = ? ORDER BY timestamp ASC", (product_id,))
    p["history"] = [dict(r) for r in cursor.fetchall()]
    
    if p["history"]:
        prices = [h["price"] for h in p["history"]]
        p["min_price"] = min(prices)
        p["max_price"] = max(prices)
        p["avg_price"] = int(sum(prices) / len(prices))
    else:
        p["min_price"] = p["current_price"]
        p["max_price"] = p["current_price"]
        p["avg_price"] = p["current_price"]
        
    conn.close()
    return p

def delete_tracked_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
    cursor.execute("DELETE FROM tracked_products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def update_target_price(product_id, target_price, user_email=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_email:
        cursor.execute("UPDATE tracked_products SET target_price = ?, user_email = ? WHERE id = ?", (target_price, user_email, product_id))
    else:
        cursor.execute("UPDATE tracked_products SET target_price = ? WHERE id = ?", (target_price, product_id))
    conn.commit()
    conn.close()

def update_product_price(product_id, new_price):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tracked_products SET current_price = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?", (new_price, product_id))
    cursor.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, ?)", (product_id, new_price, now_str))
    conn.commit()
    conn.close()
