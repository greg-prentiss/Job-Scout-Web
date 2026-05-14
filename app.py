import streamlit as st
import pandas as pd
from google.genai import Client
import json
import datetime

# 1. SECURE API KEY ACCESS
client = Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. BRANDING
st.set_page_config(page_title="Career-Paths", layout="wide")
st.title("📡 Career-Paths")

# UI Elements
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

if run_button:
    today_date = datetime.date.today().strftime("%B %d, %Y")

    with st.spinner(f"Scouting the live web for {role} roles..."):
        # UPDATED PROMPT: Demanding ATS/Root-Source URLs to prevent broken links
        prompt = (
            f"Today is {today_date}. Act as an elite technical headhunter. "
            f"Search the web to find AT LEAST 15 distinct, active job postings for '{role}' or related roles in {location}. "
            f"Keywords: {keywords}. Target salary: ${salary:,}+. "
            "CRITICAL LINK INSTRUCTION: You must find the ACTUAL, human-viewable application URL. "
            "Aggregator links (ZipRecruiter, Glassdoor) are often broken or truncated. "
            "Whenever possible, trace the job back to the root source link (e.g., Greenhouse.io, Lever.co, Workday, or direct company/VC boards like jobs.generalcatalyst.com). "
            "For example, if you find an 'IT Site Lead at Ramp' role, do not give me a broken ZipRecruiter link; find the real, working root URL. "
            "NEVER guess, truncate, or hallucinate the URL. Extract the exact working URL directly from the search tool. "
            "Return the results as a JSON list with exactly these keys: title, company, salary, location, source, link. "
            "Provide ONLY the JSON list."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.95 
                }
            )
            
            raw_text = response.text
            start = raw_text.find("[")
            end = raw_text.rfind("]") + 1
            
            if start != -1 and end != 0:
                json_data = raw_text[start:end]
                job_list = json.loads(json_data)
                leads = pd.DataFrame(job_list)

                # Standardize column names to lowercase
                leads.columns = [c.lower() for c in leads.columns]

                st.success(f"Scout complete! Found {len(leads)} leads for {today_date}.")
                
                # Render Table
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
                st.warning("The scout couldn't format the results properly. Try running the search again.")
                st.info("Raw response for debugging:")
                st.write(raw_text)
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")