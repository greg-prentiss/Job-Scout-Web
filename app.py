import streamlit as st
import pandas as pd
from google.genai import Client
import json
import datetime

# 1. SECURE API KEY ACCESS
client = Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. BRANDING YOUR APP
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
    today_date = datetime.date.today().strftime("%B %d, %Y")

    with st.spinner(f"Scouting the live web for {role} roles..."):
        # UPDATED PROMPT: Demanding direct URLs and allowing "Prioritization" over "Hard Requirements"
        prompt = (
            f"Today is {today_date}. Act as a recruiter in {industry}. "
            f"Search the web to find 10 CURRENTLY OPEN and active {role} roles in {location}. "
            f"Prioritize these keywords: {keywords}. Salary target: {salary}+. "
            "CRITICAL: Do not return 'google.com/ground-api-redirect' URLs. "
            "Return only the direct destination URL (e.g., Greenhouse, Lever, LinkedIn, Indeed). "
            "Return a JSON list with exactly these keys: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.7 
                }
            )
            
            text_data = response.text
            start_index = text_data.find("[")
            end_index = text_data.rfind("]") + 1
            
            if start_index != -1 and end_index != 0:
                clean_json = text_data[start_index:end_index]
                job_list = json.loads(clean_json)
                leads = pd.DataFrame(job_list)

                # Ensure column names are lowercase to match the config below
                leads.columns = [c.lower() for c in leads.columns]

                st.success(f"Found {len(leads)} potential leads for {today_date}!")
                
                # UPDATED UI: Clean clickable buttons
                st.data_editor(
                    leads,
                    column_config={
                        "link": st.column_config.LinkColumn(
                            "Job Link",
                            display_text="Open Posting",
                            width="medium"
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                    disabled=leads.columns # Makes it read-only
                )
                
                csv = leads.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, "jobs.csv", "text/csv")
            else:
                st.error("No valid leads found with current filters. Try removing a keyword or lowering the salary floor.")
            
        except Exception as e:
            st.error(f"Error during scouting: {e}")