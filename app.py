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

    with st.spinner(f"Scouting for verified {role} roles..."):
        # UPDATED PROMPT: Focused on actual board URLs and strictly local/remote mix
        prompt = (
            f"Today is {today_date}. Act as a senior recruiter. "
            f"Search for 15-20 ACTIVE job listings for '{role}' in {location}. "
            f"Focus: SF Bay Area (Hayward, Oakland, SF) and Remote. "
            f"Requirements: {keywords}. Salary floor: ${salary:,}+. "
            "\n--- SEARCH PROTOCOL ---\n"
            "1. ONLY return real job postings from job boards (Indeed, LinkedIn, BuiltIn) or company career sites. "
            "2. ABSOLUTELY NO blog posts, 'Top 10' articles, or career advice pages. "
            "3. If you see a job but no deep-link, use the Google Search result URL for that listing. "
            "4. NO PLACEHOLDERS: Do not use 'a1b2c3d4' or other fake IDs. "
            "\nOutput ONLY a JSON list. Keys: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.6 
                }
            )
            
            raw_text = response.text
            
            # IMPROVED EXTRACTION: Find the content between the FIRST [ and the LAST ]
            match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            
            if match:
                json_str = match.group(0).strip()
                
                # Check for empty or malformed results before parsing
                if len(json_str) > 2:
                    job_list = json.loads(json_str)
                    leads = pd.DataFrame(job_list)
                    leads.columns = [c.lower() for c in leads.columns]

                    # Post-Processing: Strip known blog/article noise
                    noise = ['/blog/', '/resources/', '/wu-news/', '/advice/', 'top-10']
                    if 'link' in leads.columns:
                        leads = leads[~leads['link'].str.contains('|'.join(noise), case=False, na=False)]
                        # Drop fake ID hallucinations
                        leads = leads[~leads['link'].str.contains('a1b2c3d4|98765|12345', na=False)]

                    st.success(f"Verified {len(leads)} potential leads for {today_date}!")
                    
                    st.data_editor(
                        leads,
                        column_config={
                            "link": st.column_config.LinkColumn(
                                "Application Link",
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
                    st.warning("The scout returned an empty list. Try reducing the number of keywords.")
            else:
                st.error("Could not isolate job data from the response.")
                with st.expander("Debug: Raw Response"):
                    st.code(raw_text)
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")