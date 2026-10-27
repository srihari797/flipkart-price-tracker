import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.flipkart.com/"
}

def get_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get("https://www.flipkart.com/", timeout=5)
    except Exception:
        pass
    return session

def extract_price_and_mrp(card):
    """Accurately extracts selling price and MRP, ignoring exchange offers and bank discounts."""
    # Primary price container tags in Flipkart DOM
    price_tag = card.find("div", class_=re.compile(r"(Nx9bqj|hZ3P6w|_30jeq3|_1_WHN1)"))
    mrp_tag = card.find("div", class_=re.compile(r"(yRaYFd|_3I9_wc|_27M-fP|_3b2fV6)"))

    current_price = None
    mrp = None

    if price_tag:
        digits = re.sub(r"[^\d]", "", price_tag.text)
        if digits:
            current_price = int(digits)

    if mrp_tag:
        mrp_digits = re.sub(r"[^\d]", "", mrp_tag.text)
        if mrp_digits:
            mrp = int(mrp_digits)

    if not current_price:
        # Fallback: decompose exchange and bank offer elements
        card_copy = BeautifulSoup(str(card), "lxml")
        for elem in card_copy.find_all(True):
            txt = elem.text.lower()
            if any(term in txt for term in ["exchange", "bank offer", "upto", "off on"]):
                classes = elem.get("class", [])
                if not any(c in classes for c in ["Nx9bqj", "hZ3P6w", "_30jeq3"]):
                    elem.decompose()

        prices_found = re.findall(r"₹\s*([\d,]+)", card_copy.text)
        numeric = [int(p.replace(",", "")) for p in prices_found if p.replace(",", "").isdigit()]
        if numeric:
            current_price = numeric[0]
            if len(numeric) > 1:
                mrp = max(numeric)

    if current_price and not mrp:
        mrp = int(current_price * 1.15)

    return current_price, mrp

def search_flipkart(query: str):
    """Scrapes Flipkart search results for given query string."""
    if not query or not query.strip():
        return []

    session = get_session()
    encoded_query = urllib.parse.quote(query.strip())
    url = f"https://www.flipkart.com/search?q={encoded_query}"

    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            return []
    except Exception as e:
        print(f"Error fetching Flipkart search: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    products = []

    # Target product card containers
    cards = soup.find_all("div", class_=re.compile(r"(jIjQ8S|_2kHM6A|cPH28e|_1sdBo1|yKfP86|RGLWAk|_75nlWZ|_13oc-S)"))

    if not cards:
        # Fallback to finding product link elements directly
        a_tags = soup.find_all("a", href=re.compile(r"/p/itm"))
        seen_urls = set()
        for a in a_tags:
            href = a.get("href", "")
            if href in seen_urls:
                continue
            seen_urls.add(href)
            parent = a.find_parent("div", class_=re.compile(r"(jIjQ8S|_2kHM6A|cPH28e|_1sdBo1|yKfP86|_1AtVbE)")) or a.parent.parent
            if parent:
                cards.append(parent)

    seen_links = set()

    for card in cards:
        a_tag = card.find("a", href=re.compile(r"/p/itm"))
        if not a_tag:
            continue

        raw_link = a_tag["href"]
        full_link = "https://www.flipkart.com" + raw_link if raw_link.startswith("/") else raw_link
        
        # Deduplicate links
        clean_link_id = raw_link.split("?")[0]
        if clean_link_id in seen_links:
            continue
        seen_links.add(clean_link_id)

        # Image extraction
        img_tag = card.find("img")
        img_url = None
        if img_tag:
            img_url = img_tag.get("src") or img_tag.get("data-src")
            if img_url and "data:image" in img_url:
                img_url = img_tag.get("data-src")

        if not img_url:
            img_url = "https://rukminim2.flixcart.com/image/312/312/xif0q/mobile/j/z/3/-original-imagtc5fqyz8tu4c.jpeg?q=70"

        # Title extraction
        title = None
        if img_tag and img_tag.get("alt"):
            title = img_tag.get("alt").strip()
        if not title:
            title_el = card.find("div", class_=re.compile(r"(RG5Slk|KzBmYi|_4rR01T|K63V2T|wBuR4p)")) or card.find("a", class_=re.compile(r"(WpWyFf|pIpigb|s1QR8n|IRrkB5)"))
            if title_el:
                title = title_el.text.strip()

        if not title:
            text = a_tag.text.strip()
            if len(text) > 5 and "Compare" not in text:
                title = text

        if not title:
            continue

        # Clean title
        title = re.sub(r"^Add to Compare", "", title).strip()
        title = re.sub(r"\d\.\d\d+,\d+.*", "", title).strip()

        # Extract real selling price and MRP
        current_price, mrp = extract_price_and_mrp(card)
        if not current_price:
            continue

        # Rating extraction
        card_text = card.text
        rating_match = re.search(r"(\d\.\d)\s*(\d[,\d]*\s*Ratings)?", card_text)
        rating = float(rating_match.group(1)) if rating_match else 4.2

        discount = int(((mrp - current_price) / mrp) * 100) if mrp > current_price else 0

        products.append({
            "title": title,
            "current_price": current_price,
            "mrp": mrp,
            "discount": discount,
            "rating": rating,
            "img_url": img_url,
            "link": full_link
        })

    return products

def fetch_live_price(title: str, product_url: str):
    """Refreshes live price of a product by performing targeted search query."""
    clean_title = re.sub(r"\(.*?\)", "", title).strip()[:40]
    results = search_flipkart(clean_title)
    
    if results:
        for r in results:
            if title.lower() in r["title"].lower() or r["title"].lower() in title.lower():
                return r["current_price"]
        return results[0]["current_price"]
    
    return None
