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
        prompt = (
            f"Today is {today_date}. Act as an expert career scout in {industry}. "
            f"Search the web for approximately 10 active job openings similar to '{role}' in {location}. "
            f"Focus on roles that value these skills: {keywords}. "
            f"Target a salary of ${salary:,}+. "
            "I need direct links to the job postings (like Greenhouse, Lever, LinkedIn, or Company sites). "
            "Avoid links that are just '[google.com/ground-api-redirect](https://google.com/ground-api-redirect)'. "
            "Return a JSON list with these keys: title, company, salary, location, source, link. "
            "Provide ONLY the JSON list, no other text."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.8 
                }
            )
            
            raw_text = response.text
            
            # THE "STRAIGHTFORWARD" FIX: Find the JSON list without using complex splits
            start = raw_text.find("[")
            end = raw_text.rfind("]") + 1
            
            if start != -1 and end != 0:
                json_data = raw_text[start:end]
                job_list = json.loads(json_data)
                leads = pd.DataFrame(job_list)

                # Standardize column names to lowercase for the UI config
                leads.columns = [c.lower() for c in leads.columns]

                st.success(f"Found {len(leads)} potential leads!")
                
                # Render the table with clickable buttons
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
                    disabled=leads.columns
                )
                
                csv = leads.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, "jobs.csv", "text/csv")
            else:
                st.warning("No clear leads found. Try broadening your keywords.")
                st.info("Debugging Info: No JSON list detected in response.")
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")