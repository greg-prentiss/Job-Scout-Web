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

# 2. Logic Execution
if run_button:
    today_date = datetime.date.today().strftime("%B %d, %Y")

    with st.spinner(f"Scouting the live web for a high volume of {role} roles..."):
        # UPDATED PROMPT: "Fuzzy" volume boost + "No-Guess" link rule
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. "
            f"Search the web for AT LEAST 15 active job listings similar to '{role}' in {location}. "
            f"Treat these keywords as preferred, not mandatory: {keywords}. "
            f"Target a salary near ${salary:,}+, but include strong technical matches even if salary isn't listed. "
            "CRITICAL LINK RULE: Use ONLY verified URLs found in search results (e.g., Greenhouse, Lever, LinkedIn, Indeed, ZipRecruiter). "
            "ABSOLUTELY FORBIDDEN: Do not guess or construct a URL (e.g., do not guess 'company.com/careers/job-title'). "
            "If you cannot find a direct verified URL for a listing, skip that listing and find another. "
            "Return a JSON list with: title, company, salary, location, source, link. "
            "Provide ONLY the JSON list."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.85 # High enough for variety, low enough for focus
                }
            )
            
            raw_text = response.text
            
            # Straightforward extraction
            start = raw_text.find("[")
            end = raw_text.rfind("]") + 1
            
            if start != -1 and end != 0:
                json_data = raw_text[start:end]
                job_list = json.loads(json_data)
                leads = pd.DataFrame(job_list)

                # Standardize columns to lowercase
                leads.columns = [c.lower() for c in leads.columns]

                st.success(f"Found {len(leads)} potential leads for {today_date}!")
                
                # Interactive Table
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
                st.warning("The scout had trouble finding 100% verified links. Try narrowing the location or adjusting keywords.")
                st.info("Raw response for debugging:")
                st.write(raw_text)
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")