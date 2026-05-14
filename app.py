import streamlit as st
import pandas as pd
from google.genai import Client
import json

# 1. SECURE API KEY ACCESS
# This looks for the key in your .streamlit/secrets.toml (locally) 
# or the Streamlit Cloud Secrets dashboard (once deployed).
client = Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. BRANDING YOUR APP
# This replaces the generic "Streamlit" tab name with your new catchy name.
st.set_page_config(page_title="Career-Paths", layout="wide")
st.title("📡 Career-Paths")

# 1. UI Elements
st.title("🔎 AI Job Scout")
st.markdown("Find your next role using Gemini-powered web scouting.")

with st.sidebar:
    st.header("Search Parameters")
    industry = st.selectbox("Industry", ["I.T. & Systems", "Education", "Healthcare", "General"])
    role = st.text_input("Job Title", "IT Systems Lead")
    location = st.text_input("Location", "San Francisco Bay Area or Remote")
    salary = st.number_input("Min Salary", value=120000, step=5000)
    keywords = st.text_area("Keywords", "Meraki, Jamf, PowerShell, Google Workspace")
    
    run_button = st.button("Start Scouting")

# 2. Logic Execution
if run_button:
    # Requires a local .streamlit/secrets.toml file or Streamlit Cloud Secrets
    client = Client(api_key=st.secrets["GEMINI_API_KEY"])

    with st.spinner(f"Scouting the web..."):
        prompt = (
            f"Act as a recruiter in {industry}. Find 10 open {role} roles in {location}. "
            f"Requirements: {keywords}. Salary: {salary}+. "
            "Return a JSON list with: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            text_data = response.text
            
            # Find the JSON list bounds
            start_index = text_data.find("[")
            end_index = text_data.rfind("]") + 1
            
            if start_index != -1 and end_index != 0:
                clean_json = text_data[start_index:end_index]
                
                # Parse the string into a Python list
                job_list = json.loads(clean_json)
                
                # Turn that list into a DataFrame
                leads = pd.DataFrame(job_list)
                
                st.success(f"Found {len(leads)} potential leads!")
                
                # UPDATED: Replaced deprecated use_container_width with width='stretch'
                st.dataframe(leads, width='stretch')
                
                csv = leads.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, "jobs.csv", "text/csv")
            else:
                st.error("Format mismatch. Try refining your keywords.")
                st.code(text_data)
            
        except Exception as e:
            st.error(f"Error: {e}")