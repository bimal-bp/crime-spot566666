import streamlit as st
import psycopg2
import bcrypt
import ast  # To convert database array strings into Python lists
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
            dbname="neondb",
            user="neondb_owner",
            password="npg_hnmkC3SAi7Lc",
            host="ep-steep-dawn-a87fu2ow-pooler.eastus2.azure.neon.tech",
            port="5432",
            sslmode="require"
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

# ------------------- JOB RECOMMENDATION FUNCTION -------------------

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

# ------------------- SESSION STATE INITIALIZATION -------------------

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "show_trend_form" not in st.session_state:
    st.session_state["show_trend_form"] = False

st.title("🔍 Job Recommendation System")

# ------------------- SIDEBAR NAVIGATION -------------------

# When not logged in, only the Home page is available.
if not st.session_state["logged_in"]:
    nav_pages = ["Home"]
else:
    # Once logged in, show Dashboard; if admin, also show Admin page.
    nav_pages = ["Dashboard"]
    if st.session_state["role"] == "admin":
        nav_pages.append("Admin")
        
page = st.sidebar.radio("Go to", nav_pages)

# ------------------- HOME PAGE -------------------
if page == "Home" and not st.session_state["logged_in"]:
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
                try:
                    st.experimental_rerun()  # Re-run to update the UI
                except AttributeError:
                    st.stop()
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
                try:
                    st.experimental_rerun()  # Force the app to re-run and update the navigation
                except AttributeError:
                    st.stop()
            else:
                st.error("Invalid credentials.")

    # ---------- Admin Access ----------
    with col2:
        st.header("Admin Access")
        admin_login_email = st.text_input("Admin Email", key="admin_login_email")
        admin_login_password = st.text_input("Admin Password", type="password", key="admin_login_password")
        if st.button("Admin Login", key="admin_login_button"):
            role = authenticate_user(admin_login_email, admin_login_password)
            if role and role == "admin":
                st.session_state["logged_in"] = True
                st.session_state["role"] = role
                st.success("Admin login successful!")
                try:
                    st.experimental_rerun()  # Re-run after admin login
                except AttributeError:
                    st.stop()
            else:
                st.error("Invalid admin credentials.")

# ------------------- USER DASHBOARD -------------------
elif page == "Dashboard" and st.session_state["logged_in"] and st.session_state["role"] != "admin":
    st.sidebar.title("Dashboard Navigation")
    dashboard_option = st.sidebar.radio("Select Option", ["Job Recommendations", "Market Trends"])
    
    if dashboard_option == "Job Recommendations":
        st.header("Job Recommendation Dashboard")
        job_title = st.text_input("Job Title", "DevOps Engineer")
        skills_input = st.text_area("Skills (comma separated)", "Docker, Kubernetes")
        skills = [skill.strip() for skill in skills_input.split(",") if skill.strip()]
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
                    st.write(f"🏢 **Company:** {job['Company']}")
                    st.markdown(f"🔗 [Apply Here]({job['Job Link']})")
            else:
                st.write("No job recommendations found. Try modifying your search criteria.")
                
    elif dashboard_option == "Market Trends":
        st.header("Market Trends")
        st.write("📊 Market Trends coming soon!")
        # You can add additional market trend visualizations or data here.

# ------------------- ADMIN DASHBOARD -------------------
elif page == "Admin" and st.session_state["logged_in"] and st.session_state["role"] == "admin":
    st.header("Admin Dashboard - Market Trends Management")
    st.write("Here you can write and submit market trend details.")

    if st.button("Write Market Trend"):
        st.session_state["show_trend_form"] = True

    if st.session_state["show_trend_form"]:
        trend_text = st.text_area("Enter Market Trend Details")
        if st.button("Submit Trend"):
            # TODO: Add your database storage logic for market trends here.
            st.success("Market trend submitted successfully!")
            st.session_state["show_trend_form"] = False

else:
    st.write("Please log in to continue.")
