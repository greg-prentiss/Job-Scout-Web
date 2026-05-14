import streamlit as st
import pandas as pd
from google.genai import Client
import json
import datetime

# 1. SECURE API KEY ACCESS
# This looks for the key in your .streamlit/secrets.toml (locally) 
# or the Streamlit Cloud Secrets dashboard (once deployed).
client = Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. BRANDING YOUR APP
# Replaces the generic "Streamlit" tab name with your catchy new name.
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
    # Use today's date to force the AI to look for current, active listings
    today_date = datetime.date.today().strftime("%B %d, %Y")

    with st.spinner(f"Scouting the live web for {role} roles..."):
        # Updated prompt with the date and a directive to find "active" roles
        prompt = (
            f"Today is {today_date}. Act as a recruiter in {industry}. "
            f"Search the web to find 10 CURRENTLY OPEN and active {role} roles in {location}. "
            f"Requirements: {keywords}. Salary expectation: {salary}+. "
            "Return a JSON list with exactly these keys: title, company, salary, location, source, link. "
            "Ensure the links are direct to the job posting where possible."
        )

        try:
            # Tool-enabled call: This activates the Google Search engine
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}], # Enables live scouting
                    'temperature': 0.7              # Encourages variety in results
                }
            )
            
            text_data = response.text
            
            # Find the JSON list bounds in the AI response
            start_index = text_data.find("[")
            end_index = text_data.rfind("]") + 1
            
            if start_index != -1 and end_index != 0:
                clean_json = text_data[start_index:end_index]
                
                # Parse the string into a Python list
                job_list = json.loads(clean_json)
                
                # Convert the list into a Pandas DataFrame
                leads = pd.DataFrame(job_list)
                
                st.success(f"Found {len(leads)} potential leads for {today_date}!")
                
                # Display the data
                st.dataframe(leads, width='stretch')
                
                # Provide a CSV download option
                csv = leads.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, "jobs.csv", "text/csv")
            else:
                st.error("The scout returned data in an unexpected format. Try refining your keywords.")
                st.code(text_data) # Shows raw data for debugging
            
        except Exception as e:
            st.error(f"Error during scouting: {e}")