import streamlit as st
import pandas as pd
import joblib
import scipy.sparse as sp
from sklearn.metrics.pairwise import cosine_similarity

# ✅ Load Saved Models & Data
vectorizer = joblib.load("vectorizer.pkl")
scaler = joblib.load("scaler.pkl")
df = joblib.load("df.pkl")  # Load saved DataFrame
final_features = joblib.load("features.pkl")  # Load precomputed features

def recommend_jobs(job_title, skills, section, experience, salary, locations, top_n=5):
    """Returns top N job recommendations with Company Name and Job Link."""
    
    # Combine inputs into a job description
    job_desc = f"{job_title} in {section} with skills: {', '.join(skills)}"
    user_text_vector = vectorizer.transform([job_desc])

    # Normalize experience & salary
    user_numeric_vector = pd.DataFrame([[experience, salary]], columns=["Experience", "Salary"])
    user_numeric_vector = scaler.transform(user_numeric_vector)
    user_numeric_vector = sp.csr_matrix(user_numeric_vector)

    # Encode locations if present in df
    location_columns = [col for col in df.columns if col.startswith("location_")]
    user_location_vector = sp.csr_matrix((1, len(location_columns)))  # Default empty matrix

    if locations:
        user_location_df = pd.DataFrame(0, index=[0], columns=location_columns)
        for location in locations:
            location_column_name = f"location_{location.lower()}"
            if location_column_name in user_location_df.columns:
                user_location_df[location_column_name] = 1
        user_location_vector = sp.csr_matrix(user_location_df.values)

    # Concatenate all user input features
    user_vector = sp.hstack([user_text_vector, user_numeric_vector, user_location_vector])

    # Compute similarity scores
    similarity_scores = cosine_similarity(user_vector, final_features)
    ranked_indices = similarity_scores.argsort()[0][::-1][:top_n]

    # Retrieve recommended jobs
    recommended_jobs = [
        {
            "Company": df.iloc[i]["Company"],
            "Job Link": df.iloc[i]["job_link"]
        }
        for i in ranked_indices
    ]
    return recommended_jobs

# ✅ Streamlit UI
st.title("🔍 Job Recommendation System")
st.write("Enter your job preferences to get recommendations!")

# Input fields
job_title = st.text_input("Job Title", "DevOps Engineer")
skills = st.text_area("Skills", "Docker, Kubernetes").split(", ")
section = st.text_input("Job Section", "IT")
experience = st.number_input("Years of Experience", min_value=0, max_value=50, value=5)
salary = st.number_input("Expected Salary (in LPA)", min_value=0, max_value=100, value=15)

# Location selection
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
