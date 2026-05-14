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
    location = st.text_input("Location", "Hayward, Oakland, San Francisco or Remote")
    salary = st.number_input("Min Salary", value=120000, step=5000)
    keywords = st.text_area("Keywords", "Meraki, Jamf, PowerShell, Google Workspace")
    
    run_button = st.button("Start Scouting")

if run_button:
    today_date = datetime.date.today().strftime("%B %d, %Y")

    with st.spinner(f"Running Multi-Pass verification for {role} roles..."):
        # UPDATED PROMPT: 2.5 Flash + Multi-Pass Verification
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. "
            f"Find 15-20 active job listings for '{role}' in {location}. "
            f"Preferences: {keywords}. Target: ${salary:,}+. "
            "\n--- MANDATORY LINK VERIFICATION ---\n"
            "1. You must provide a DIRECT DEEP LINK to the job posting. "
            "2. A deep link MUST contain a unique identifier (e.g., /jobs/12345 or /postings/abc-xyz). "
            "3. DO NOT guess or synthesize URLs based on company names. "
            "4. If you see a generic career page (e.g., 'cisco.com/careers'), search deeper for the specific job's unique URL. "
            "5. Avoid ZipRecruiter 'ghost' links; prioritize Greenhouse, Lever, Workday, or LinkedIn direct postings. "
            "\n--- OUTPUT FORMAT ---\n"
            "Return a JSON list with: title, company, salary, location, source, link. "
            "Provide ONLY the JSON list."
        )

        try:
            # Reverted to the high-performance 2.5 Flash model
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.8
                }
            )
            
            raw_text = response.text
            
            # Robust JSON isolation
            start = raw_text.find("[")
            end = raw_text.rfind("]") + 1
            
            if start != -1 and end != 0:
                json_data = raw_text[start:end]
                job_list = json.loads(json_data)
                leads = pd.DataFrame(job_list)
                leads.columns = [c.lower() for c in leads.columns]

                # Filter: Only keep links that look like actual deep links (>35 chars)
                leads = leads[leads['link'].str.contains('/', na=False)]
                leads = leads[leads['link'].str.len() > 35]

                st.success(f"Verified {len(leads)} deep-link leads!")
                
                st.data_editor(
                    leads,
                    column_config={
                        "link": st.column_config.LinkColumn(
                            "Application Link",
                            display_text="Apply Directly",
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
                st.warning("The scout found listings but couldn't verify the deep links. Try reducing keywords.")
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")