import smtplib
import psycopg2
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 🔹 PostgreSQL Database Connection
DB_URL = "postgresql://neondb_owner:npg_hnmkC3SAi7Lc@ep-steep-dawn-a87fu2ow-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"
conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

# 🔹 Fetch User Data (Adjust table/column names based on your database schema)
query = """
SELECT Email, PreferedOrderCat, CouponUsed, SatisfactionScore, OrderCount, Tenure, CashbackAmount FROM users;
"""
cursor.execute(query)
rows = cursor.fetchall()

# Convert Data to Pandas DataFrame for Easy Processing
columns = ["Email", "PreferedOrderCat", "CouponUsed", "SatisfactionScore", "OrderCount", "Tenure", "CashbackAmount"]
df = pd.DataFrame(rows, columns=columns)

# 🔹 Gmail SMTP Configuration (Use App Password for Security)
SENDER_EMAIL = "your_email@gmail.com"  # Replace with your Gmail
SENDER_PASSWORD = "your_app_password"  # Use App Password from Google

# Setup SMTP Server
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login(SENDER_EMAIL, SENDER_PASSWORD)

# 🔹 Function to Generate Personalized Notifications
def generate_notification(row, df, risk='low'):
    category = row['PreferedOrderCat']
    
    if row['CouponUsed'] > df['CouponUsed'].quantile(0.25) and risk == 'low':
        return f"Exclusive coupons for your favorite {category}!"
    
    elif row['SatisfactionScore'] < df['SatisfactionScore'].quantile(0.65) and risk == 'high':
        return "Not satisfied? Share your feedback and help us improve!"
    
    elif row['OrderCount'] > df['OrderCount'].quantile(0.25) and risk == 'high':
        return "Loyalty rewarded! Enjoy free shipping on your next order."
    
    elif row['Tenure'] > 3 and row['OrderCount'] == 0 and risk == 'high':
        return f"We miss you! Check out our latest {category} deals."
    
    elif row['CashbackAmount'] > df['CashbackAmount'].quantile(0.25) and risk == 'high':
        return f"Great news! You've earned cashback for your next {category} purchase."

    return f"Hey! We appreciate you. Check out new offers in {category}!"

# 🔹 Send Emails to Users
for _, row in df.iterrows():
    email = row["Email"]
    notif = generate_notification(row, df, risk="high")  # Generate personalized notification

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg['Subject'] = 'We Missed You!'
    msg.attach(MIMEText(notif, 'plain'))

    server.send_message(msg)
    print(f"✅ Email sent to {email}")

# 🔹 Close SMTP & Database Connections
server.quit()
cursor.close()
conn.close()
print("✅ All emails sent successfully & connections closed.")
