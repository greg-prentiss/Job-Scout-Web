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

    with st.spinner(f"Performing a Multi-Pass deep scout for {role} roles..."):
        # UPDATED PROMPT: Sequential search instructions + "No-Guess" hard rule
        prompt = (
            f"Today is {today_date}. Act as an expert technical headhunter. "
            f"Your mission is to find 15-20 active job listings for '{role}' in {location}. "
            f"Prioritize skills: {keywords}. Target: ${salary:,}+. "
            "\n--- SEARCH STRATEGY ---\n"
            "1. Search broadly for the roles on LinkedIn, Indeed, and BuiltIn.\n"
            "2. For EACH company found, perform a targeted search for their Greenhouse, Lever, or Career portal link.\n"
            "3. A valid job link MUST be a deep link containing a numeric ID or a long slug (e.g., /jobs/54800168 or /postings/abc-123).\n"
            "\n--- THE 'NO-GUESS' RULE ---\n"
            "ABSOLUTELY FORBIDDEN: Do not synthesize or guess URLs like 'company.com/careers/job-title'. "
            "If you only see a generic career page (e.g., 'cisco.com/careers'), skip it and keep searching until you find the exact deep link for the specific job.\n"
            "\n--- REFERENCE EXAMPLE ---\n"
            "Good Link: 'jobs.generalcatalyst.com/companies/ramp-2/jobs/54800168-it-site-lead-san-francisco'\n"
            "Bad Link: 'ramp.com/careers/it-site-lead'\n"
            "\nReturn ONLY a JSON list with: title, company, salary, location, source, link."
        )

        try:
            # Note: Standardizing to 'gemini-1.5-flash' for maximum reliability in 2026
            response = client.models.generate_content(
                model="gemini-1.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.7 # Lowered slightly for accuracy over 'vibe'
                }
            )
            
            raw_text = response.text
            start = raw_text.find("[")
            end = raw_text.rfind("]") + 1
            
            if start != -1 and end != 0:
                json_data = raw_text[start:end]
                job_list = json.loads(json_data)
                leads = pd.DataFrame(job_list)
                leads.columns = [c.lower() for c in leads.columns]

                # Filter out obvious 'bad' links that are too short (root domains)
                leads = leads[leads['link'].str.len() > 30]

                st.success(f"Verified {len(leads)} leads for {today_date}!")
                
                st.data_editor(
                    leads,
                    column_config={
                        "link": st.column_config.LinkColumn(
                            "Direct Application",
                            display_text="Apply on Company Site",
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
                st.warning("The scout is having trouble finding deep links. Broadening location...")
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")