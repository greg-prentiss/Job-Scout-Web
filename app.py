import streamlit as st
import pandas as pd
from google.genai import Client
import json
import datetime
import re

# 1. SECURE API KEY ACCESS
# Ensure GEMINI_API_KEY is set in your Streamlit Secrets
client = Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. BRANDING & UI SETUP
st.set_page_config(page_title="Career-Paths", layout="wide")
st.title("📡 Career-Paths")
st.markdown("A flexible, AI-powered tool to scout the live web for your next career move.")

# SIDEBAR PARAMETERS
with st.sidebar:
    st.header("Search Parameters")
    industry = st.text_input("Industry / Sector", "Education")
    role = st.text_input("Job Title", "IT Admin")
    location = st.text_input("Location / City", "Hayward, CA")
    salary = st.number_input("Min Salary / Pay", value=90000, step=5000)
    keywords = st.text_area("Skills / Keywords (Wishlist)", "Meraki, Jamf, PowerShell, Google Workspace, PowerSchool, Chromebook")
    
    st.divider()
    # THE BUDGET TOGGLE
    deep_scout = st.checkbox("Deep Scout (More leads, higher API cost)", value=False)
    
    run_button = st.button("Start Scouting")

if run_button:
    today_date = datetime.date.today().strftime("%B %d, %Y")
    
    # 3. COST-OPTIMIZATION LOGIC
    # Adjusting parameters based on the Deep Scout flag
    max_leads = 25 if deep_scout else 10
    intensity = "Perform multiple comprehensive deep-pass searches" if deep_scout else "Perform a quick, targeted search"
    temp_setting = 0.2 if not deep_scout else 0.7 # Higher variance for deep scouting

    with st.spinner(f"Scouting the {industry} sector... Intensity: {'High' if deep_scout else 'Standard'}"):
        
        # 4. UNIVERSAL AGNOSTIC PROMPT
        prompt = (
            f"Today is {today_date}. Act as a senior recruiter. {intensity}. "
            f"Find {max_leads} active job listings for '{role}' in the {industry} sector. "
            f"\n--- GEOGRAPHIC RADIUS ---\n"
            f"Focus on {location} and a 20-mile commuter radius (e.g., San Leandro, Fremont, Union City, Oakland, SF). "
            "\n--- MATCHING LOGIC ---\n"
            f"1. KEYWORDS: Treat these as a priority wishlist: {keywords}. "
            "Match as many as possible, but do NOT discard a job for missing some keywords. "
            f"2. SALARY: Prioritize roles matching or exceeding ${salary:,}+. "
            "\n--- LINK INTEGRITY & FALLBACK ---\n"
            "1. ONLY return real job postings. Skip blog posts or career advice articles. "
            "2. If you find a direct application link, use it. "
            "3. FALLBACK: If a deep-link is missing or uncertain, you MUST provide the URL of the "
            "Google Search results page or the job board page where the job is clearly visible. "
            "4. NO HALLUCINATIONS: Do not guess IDs or URLs. No 'a1b2c3d4' placeholder links. "
            "\nOutput ONLY a JSON list of objects with: title, company, salary, location, source, link."
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
                
                # Robust regex extraction for JSON list
                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                
                if match:
                    json_str = match.group(0).strip()
                    
                    # Bracket balancing for clean JSON extraction
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

                    # 5. POST-PROCESSING FILTERS
                    if 'link' in leads.columns:
                        # Drop generic homepages (require at least two slashes in path)
                        leads = leads[leads['link'].str.count('/') > 2]
                        # Remove common placeholder/fake ID patterns
                        leads = leads[~leads['link'].str.contains('a1b2c3d4|98765|12345', na=False)]
                        # Strip blog/resource noise
                        noise = ['/blog/', '/resources/', '/advice/', 'top-10', '/news/']
                        leads = leads[~leads['link'].str.contains('|'.join(noise), case=False, na=False)]

                    if not leads.empty:
                        st.success(f"Scout complete! Found {len(leads)} potential leads.")
                        
                        # Render Interactive Table
                        st.data_editor(
                            leads,
                            column_config={
                                "link": st.column_config.LinkColumn(
                                    "Source Link",
                                    display_text="View Posting",
                                    width="medium"
                                ),
                            },
                            hide_index=True,
                            use_container_width=True,
                            disabled=leads.columns
                        )
                        
                        # Download Button for results
                        csv = leads.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Download Results", csv, f"scouted_jobs_{today_date}.csv", "text/csv")
                    else:
                        st.warning("No technical leads found. Try loosening your keywords or expanding location.")
                else:
                    st.warning("The scout couldn't isolate a formatted list. Try running the search again.")
            else:
                st.error("Empty response from the AI. The search tool may be throttled.")
                
        except Exception as e:
            st.error(f"Scouting Error: {e}")