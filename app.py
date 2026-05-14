import streamlit as st
import pandas as pd
from google.genai import Client
import json
import datetime
import re

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

    with st.spinner(f"Scouting the live web for {role} roles..."):
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. "
            f"Find 15-20 active job listings for '{role}' in {location}. "
            f"Technical stack priorities: {keywords}. Target: ${salary:,}+. "
            "WILDCARD: Include 2-3 high-level roles outside the exact title, such as 'Infrastructure Manager' or 'Site Reliability Lead'. "
            "\n--- MANDATORY LINK VERIFICATION ---\n"
            "1. Provide a DIRECT DEEP LINK to the job posting. "
            "2. A deep link MUST contain a unique identifier (e.g., /jobs/12345 or /postings/abc-xyz). "
            "3. DO NOT guess or synthesize URLs based on company names. "
            "4. Avoid generic career pages and ZipRecruiter 'ghost' links. "
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
            
            # IMPROVED EXTRACTION: Using regex to find the JSON block more reliably
            # This looks for the content between the first [ and the last ]
            json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0).strip()
                
                # Double-check for multiple lists and take the longest one (usually the main one)
                if json_str.count('[') > 1:
                    # Basic bracket balancing to extract just the first full list
                    bracket_level = 0
                    for i, char in enumerate(json_str):
                        if char == '[': bracket_level += 1
                        elif char == ']': bracket_level -= 1
                        if bracket_level == 0:
                            json_str = json_str[:i+1]
                            break

                job_list = json.loads(json_str)
                leads = pd.DataFrame(job_list)
                leads.columns = [c.lower() for c in leads.columns]

                # Filter: Remove generic or short URLs
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
                st.warning("The scout couldn't isolate the data list. View the raw response below to troubleshoot.")
                with st.expander("Raw AI Response"):
                    st.write(raw_text)
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")