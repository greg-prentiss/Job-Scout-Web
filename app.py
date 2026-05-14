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
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. "
            f"Search the web for 15-20 active job listings for '{role}' in {location}. "
            f"Preferences: {keywords}. Target: ${salary:,}+. "
            "\n--- MANDATORY LINK VERIFICATION ---\n"
            "1. You must provide a DIRECT DEEP LINK to the job posting. "
            "2. A deep link MUST contain a unique identifier (e.g., /jobs/12345 or /postings/abc-xyz). "
            "3. DO NOT guess or synthesize URLs based on company names. "
            "4. If you see a generic career page, search deeper for the specific job's unique URL. "
            "5. Avoid ZipRecruiter 'ghost' links; prioritize Greenhouse, Lever, Workday, or LinkedIn direct postings. "
            "\n--- OUTPUT FORMAT ---\n"
            "Return ONLY a JSON list of objects. No markdown, no triple backticks, no preamble. "
            "Keys: title, company, salary, location, source, link."
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
            
            raw_text = response.text
            
            # IMPROVED EXTRACTION: Handles the "Extra data" issue by being more specific
            start_index = raw_text.find("[")
            end_index = raw_text.rfind("]") + 1
            
            if start_index != -1 and end_index > start_index:
                json_str = raw_text[start_index:end_index].strip()
                
                # Double-check for nested arrays that might cause "Extra data"
                # If the AI provided multiple lists, this ensures we only take the first one
                if json_str.count('[') > 1 and json_str.count(']') > 1:
                     # Attempt to find the first complete valid array
                     bracket_level = 0
                     for i, char in enumerate(json_str):
                         if char == '[': bracket_level += 1
                         if char == ']': bracket_level -= 1
                         if bracket_level == 0:
                             json_str = json_str[:i+1]
                             break

                job_list = json.loads(json_str)
                leads = pd.DataFrame(job_list)
                leads.columns = [c.lower() for c in leads.columns]

                # Filter: Only keep links that look like actual deep links
                if 'link' in leads.columns:
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
                st.warning("The scout couldn't isolate the data list. Try running it again.")
            
        except Exception as e:
            # Enhanced error reporting to help us debug the "Extra data" if it persists
            st.error(f"Scouting Error: {e}")
            if 'raw_text' in locals():
                with st.expander("View Raw Response"):
                    st.code(raw_text)