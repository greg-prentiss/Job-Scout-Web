import streamlit as st
import pandas as pd
from google.genai import Client
import json
import datetime
import re

# 1. SECURE API KEY ACCESS
client = Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. BRANDING & UI SETUP
st.set_page_config(page_title="Career-Paths", layout="wide")
st.title("📡 Career-Paths")
st.markdown("Validated for high-precision matching and transparent auditing.")

# SIDEBAR PARAMETERS
with st.sidebar:
    st.header("Search Parameters")
    industry = st.text_input("Industry / Sector", "Education")
    role = st.text_input("Job Title", "IT Admin")
    location = st.text_input("Location / City", "Hayward, CA")
    salary = st.number_input("Min Salary / Pay", value=90000, step=5000)
    keywords = st.text_area("Skills / Keywords (Wishlist)", "Meraki, Jamf, PowerShell, Google Workspace, PowerSchool, Chromebook")
    
    st.divider()
    # THE BOOLEAN FLAG
    deep_scout = st.checkbox("Deep Scout (More leads, higher API cost)", value=False)
    run_button = st.button("Start Scouting")

if run_button:
    today_date = datetime.date.today().strftime("%B %d, %Y")
    
    # PRECISION LOGIC
    temp_setting = 0.4 if not deep_scout else 0.8 
    max_leads = 25 if deep_scout else 15

    with st.spinner(f"Scouting {industry}..."):
        
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. "
            f"Search the web for {max_leads} active job listings for '{role}' in {industry}. "
            f"\n--- GEOGRAPHIC RADIUS ---\n"
            f"Focus on {location} and a 20-mile commuter radius (e.g., San Leandro, Fremont, Oakland). "
            "\n--- MATCHING LOGIC ---\n"
            "1. LITERAL TITLES: Your 'title' field must match the job title in the search snippet. "
            "2. SNIPPET: Include the exact text from the search result justifying this lead. "
            f"3. KEYWORDS: Match as many as possible: {keywords}. "
            f"4. SALARY: Prioritize roles matching or exceeding ${salary:,}+. "
            "\n--- OUTPUT RULE ---\n"
            "You MUST output a valid JSON list. If NO jobs are found, return an empty list: []. "
            "Do not provide conversational text. "
            "\nOutput ONLY a JSON list of objects with: title, company, salary, location, source, link, snippet."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': temp_setting
                }
            )
            
            if response and response.text:
                raw_text = response.text
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
                    
                    if not job_list:
                        st.warning("No jobs found matching your criteria. Try loosening your keywords.")
                    else:
                        leads = pd.DataFrame(job_list)
                        leads.columns = [c.lower() for c in leads.columns]

                        # FILTERS
                        if 'link' in leads.columns:
                            leads = leads[leads['link'].str.count('/') > 2]
                            leads = leads[~leads['link'].str.contains('a1b2c3d4|98765|12345', na=False)]
                            noise = ['/blog/', '/resources/', '/advice/', 'top-10']
                            leads = leads[~leads['link'].str.contains('|'.join(noise), case=False, na=False)]

                        st.success(f"Scout complete! Found {len(leads)} verified leads.")
                        
                        st.data_editor(
                            leads,
                            column_config={
                                "link": st.column_config.LinkColumn("Source Link", display_text="View Posting", width="medium"),
                                "snippet": st.column_config.TextColumn("AI Context (Snippet Audit)", width="large"),
                            },
                            hide_index=True,
                            use_container_width=True,
                            disabled=leads.columns
                        )
                else:
                    # SYSTEM LOG FOR DEBUGGING
                    st.error("Data format mismatch: The AI response did not contain a valid list.")
                    with st.expander("🔍 View System Log (Raw AI Output)"):
                        st.code(raw_text)
            else:
                st.error("Empty response from the AI.")
                
        except Exception as e:
            st.error(f"Scouting Error: {e}")