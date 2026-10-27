# 🛒 Flipkart Price Tracker & Intelligence Dashboard

A full-stack, real-time web application to scrape, track, and analyze Flipkart product prices with interactive charts, target price alerts, and automated email notifications.

![Dashboard Preview](https://img.shields.io/badge/Status-Live%20Active-emerald?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)

---

## ✨ Features

- 🔍 **Real-Time Live Flipkart Search**: Extracts live selling prices, MRPs, discounts, star ratings, and thumbnails directly from Flipkart.
- 🎯 **Target Price Monitoring**: Set custom target price thresholds and receive visual "Target Hit!" badges and email alerts when prices drop.
- 📈 **Interactive Price History Charts**: Visualizes historical price trends, min/max/average metrics using Chart.js.
- 📧 **Automated Price Drop Email Alerts**: Centralized server-side SMTP email notification pipeline dispatching alerts directly to user inboxes.
- ⚡ **Accurate Price Disambiguation**: Custom DOM parser filtering out exchange offers and promotional text (e.g. *"Upto ₹70,550 Off on Exchange"*) to capture the true selling price.
- 🎨 **Modern Glassmorphic UI**: Single-page application styled with Tailwind CSS, responsive on mobile and desktop.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **Scraping Engine**: BeautifulSoup4, Requests (Session-based with custom browser headers)
- **Database**: SQLite3 (Relational schema: `tracked_products` 1-to-many `price_history`)
- **Frontend**: Vanilla JavaScript (ES6+), Tailwind CSS, Chart.js, FontAwesome
- **Notifications**: Python `smtplib` + MIME HTML templates (Gmail SMTP / Cloud Email Services)

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/srihari797/flipkart-price-tracker.git
cd flipkart-price-tracker
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Email Alerts (Optional)
Copy `.env.example` to `.env` and configure your sender credentials:
```bash
cp .env.example .env
```
Add your details:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_16_digit_app_password
SENDER_EMAIL=your_email@gmail.com
```

### 4. Run the Application
```bash
python -m uvicorn app:app --reload --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

## ☁️ Deployment (e.g. Render / Railway)

1. Connect your repository to **[Render.com](https://render.com)**.
2. Select **Web Service**.
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `SMTP_HOST`: `smtp.gmail.com`
   - `SMTP_PORT`: `587`
   - `SMTP_USER`: `your_email@gmail.com`
   - `SMTP_PASS`: `your_16_digit_app_password`
   - `SENDER_EMAIL`: `your_email@gmail.com`

---

## 📄 License
MIT License. Created by [Srihari](https://github.com/srihari797).
