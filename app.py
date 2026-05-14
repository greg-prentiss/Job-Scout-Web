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

    with st.spinner(f"Scouting all available sources for {role} roles..."):
        # UPDATED PROMPT: Brand-Agnostic with Search-Result Fallback
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. "
            f"Find 15-20 active job listings for '{role}' in {location}. "
            f"Priorities: {keywords}. Target: ${salary:,}+. "
            "\n--- VERIFICATION PROTOCOL ---\n"
            "1. Your primary goal is to provide a working URL for every job found. "
            "2. If you find a direct application deep-link, use it. "
            "3. FALLBACK RULE: If you cannot find a direct deep-link, provide the URL of the Google Search result "
            "or the job board landing page (LinkedIn, Indeed, etc.) where you saw the listing. "
            "4. ABSOLUTELY FORBIDDEN: Never guess, synthesize, or hallucinate a URL. Do not create IDs like 'a1b2c3d4'. "
            "5. If a link is not explicitly visible in your search results, provide the search result's source URL. "
            "\n--- OUTPUT FORMAT ---\n"
            "Return ONLY a JSON list. No markdown. "
            "Keys: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.4 # Lowered to further reduce "creative" guessing
                }
            )
            
            raw_text = response.text
            json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0).strip()
                
                # Robust bracket-leveling to capture exactly one list
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

                # CLEANUP: Remove obvious placeholders if they still slip through
                placeholders = ['a1b2c3d4', '98765', '12345']
                if 'link' in leads.columns:
                    leads = leads[~leads['link'].str.contains('|'.join(placeholders), case=False, na=False)]

                st.success(f"Scout complete! Found {len(leads)} potential leads.")
                
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
                st.warning("The scout couldn't format the data. Please try again.")
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")
            with st.expander("Debug: Raw Response"):
                st.code(raw_text)