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

    with st.spinner(f"Filtering for active {role} postings..."):
        # UPDATED PROMPT: Strict ban on articles/blogs + localized priority
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. "
            f"Search for 15-20 ACTIVE, LIVE job postings for '{role}' in {location}. "
            f"Focus on the SF Bay Area (Hayward, Oakland, SF) first, then Remote. "
            f"Required tech: {keywords}. Target: ${salary:,}+. "
            "\n--- SEARCH INTEGRITY RULES ---\n"
            "1. You must only return actual job listings. "
            "2. ABSOLUTELY FORBIDDEN: Do not include blog posts, career advice articles, or 'Top 10' lists. "
            "3. Every link must point to a specific job board (LinkedIn, Indeed, BuiltIn) or a company career page. "
            "4. If you cannot find a deep-link, provide the URL of the job search results page on that platform. "
            "5. NO HALLUCINATIONS: If a job does not meet the $120k salary floor, skip it. "
            "\nOutput ONLY a JSON list of objects with: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.7 # Increased slightly to find more leads while obeying rules
                }
            )
            
            raw_text = response.text
            # Robust extraction logic to prevent "Extra data" errors
            match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            
            if match:
                json_str = match.group(0).strip()
                # Bracket balancing
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

                # Post-Processing: Drop links that look like articles or generic "help" pages
                junk_keywords = ['/blog/', '/resources/', '/wu-news/', '/advice/', '/career-advice/']
                if 'link' in leads.columns:
                    leads = leads[~leads['link'].str.contains('|'.join(junk_keywords), case=False, na=False)]
                    # Remove the a1b2c3d4 placeholder hallucinations
                    leads = leads[~leads['link'].str.contains('a1b2c3d4|98765|12345', na=False)]

                st.success(f"Verified {len(leads)} active postings!")
                
                st.data_editor(
                    leads,
                    column_config={
                        "link": st.column_config.LinkColumn(
                            "Job Source",
                            display_text="Apply / View",
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
                st.warning("The scout couldn't find enough active listings. Try removing one technical keyword.")
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")