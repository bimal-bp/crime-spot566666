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

# Job Recommendation Function
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
                st.write(f"🏢 *Company:* {job['Company']}")
                st.markdown(f"🔗 [Apply Here]({job['Job Link']})")
        else:
            st.write("No job recommendations found. Try modifying your search criteria.")

elif page == "Admin" and st.session_state.get("role") == "admin":
    st.write("Admin Dashboard - Manage Users and Jobs")

elif page == "Market Trends":
    st.write("📊 Market Trends coming soon!")
