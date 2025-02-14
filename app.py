import smtplib
import psycopg2
import pandas as pd
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 🔹 Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🔹 Environment Variables (Recommended for Security)
DB_URL = os.getenv("DB_URL", "postgresql://neondb_owner:npg_hnmkC3SAi7Lc@ep-steep-dawn-a87fu2ow-pooler.eastus2.azure.neon.tech/neondb?sslmode=require")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "bimalpatra@gmail.com")  # Replace with actual email
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "Trishamami@9")  # Use App Password

# 🔹 Connect to PostgreSQL Database
try:
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    logging.info("✅ Database connection successful.")
except Exception as e:
    logging.error(f"❌ Database connection failed: {e}")
    exit()

# 🔹 Fetch User Data (Ensure column names match your database)
query = """
SELECT email, preferedordercat, couponused, satisfactionscore, ordercount, tenure, cashbackamount FROM users;
"""
try:
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = ["Email", "PreferedOrderCat", "CouponUsed", "SatisfactionScore", "OrderCount", "Tenure", "CashbackAmount"]
    df = pd.DataFrame(rows, columns=columns)
    logging.info(f"✅ Retrieved {len(df)} user records.")
except Exception as e:
    logging.error(f"❌ Failed to fetch data: {e}")
    cursor.close()
    conn.close()
    exit()

# 🔹 Gmail SMTP Configuration
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    logging.info("✅ SMTP login successful.")
except Exception as e:
    logging.error(f"❌ SMTP login failed: {e}")
    cursor.close()
    conn.close()
    exit()

# 🔹 Function to Generate Personalized Notifications
def generate_notification(row, df):
    category = row['PreferedOrderCat']

    if row['CouponUsed'] > df['CouponUsed'].quantile(0.25):
        return f"Exclusive coupons for your favorite {category}!"
    
    elif row['SatisfactionScore'] < df['SatisfactionScore'].quantile(0.65):
        return "Not satisfied? Share your feedback and help us improve!"
    
    elif row['OrderCount'] > df['OrderCount'].quantile(0.25):
        return "Loyalty rewarded! Enjoy free shipping on your next order."
    
    elif row['Tenure'] > 3 and row['OrderCount'] == 0:
        return f"We miss you! Check out our latest {category} deals."
    
    elif row['CashbackAmount'] > df['CashbackAmount'].quantile(0.25):
        return f"Great news! You've earned cashback for your next {category} purchase."

    return f"Hey! We appreciate you. Check out new offers in {category}!"

# 🔹 Send Emails
for _, row in df.iterrows():
    email = row["Email"]
    notif = generate_notification(row, df)

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = email
        msg['Subject'] = 'We Missed You!'
        msg.attach(MIMEText(notif, 'plain'))
        
        server.send_message(msg)
        logging.info(f"✅ Email sent to {email}")
    except Exception as e:
        logging.error(f"❌ Failed to send email to {email}: {e}")

# 🔹 Close Connections
server.quit()
cursor.close()
conn.close()
logging.info("✅ All emails sent successfully & connections closed.")
