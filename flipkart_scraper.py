
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
import time

brand = input("Enter brand name: ")
model = input("Enter model name: ")

product = brand + " " + model
print(product)

driver = webdriver.Chrome()

url = f"https://www.flipkart.com/search?q={product}&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off"
driver.get(url)

time.sleep(5)

html = driver.page_source
soup = BeautifulSoup(html, "lxml")

print("FF6GgS" in html)

pages_div = soup.find("div", class_="FF6GgS")
print(pages_div)

if pages_div is None:
    pages = 1
else:
    span = pages_div.find("span")
    if span:
        pages = int(span.text.split(" ")[-1])
    else:
        pages = 1

print(f"Total available pages: {pages}")

scraped_items = []

for page in range(1, pages + 1):
    url = f"https://www.flipkart.com/search?q={product}&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&page={page}"
    driver.get(url)
    time.sleep(5)

    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")

    # Type 1 layout
    type1_page = soup.find_all("div", class_="RGLWAk")

    if type1_page:
        for item in type1_page:
            a_tag = item.find("a", class_="pIpigb")
            price_div = item.find("div", class_="hZ3P6w")

            if price_div is None or a_tag is None:
                continue

            name = a_tag.get("title")

            if not name:
                continue

            price_text = price_div.text.strip()
            price_digits = re.sub(r"[^\d]", "", price_text)

            if not price_digits:
                continue

            price = int(price_digits)
            name_lower = name.lower()

            if brand.lower() in name_lower and model.lower() in name_lower:
                scraped_items.append({
                    "title": name,
                    "price": price
                })

    else:
        # Type 2 layout
        type2_page = soup.find_all("div", class_="ZFwe0M row")

        for item in type2_page:
            name_div = item.find("div", class_="RG5Slk")
            price_div = item.find("div", class_="hZ3P6w DeU9vF")

            if name_div is None or price_div is None:
                continue

            name_text = name_div.text.strip()
            price_text = price_div.text.strip()

            price_digits = re.sub(r"[^\d]", "", price_text)

            if not price_digits:
                continue

            price = int(price_digits)

            if brand.lower() in name_text.lower() and model.lower() in name_text.lower():
                scraped_items.append({
                    "title": name_text,
                    "price": price
                })

driver.quit()

seen = set()
unique_products = []

for item in scraped_items:
    key = (item["title"], item["price"])

    if key in seen:
        continue

    seen.add(key)
    unique_products.append(item)

print("Total scraped items:", len(scraped_items))
print("Total unique products:", len(unique_products))

for p in unique_products:
    print("-", p["title"], "₹", p["price"])

