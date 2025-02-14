import streamlit as st
import psycopg2
import bcrypt
import pandas as pd
import joblib
import scipy.sparse as sp
from sklearn.metrics.pairwise import cosine_similarity

# ✅ Load Saved Models & Data
vectorizer = joblib.load("vectorizer.pkl")
scaler = joblib.load("scaler.pkl")
df = joblib.load("df.pkl")  # Load saved DataFrame
final_features = joblib.load("features.pkl")  # Load precomputed features

# ------------------- DATABASE CONNECTION -------------------

DB_URL = "postgresql://neondb_owner:npg_7JQelPFsVf2K@ep-purple-surf-a5w6dl4v-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    try:
        return psycopg2.connect(DB_URL)
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# ------------------- USER MANAGEMENT -------------------

def register_user(email, password):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        # Check if user already exists
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            st.error("User already exists. Please log in.")
            cur.close()
            conn.close()
            return False

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, %s)", (email, hashed_password, "user"))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error during registration: {e}")
        return False

def authenticate_user(email, password):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT password, role FROM users WHERE email = %s", (email,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            stored_password, role = result
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                return role
            else:
                return None
        else:
            return None
    except Exception as e:
        st.error(f"Error during authentication: {e}")
        return None

# ------------------- SESSION STATE INITIALIZATION -------------------

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "Home"

def navigate_to(page):
    st.session_state["page"] = page

# ------------------- HOME PAGE -------------------

def home_page():
    st.write("Welcome to the Job Recommendation System! Please log in or sign up to continue.")
    col1, col2 = st.columns(2)

    with col1:
        st.header("User Access")
        st.subheader("Sign Up")
        user_signup_email = st.text_input("Email (Sign Up)", key="signup_email")
        user_signup_password = st.text_input("Password (Sign Up)", type="password", key="signup_password")
        if st.button("Sign Up"):
            if register_user(user_signup_email, user_signup_password):
                st.success("Signup successful! Please log in.")
                navigate_to("Home")
        
        st.subheader("User Login")
        user_login_email = st.text_input("Email (Login)", key="login_email")
        user_login_password = st.text_input("Password (Login)", type="password", key="login_password")
        if st.button("Login"):
            role = authenticate_user(user_login_email, user_login_password)
            if role:
                st.session_state["logged_in"] = True
                st.session_state["role"] = role
                st.success("Login successful!")
                navigate_to("Dashboard")
            else:
                st.error("Invalid credentials.")

    DEFAULT_ADMIN_EMAIL = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD = "adminpassword"

    with col2:
        st.header("Admin Access")
        admin_login_email = st.text_input("Admin Email", key="admin_login_email")
        admin_login_password = st.text_input("Admin Password", type="password", key="admin_login_password")
        if st.button("Admin Login"):
            if admin_login_email == DEFAULT_ADMIN_EMAIL and admin_login_password == DEFAULT_ADMIN_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["role"] = "admin"
                st.success("Admin login successful!")

# ------------------- JOB RECOMMENDATION -------------------

def recommend_jobs(job_title, skills, section, experience, salary, locations, top_n=5):
    job_desc = f"{job_title} in {section} with skills: {', '.join(skills)}"
    user_text_vector = vectorizer.transform([job_desc])
    user_numeric_vector = scaler.transform(pd.DataFrame([[experience, salary]], columns=["Experience", "Salary"]))
    user_numeric_vector = sp.csr_matrix(user_numeric_vector)

    location_columns = [col for col in df.columns if col.startswith("location_")]
    user_location_vector = sp.csr_matrix((1, len(location_columns)))

    if locations:
        user_location_df = pd.DataFrame(0, index=[0], columns=location_columns)
        for location in locations:
            location_column_name = f"location_{location.lower()}"
            if location_column_name in user_location_df.columns:
                user_location_df[location_column_name] = 1
        user_location_vector = sp.csr_matrix(user_location_df.values)

    user_vector = sp.hstack([user_text_vector, user_numeric_vector, user_location_vector])
    similarity_scores = cosine_similarity(user_vector, final_features)
    ranked_indices = similarity_scores.argsort()[0][::-1][:top_n]

    return [{"Company": df.iloc[i]["Company"], "Job Link": df.iloc[i]["job_link"]} for i in ranked_indices]

# ------------------- DASHBOARD PAGE -------------------

def dashboard_page():
    st.sidebar.title("Dashboard Navigation")
    dashboard_option = st.sidebar.radio("Select Option", ["Job Recommendations", "Market Trends"])

    if dashboard_option == "Job Recommendations":
        st.header("Job Recommendation Dashboard")
        job_title = st.text_input("Job Title", "Data Scientist")
        skills = st.text_area("Skills (comma separated)", "Python, Machine Learning").split(",")
        section = st.text_input("Job Section", "AI")
        experience = st.number_input("Years of Experience", min_value=0, max_value=50, value=2)
        salary = st.number_input("Expected Salary (LPA)", min_value=0, max_value=100, value=10)
        locations = st.multiselect("Preferred Locations", ["Bangalore", "Pune"], ["Bangalore"])

        if st.button("Get Recommendations"):
            recommendations = recommend_jobs(job_title, skills, section, experience, salary, locations)
            if recommendations:
                st.subheader("Top Job Recommendations")
                for job in recommendations:
                    st.write(f"🏢 **Company:** {job['Company']}")
                    st.markdown(f"🔗 [Apply Here]({job['Job Link']})")
            else:
                st.write("No job recommendations found.")

# ------------------- APP NAVIGATION -------------------

if st.session_state["page"] == "Home":
    home_page()
elif st.session_state["page"] == "Dashboard":
    dashboard_page()
