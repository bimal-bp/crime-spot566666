import streamlit as st
import psycopg2
import bcrypt
import ast  # To convert database array strings into Python lists
import pandas as pd
import joblib
import scipy.sparse as sp
from sklearn.metrics.pairwise import cosine_similarity

# Database connection
def get_db_connection():
    try:
        return psycopg2.connect(
            dbname="neondb",
            user="neondb_owner",
            password="npg_7JQelPFsVf2K",
            host="ep-purple-surf-a5w6dl4v-pooler.us-east-2.aws.neon.tech",
            port="5432",
            sslmode="require"
        )
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None


# Hash password
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Verify password
def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Authenticate user
def authenticate_user(email, password):
    conn = get_db_connection()
    if not conn:
        return None
    
    cur = conn.cursor()
    cur.execute("SELECT password, role FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    conn.close()
    
    if user and check_password(password, user[0]):
        return user[1]  # Return role (user/admin)
    return None

# Save new user
def register_user(email, password):
    conn = get_db_connection()
    if not conn:
        return False
    
    cur = conn.cursor()
    try:
        hashed_password = hash_password(password)
        cur.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, 'user')", (email, hashed_password))
        conn.commit()
        return True
    except psycopg2.errors.UniqueViolation:
        st.error("Email already exists. Please use a different email.")
        return False
    finally:
        conn.close()

# Parse field safely
def parse_field(data):
    if data is None:
        return []
    if isinstance(data, str):
        try:
            return ast.literal_eval(data)
        except (ValueError, SyntaxError):
            return [item.strip() for item in data.split(",")]
    elif isinstance(data, list):
        return data
    return []

# Streamlit UI
st.title("🔍 Job Recommendation System")
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Login", "Signup", "Dashboard", "Admin"])

if page == "Home":
    st.write("Welcome to the Job Recommendation System! Please sign up or log in to continue.")

elif page == "Signup":
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Sign Up"):
        if register_user(email, password):
            st.success("Signup successful! Please log in.")

elif page == "Login":
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = authenticate_user(email, password)
        if role:
            st.session_state["logged_in"] = True
            st.session_state["role"] = role
            st.success("Login successful! Go to Dashboard.")
        else:
            st.error("Invalid credentials.")

elif page == "Dashboard" and st.session_state.get("logged_in"):
    st.write("Enter your job preferences to get recommendations!")
    job_title = st.text_input("Job Title", "DevOps Engineer")
    skills = st.text_area("Skills", "Docker, Kubernetes").split(", ")
    section = st.text_input("Job Section", "IT")
    experience = st.number_input("Years of Experience", min_value=0, max_value=50, value=5)
    salary = st.number_input("Expected Salary (in LPA)", min_value=0, max_value=100, value=15)
    available_locations = ["Pune", "Bangalore", "Hyderabad", "Mumbai", "Delhi", "Chennai"]
    selected_locations = st.multiselect("Preferred Locations", available_locations, ["Pune"])
    if st.button("Get Recommendations"):
        recommendations = recommend_jobs(job_title, skills, section, experience, salary, selected_locations)
        if recommendations:
            st.subheader("Top Job Recommendations")
            for idx, job in enumerate(recommendations, start=1):
                st.write(f"### 🔹 Recommendation {idx}")
                st.write(f"🏢 **Company:** {job['Company']}")
                st.markdown(f"🔗 [Apply Here]({job['Job Link']})")
        else:
            st.write("No job recommendations found. Try modifying your search criteria.")

elif page == "Admin" and st.session_state.get("role") == "admin":
    st.write("Admin Dashboard - Manage Users and Jobs")
    # Additional admin functionalities can be added here.

elif page == "Market Trends":
    st.write("📊 Market Trends coming soon!")
