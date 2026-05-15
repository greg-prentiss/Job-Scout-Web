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
    salary = st.number_input("Min Salary", value=120000, step=5000)
    keywords = st.text_area("Keywords", "Meraki, Jamf, PowerShell, Google Workspace")
    
    run_button = st.button("Start Scouting")

if run_button:
    today_date = datetime.date.today().strftime("%B %d, %Y")

    with st.spinner(f"Scouting {industry} for verified technical roles..."):
        # UPDATED PROMPT: Added specific instruction for Education/Admin distinction
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter in {industry}. "
            f"Find 15-20 active job listings for '{role}' in {location}. "
            f"Requirements: {keywords}. Salary floor: ${salary:,}+. "
            "\n--- EDUCATION SECTOR PROTOCOL ---\n"
            "1. FOCUS: Find 'Information Technology' roles. Skip Principal or School Administrator roles. "
            "2. SOURCE: Prioritize EdJoin, school district portals (SFUSD, OUSD, etc.), and Charter networks. "
            "3. FALLBACK: If a deep-link is missing, provide the URL of the job search results page. "
            "4. NO HALLUCINATIONS: Do not guess URLs. Do not create fake IDs. "
            "\nOutput ONLY a JSON list of objects with: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.4 # Kept low for high data integrity
                }
            )
            
            if response and response.text:
                raw_text = response.text
                
                # SURGICAL REPAIR: Find the first [ and the last ]
                start = raw_text.find("[")
                end = raw_text.rfind("]") + 1
                
                if start != -1 and end > start:
                    json_str = raw_text[start:end].strip()
                    
                    # Sanitize common JSON-breaking characters (like unescaped dollar signs)
                    json_str = json_str.replace(r'\$', '$').replace('$', r'\$') # Standardize for parser
                    
                    try:
                        job_list = json.loads(json_str)
                        leads = pd.DataFrame(job_list)
                        leads.columns = [c.lower() for c in leads.columns]

                        # Post-Processing: Strip known article noise and fake IDs
                        noise = ['/blog/', '/resources/', '/wu-news/', '/advice/', 'a1b2c3d4']
                        if 'link' in leads.columns:
                            leads = leads[~leads['link'].str.contains('|'.join(noise), case=False, na=False)]

                        st.success(f"Verified {len(leads)} technical leads for {today_date}!")
                        
                        st.data_editor(
                            leads,
                            column_config={
                                "link": st.column_config.LinkColumn(
                                    "View Posting",
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
                    except json.JSONDecodeError:
                        st.error("The AI returned a malformed list. Attempting to show raw data...")
                        st.write(raw_text)
                else:
                    st.warning("No formatted list was detected. The AI might have returned a conversational response.")
                    with st.expander("Review Raw AI Output"):
                        st.write(raw_text)
            else:
                st.error("Empty response from the scout. Please try again.")
                
        except Exception as e:
            st.error(f"Scouting Error: {e}")