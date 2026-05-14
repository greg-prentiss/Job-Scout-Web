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

    with st.spinner(f"Scouting verified sources for {role} roles..."):
        # PROMPT: Agnostic Source Fallback Logic
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. "
            f"Find 15-20 active job listings for '{role}' in {location}. "
            f"Prioritize matches for: {keywords}. Target: ${salary:,}+. "
            "\n--- THE AGNOSTIC FALLBACK PROTOCOL ---\n"
            "1. You must provide a working URL for every job found. "
            "2. If you find a direct application deep-link, use it. "
            "3. FALLBACK: If a direct link is not obvious, provide the URL of the Google Search result "
            "or the job board aggregator page (Indeed, LinkedIn, ZipRecruiter) where you saw the listing. "
            "4. NEVER guess or synthesize a URL. No placeholder IDs. "
            "\nOutput ONLY a JSON list of objects with: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.5 
                }
            )
            
            # ARMOR: Validate that we actually got a text response
            if response and response.text:
                raw_text = response.text
                
                # Surgical extraction using regex
                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                
                if match:
                    json_str = match.group(0).strip()
                    
                    # Bracket-level balancing to ensure a clean list
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

                    # Post-Processing: Strip known hallucination patterns
                    placeholders = ['a1b2c3d4', '98765', '12345', 'placeholder']
                    if 'link' in leads.columns:
                        leads = leads[~leads['link'].str.contains('|'.join(placeholders), case=False, na=False)]

                    st.success(f"Verified {len(leads)} active postings!")
                    
                    st.data_editor(
                        leads,
                        column_config={
                            "link": st.column_config.LinkColumn(
                                "Source Link",
                                display_text="View on Source",
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
                    st.warning("The scout found data but it wasn't formatted correctly. Try clicking 'Start Scouting' again.")
            else:
                st.error("The AI search returned an empty result. This can happen if the search tool is throttled or a safety filter is triggered.")
                
        except Exception as e:
            st.error(f"Scouting Error: {e}")