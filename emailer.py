import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from dotenv import load_dotenv, set_key

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH, override=True)

logger = logging.getLogger("emailer")
logging.basicConfig(level=logging.INFO)

def get_smtp_config():
    load_dotenv(ENV_PATH, override=True)
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "").strip()
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    try:
        port = int(os.getenv("SMTP_PORT", "587").strip())
    except Exception:
        port = 587
    sender = os.getenv("SENDER_EMAIL", "").strip() or user or "flipkart.price.tracker@gmail.com"
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "sender": sender
    }

def is_smtp_configured():
    cfg = get_smtp_config()
    return bool(cfg["user"] and cfg["password"])

def save_smtp_config(user: str, password: str, host: str = "smtp.gmail.com", port: int = 587, sender: str = ""):
    if not os.path.exists(ENV_PATH):
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write("# Flipkart Tracker SMTP Configuration\n")
            
    set_key(ENV_PATH, "SMTP_HOST", host.strip())
    set_key(ENV_PATH, "SMTP_PORT", str(port))
    set_key(ENV_PATH, "SMTP_USER", user.strip())
    set_key(ENV_PATH, "SMTP_PASS", password.strip())
    set_key(ENV_PATH, "SENDER_EMAIL", (sender.strip() or user.strip()))
    
    # Reload environment
    load_dotenv(ENV_PATH, override=True)
    return True

def verify_smtp_credentials(host: str, port: int, user: str, password: str):
    """Attempts to connect and authenticate with SMTP server."""
    try:
        server = smtplib.SMTP(host, port, timeout=10)
        server.starttls()
        server.login(user, password)
        server.quit()
        return True, "SMTP connection and login successful!"
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed! If using Gmail, ensure you are using a 16-character 'App Password' (not your normal Gmail password)."
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

def send_price_drop_email(recipient_email: str, product_title: str, old_price: int, new_price: int, target_price: int, product_url: str, image_url: str):
    """Sends an email notification when a product price drops or meets target price."""
    if not recipient_email or "@" not in recipient_email:
        return False, "Invalid recipient email address"

    cfg = get_smtp_config()
    host = cfg["host"]
    port = cfg["port"]
    user = cfg["user"]
    password = cfg["password"]
    sender = cfg["sender"]

    subject = f"PRICE DROP ALERT: {product_title[:35]} is now Rs.{new_price:,}!"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 24px; border: 1px solid #334155; }}
            .header {{ text-align: center; border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 20px; }}
            .badge {{ background: #10b981; color: #022c22; font-weight: bold; padding: 6px 12px; border-radius: 20px; display: inline-block; font-size: 14px; }}
            .product-card {{ background: #0f172a; border-radius: 12px; padding: 16px; text-align: center; margin: 20px 0; border: 1px solid #334155; }}
            .product-img {{ max-height: 180px; object-fit: contain; margin-bottom: 12px; }}
            .title {{ font-size: 16px; font-weight: bold; color: #f1f5f9; margin-bottom: 12px; }}
            .old-price {{ text-decoration: line-through; color: #94a3b8; }}
            .new-price {{ color: #38bdf8; font-size: 24px; font-weight: bold; }}
            .btn {{ display: inline-block; background: #2874f0; color: #ffffff; font-weight: bold; padding: 12px 28px; text-decoration: none; border-radius: 10px; margin-top: 16px; }}
            .footer {{ text-align: center; font-size: 12px; color: #64748b; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span class="badge">TARGET PRICE MET!</span>
                <h2 style="color: #ffffff; margin-top: 10px;">Flipkart Price Drop Alert</h2>
            </div>

            <p style="color: #cbd5e1;">Good news! The product you are tracking on Flipkart has dropped in price!</p>

            <div class="product-card">
                <img src="{image_url}" class="product-img" alt="Product Image">
                <div class="title">{product_title}</div>
                
                <div style="margin-top: 15px;">
                    <span style="color: #94a3b8; font-size: 14px;">Previous Price: </span>
                    <span class="old-price">Rs.{old_price:,}</span>
                </div>

                <div style="margin-top: 5px;">
                    <span style="color: #38bdf8; font-size: 14px;">Current New Price: </span>
                    <span class="new-price">Rs.{new_price:,}</span>
                </div>

                <div style="margin-top: 5px; color: #f59e0b; font-size: 13px;">
                    Target Price Set: <b>Rs.{target_price:,}</b>
                </div>

                <a href="{product_url}" class="btn" target="_blank">Buy Now on Flipkart</a>
            </div>

            <div class="footer">
                This is an automated notification from your Flipkart Price Tracker App.
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Flipkart Price Tracker <{sender}>"
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_content, "html"))

    if not user or not password:
        logger.warning(f"[EMAIL NOT SENT - NO SMTP CREDENTIALS] Recipient: {recipient_email}")
        return False, "Email NOT delivered: Sender Gmail & App Password are not configured yet! Click 'Email Setup' to configure."

    try:
        server = smtplib.SMTP(host, port, timeout=15)
        server.starttls()
        server.login(user, password)
        server.sendmail(sender, [recipient_email], msg.as_string())
        server.quit()
        logger.info(f"Email successfully delivered to {recipient_email}")
        return True, f"Email notification successfully sent to {recipient_email}!"
    except smtplib.SMTPAuthenticationError:
        err = "Authentication Error! If using Gmail, make sure you generated a 16-character App Password (not normal password)."
        logger.error(err)
        return False, err
    except Exception as e:
        err = f"Failed to send email: {str(e)}"
        logger.error(err)
        return False, err
