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
    role = st.text_input("Job Title", "IT Admin")
    location = st.text_input("Location", "Hayward, Oakland, San Francisco or Remote")
    salary = st.number_input("Min Salary", value=90000, step=5000)
    keywords = st.text_area("Keywords", "Meraki, Jamf, PowerShell, Google Workspace, Chromebook, LMS, PowerSchool")
    
    run_button = st.button("Start Scouting")

if run_button:
    today_date = datetime.date.today().strftime("%B %d, %Y")

    with st.spinner(f"Broadening search for {role} roles in the greater Bay Area..."):
        # UPDATED PROMPT: "OR" Logic + Geographic Radius + Verification
        prompt = (
            f"Today is {today_date}. Act as a senior recruiter specializing in {industry}. "
            f"Search for 15-20 ACTIVE technical job listings for '{role}'. "
            f"GEOGRAPHY: Focus on a 15-mile radius around {location}. "
            "Specifically include nearby cities like San Leandro, Fremont, Berkeley, and Alameda. "
            f"KEYWORDS: Treat the following as a non-mandatory wishlist. Include jobs that match ANY of these: {keywords}. "
            f"SALARY: Focus on roles targetting ${salary:,}+. "
            "\n--- SEARCH INTEGRITY ---\n"
            "1. VERIFY: The job title must be technical (e.g., IT, Systems, Network, Admin). Skip Science/Special Ed teachers. "
            "2. NO GUESSING: Provide only real links found in the snippets. "
            "3. NO BLOGS: Skip 'Top 10' or 'Career Advice' articles. "
            "\nOutput ONLY a JSON list of objects with: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.8 # Higher temp for more variety/volume
                }
            )
            
            if response and response.text:
                raw_text = response.text
                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                
                if match:
                    json_str = match.group(0).strip()
                    try:
                        job_list = json.loads(json_str)
                        leads = pd.DataFrame(job_list)
                        leads.columns = [c.lower() for c in leads.columns]

                        # Post-Processing: Filtering the "noise"
                        if 'link' in leads.columns:
                            noise = ['/blog/', '/resources/', '/advice/', 'top-10', '/news/']
                            leads = leads[~leads['link'].str.contains('|'.join(noise), case=False, na=False)]
                            # Filter out those sequential EdJoin hallucinations
                            leads = leads[~leads['link'].str.contains('a1b2c3d4|98765|12345', na=False)]

                        if not leads.empty:
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
                            st.warning("No verified technical leads found. Try removing a keyword.")
                    except Exception as e:
                        st.error(f"Formatting error: {e}")
                else:
                    st.warning("No data list isolated. The search parameters may be too restrictive.")
            else:
                st.error("Empty response from the AI. Try running the search again.")
                
        except Exception as e:
            st.error(f"Scouting Error: {e}")