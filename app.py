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

# Database connection
def get_db_connection():
    try:
        return psycopg2.connect(
            "postgresql://neondb_owner:npg_7JQelPFsVf2K@ep-purple-surf-a5w6dl4v-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
        )
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# ------------------- USER MANAGEMENT FUNCTIONS -------------------

def register_user(email, password):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        # Check if user already exists:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            st.error("User already exists. Please log in.")
            cur.close()
            conn.close()
            return False

        # Hash the password:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # Insert new user with default role 'user'
        cur.execute(
            "INSERT INTO users (email, password, role) VALUES (%s, %s, %s)",
            (email, hashed_password, "user")
        )
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
            # Compare the provided password with the stored hashed password.
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

# ------------------- PAGE NAVIGATION -------------------

def navigate_to(page):
    st.session_state["page"] = page

# ------------------- HOME PAGE -------------------

def home_page():
    st.write("Welcome to the Job Recommendation System! Please log in or sign up to continue.")
    col1, col2 = st.columns(2)

    # ---------- User Access (Signup & Login) ----------
    with col1:
        st.header("User Access")
        
        st.subheader("Sign Up")
        user_signup_email = st.text_input("Email (Sign Up)", key="signup_email")
        user_signup_password = st.text_input("Password (Sign Up)", type="password", key="signup_password")
        if st.button("Sign Up", key="signup_button"):
            if register_user(user_signup_email, user_signup_password):
                st.success("Signup successful! Please log in.")
                navigate_to("Home")  # Stay on home page to allow login
            else:
                st.error("Signup failed. Please try again.")
                
        st.subheader("User Login")
        user_login_email = st.text_input("Email (Login)", key="login_email")
        user_login_password = st.text_input("Password (Login)", type="password", key="login_password")
        if st.button("Login", key="login_button"):
            role = authenticate_user(user_login_email, user_login_password)
            if role:
                st.session_state["logged_in"] = True
                st.session_state["role"] = role
                st.success("Login successful!")
                navigate_to("Dashboard")
            else:
                st.error("Invalid credentials.")

    # ---------- Admin Access ----------
    DEFAULT_ADMIN_EMAIL = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD = "adminpassword"
    
    with col2:
        st.header("Admin Access")
        admin_login_email = st.text_input("Admin Email", key="admin_login_email")
        admin_login_password = st.text_input("Admin Password", type="password", key="admin_login_password")
    
        if st.button("Admin Login", key="admin_login_button"):
            if admin_login_email == DEFAULT_ADMIN_EMAIL and admin_login_password == DEFAULT_ADMIN_PASSWORD:
                st.session_state["logged_in"] = True
                st.session_state["role"] = "admin"
                st.success("Admin login successful!")
            else:
                st.error("Invalid admin credentials.")

# Fetch market trends
def fetch_market_trends():
    """Fetch market trends from the database"""
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT trend_text, skill_link FROM market_trends")
        trends = cur.fetchall()
        cur.close()
        conn.close()
        return trends
    return []

# ------------------- USER DASHBOARD -------------------

import psycopg2
import streamlit as st
import pandas as pd
import scipy.sparse as sp
from sklearn.metrics.pairwise import cosine_similarity

# Database connection details
DB_URL = "postgresql://neondb_owner:npg_hnmkC3SAi7Lc@ep-steep-dawn-a87fu2ow-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"

# Function to create the table in PostgreSQL
def create_table():
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_recommendations (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            job_title TEXT NOT NULL,
            company TEXT NOT NULL,
            job_link TEXT NOT NULL
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Function to insert job recommendations into the database
def save_job_recommendations(user_email, job_title, recommendations):
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    for job in recommendations:
        cursor.execute('''
            INSERT INTO job_recommendations (user_email, job_title, company, job_link)
            VALUES (%s, %s, %s, %s)
        ''', (user_email, job_title, job.get("Company", "Unknown"), job.get("Job Link", "#")))
    conn.commit()
    cursor.close()
    conn.close()

# Function to fetch saved jobs for a user
def get_saved_jobs(user_email):
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT job_title, company, job_link FROM job_recommendations WHERE user_email = %s
    ''', (user_email,))
    jobs = cursor.fetchall()
    cursor.close()
    conn.close()
    return jobs

# Function to fetch job recommendations (Replace with actual logic)
def recommend_jobs(job_title, skills, section, experience, salary, locations, top_n=5):
    """Returns top N job recommendations with Company Name and Job Link."""
    
    job_desc = f"{job_title} in {section} with skills: {', '.join(skills)}"
    user_text_vector = vectorizer.transform([job_desc])

    user_numeric_vector = pd.DataFrame([[experience, salary]], columns=["Experience", "Salary"])
    user_numeric_vector = scaler.transform(user_numeric_vector)
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

    recommended_jobs = [
        {
            "Company": df.iloc[i]["Company"],
            "Job Link": df.iloc[i]["job_link"]
        }
        for i in ranked_indices
    ]
    return recommended_jobs

# Dashboard Page
def dashboard_page():
    st.sidebar.title("Dashboard Navigation")
    dashboard_option = st.sidebar.radio("Select Option", ["Job Recommendations", "My Saved Jobs", "Market Trends"])

    if dashboard_option == "Job Recommendations":
        st.header("Job Recommendation Dashboard")
        user_email = st.text_input("Enter your email")
        job_title = st.text_input("Job Title", "DevOps Engineer")
        skills_input = st.text_area("Skills (comma separated)", "Docker, Kubernetes")
        skills = [skill.strip() for skill in skills_input.split(",") if skill.strip()]
        section = st.text_input("Job Section", "IT")
        experience = st.number_input("Years of Experience", min_value=0, max_value=50, value=5)
        salary = st.number_input("Expected Salary (in LPA)", min_value=0, max_value=100, value=15)
        available_locations = ["Pune", "Bangalore", "Hyderabad", "Mumbai", "Delhi", "Chennai"]
        selected_locations = st.multiselect("Preferred Locations", available_locations, ["Pune"])

        if st.button("save & Get Recommendations"):
            recommendations = recommend_jobs(job_title, skills, section, experience, salary, selected_locations)

            if recommendations:
                st.subheader("Top Job Recommendations")

                # Save jobs to the database
                save_job_recommendations(user_email, job_title, recommendations)

                # Display job recommendations
                for job in recommendations:
                    company = job.get("Company", "Unknown")
                    job_link = job.get("Job Link", "#")
                    st.write(f"🏢 **Company:** {company}")
                    st.markdown(f"🔗 [Apply Here]({job_link})")
            else:
                st.write("No job recommendations found. Try modifying your search criteria.")
    
    elif dashboard_option == "My Saved Jobs":
        st.header("My Saved Jobs")
        user_email = st.text_input("Enter your email to retrieve saved jobs")
        if st.button("Fetch My Saved Jobs"):
            saved_jobs = get_saved_jobs(user_email)
            if saved_jobs:
                st.subheader("Your Saved Jobs")
                for job_title, company, job_link in saved_jobs:
                    st.write(f"🏢 **Company:** {company} | **Job Title:** {job_title}")
                    st.markdown(f"🔗 [Apply Here]({job_link})")
            else:
                st.write("No saved jobs found for this email.")

    elif dashboard_option == "Market Trends":
        st.header("📊 Market Trends")

        # Fetch trends from the database
        trends = fetch_market_trends()

        if trends:
            for trend_text, skill_link in trends:
                st.subheader(trend_text)
                st.markdown(f"🔗 [Learn More]({skill_link})", unsafe_allow_html=True)
        else:
            st.write("No market trends available yet.")

# Create table before running the app
create_table()


# ------------------- ADMIN DASHBOARD -------------------

def admin_page():
    st.header("Admin Dashboard - Market Trends Management")
    st.write("Enter market trend details with a link to learn the skill.")

    trend_text = st.text_area("Enter Market Trend Details")
    skill_link = st.text_input("Skill Learning Link (e.g., Udemy, Coursera)")

    if st.button("Submit Trend"):
        if trend_text and skill_link:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO market_trends (trend_text, skill_link) VALUES (%s, %s)", (trend_text, skill_link))
                conn.commit()
                cur.close()
                conn.close()
                st.success("Market trend submitted successfully!")
            else:
                st.error("Database connection failed.")
        else:
            st.error("Please enter both trend details and a skill link.")

# ------------------- MAIN APP LOGIC -------------------

st.title("🔍 Job Recommendation System")

# Sidebar navigation
if st.session_state["logged_in"]:
    if st.session_state["role"] == "admin":
        pages = {"Home": home_page, "Admin": admin_page}
    else:
        pages = {"Home": home_page, "Dashboard": dashboard_page}
else:
    pages = {"Home": home_page}

# Display the selected page
page = st.sidebar.radio("Navigation", list(pages.keys()))
pages[page]()
