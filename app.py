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

def get_db_connection():
    try:
        return psycopg2.connect(
            "postgresql://neondb_owner:npg_7JQelPFsVf2K@ep-purple-surf-a5w6dl4v-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
        )
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# ------------------- USER AUTHENTICATION -------------------

def register_user(email, password):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            st.error("User already exists. Please log in.")
            return False
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT INTO users (email, password, role) VALUES (%s, %s, %s)", (email, hashed_password, "user"))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error during registration: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def authenticate_user(email, password):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT password, role FROM users WHERE email = %s", (email,))
        result = cur.fetchone()
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
            return result[1]
        return None
    except Exception as e:
        st.error(f"Error during authentication: {e}")
        return None
    finally:
        cur.close()
        conn.close()

# ------------------- JOB RECOMMENDATION FUNCTION -------------------

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
            if f"location_{location.lower()}" in user_location_df.columns:
                user_location_df[f"location_{location.lower()}"] = 1
        user_location_vector = sp.csr_matrix(user_location_df.values)

    user_vector = sp.hstack([user_text_vector, user_numeric_vector, user_location_vector])
    similarity_scores = cosine_similarity(user_vector, final_features)
    ranked_indices = similarity_scores.argsort()[0][::-1][:top_n]

    return [{"Company": df.iloc[i]["Company"], "Job Link": df.iloc[i]["job_link"]} for i in ranked_indices]

# ------------------- SESSION STATE INITIALIZATION -------------------

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "Home"

# ------------------- HOME PAGE -------------------

def home_page():
    st.title("🔍 Job Recommendation System")
    st.subheader("User Authentication")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = authenticate_user(email, password)
        if role:
            st.session_state["logged_in"] = True
            st.session_state["role"] = role
            st.success("Login successful!")
        else:
            st.error("Invalid credentials.")

# ------------------- DASHBOARD -------------------

def dashboard_page():
    st.title("📊 Job Recommendations")
    job_title = st.text_input("Job Title")
    skills = st.text_area("Skills (comma separated)").split(",")
    section = st.text_input("Job Section")
    experience = st.number_input("Experience (years)", min_value=0)
    salary = st.number_input("Expected Salary (LPA)", min_value=0)
    locations = st.multiselect("Preferred Locations", ["Pune", "Bangalore", "Hyderabad", "Mumbai"])

    if st.button("Get Recommendations"):
        recommendations = recommend_jobs(job_title, skills, section, experience, salary, locations)
        for job in recommendations:
            st.write(f"🏢 **{job['Company']}**")
            st.markdown(f"🔗 [Apply Here]({job['Job Link']})")

# ------------------- ADMIN PAGE -------------------

def admin_page():
    st.title("🛠 Admin Dashboard - Market Trends Management")
    trend_text = st.text_area("Enter Market Trend Details")
    if st.button("Submit Trend"):
        conn = get_db_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("INSERT INTO market_trends (trend_text) VALUES (%s)", (trend_text,))
                conn.commit()
                st.success("Market trend submitted successfully!")
            except Exception as e:
                st.error(f"Error storing market trend: {e}")
            finally:
                cur.close()
                conn.close()

# ------------------- NAVIGATION -------------------

def main():
    if st.session_state["logged_in"]:
        if st.session_state["role"] == "admin":
            admin_page()
        else:
            dashboard_page()
    else:
        home_page()

if __name__ == "__main__":
    main()
