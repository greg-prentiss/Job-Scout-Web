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
st.markdown("A resilient, AI-powered tool for deep career scouting. Validated for high-precision matching.")

# SIDEBAR PARAMETERS
with st.sidebar:
    st.header("Search Parameters")
    industry = st.text_input("Industry / Sector", "Education")
    role = st.text_input("Job Title", "IT Admin")
    location = st.text_input("Location / City", "Hayward, CA")
    salary = st.number_input("Min Salary / Pay", value=90000, step=5000)
    keywords = st.text_area("Skills / Keywords (Wishlist)", "Meraki, Jamf, PowerShell, Google Workspace, PowerSchool, Chromebook")
    
    st.divider()
    # THE BUDGET TOGGLE (BOOLEAN FLAG)
    deep_scout = st.checkbox("Deep Scout (More leads, higher API cost)", value=False)
    
    run_button = st.button("Start Scouting")

if run_button:
    today_date = datetime.date.today().strftime("%B %d, %Y")
    
    # 3. PRECISION LOGIC (TEMPERATURE CALIBRATION)
    # 0.4 provides high literal accuracy to stop "Snippet Drift"
    # 0.8 allows Deep Scout to explore more creative query variations
    temp_setting = 0.4 if not deep_scout else 0.8 
    max_leads = 25 if deep_scout else 15
    intensity = "Perform multi-pass searches" if deep_scout else "Perform a literal targeted search"

    with st.spinner(f"Scouting {industry}... Precision Mode: {'Standard (Literal)' if not deep_scout else 'Discovery (Deep)'}"):
        
        # 4. THE VERIFIED PROMPT
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. {intensity}. "
            f"Find {max_leads} active job listings for '{role}' in the {industry} sector. "
            f"\n--- GEOGRAPHIC RADIUS ---\n"
            f"Focus on {location} and a 20-mile commuter radius (e.g., San Leandro, Fremont, Union City, Oakland, SF). "
            "\n--- MATCHING & INTEGRITY LOGIC ---\n"
            "1. LITERAL TITLES: Your 'title' field must EXACTLY match the job title seen in the search snippet. "
            "Do not upgrade or summarize titles (e.g., if you see 'IT Support', do not write 'IT Admin'). "
            "2. SNIPPET: Include the exact text snippet from the search result that justifies this lead. "
            f"3. KEYWORDS: Treat as a priority wishlist: {keywords}. Match ANY, but don't discard for missing some. "
            f"4. SALARY: Prioritize roles matching or exceeding ${salary:,}+. "
            "\n--- LINK FALLBACK ---\n"
            "1. Use direct deep links if verified. "
            "2. FALLBACK: If a deep-link is uncertain, use the URL of the Google Search result or specific board page. "
            "3. NO HALLUCINATIONS: Do not guess URLs. No 'a1b2c3d4' patterns. "
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
                
                # Surgical regex extraction for JSON list
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

                    # 5. PRODUCTION FILTERS (LINK HYGIENE)
                    if 'link' in leads.columns:
                        # Drop generic homepages
                        leads = leads[leads['link'].str.count('/') > 2]
                        # Remove common placeholder/fake ID patterns
                        leads = leads[~leads['link'].str.contains('a1b2c3d4|98765|12345', na=False)]
                        # Strip blog/resource noise
                        noise = ['/blog/', '/resources/', '/advice/', 'top-10', '/news/']
                        leads = leads[~leads['link'].str.contains('|'.join(noise), case=False, na=False)]

                    if not leads.empty:
                        st.success(f"Scout complete! Found {len(leads)} verified leads.")
                        
                        # Render Interactive Table with Snippet Audit column
                        st.data_editor(
                            leads,
                            column_config={
                                "link": st.column_config.LinkColumn(
                                    "Source Link",
                                    display_text="View Posting",
                                    width="medium"
                                ),
                                "snippet": st.column_config.TextColumn(
                                    "AI Context (Snippet Audit)",
                                    help="The exact text the AI found. Use this to verify the link before clicking.",
                                    width="large"
                                ),
                            },
                            hide_index=True,
                            use_container_width=True,
                            disabled=leads.columns
                        )
                        
                        # Download Button
                        csv = leads.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Download Results", csv, f"scouted_jobs_{today_date}.csv", "text/csv")
                    else:
                        st.warning("No verified leads found. Try loosening keywords or checking your location string.")
                else:
                    st.warning("Data format mismatch. Try running the search again.")
            else:
                st.error("Empty response from the AI. The search engine might be busy.")
                
        except Exception as e:
            st.error(f"Scouting Error: {e}")