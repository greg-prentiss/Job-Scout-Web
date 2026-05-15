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
st.markdown("A flexible, AI-powered tool to scout the live web for your next career move.")

with st.sidebar:
    st.header("Search Parameters")
    # Dynamically handle industry and roles for a broader user base
    industry = st.text_input("Industry / Sector", "I.T. & Systems")
    role = st.text_input("Job Title", "IT Systems Lead")
    location = st.text_input("Location / City", "Hayward, CA")
    salary = st.number_input("Min Salary / Pay", value=90000, step=5000)
    keywords = st.text_area("Skills / Keywords (Wishlist)", "Meraki, Jamf, PowerShell, Google Workspace")
    
    run_button = st.button("Start Scouting")

if run_button:
    today_date = datetime.date.today().strftime("%B %d, %Y")

    with st.spinner(f"Scouting the web for {role} roles in {industry}..."):
        # UPDATED PROMPT: Weighted Matching + High Volume + Agnostic Fallback
        prompt = (
            f"Today is {today_date}. Act as a world-class career consultant. "
            f"Your mission is to find UP TO 25 active, real job listings for '{role}' in the {industry} sector. "
            f"\n--- GEOGRAPHIC FLEXIBILITY ---\n"
            f"Focus on {location} and a 20-mile surrounding radius (commutable distance). "
            "If results are low, include verified 'Remote' options for the same role. "
            f"\n--- MATCHING LOGIC ---\n"
            f"1. KEYWORDS: Treat these as a priority wishlist: {keywords}. "
            "Do NOT discard a job if it only matches some keywords. Match as many as possible. "
            f"2. SALARY: Prioritize roles near or above ${salary:,}+. "
            "3. RELEVANCY: Ensure the job is actually in the '{industry}' domain. "
            "\n--- VERIFICATION & LINKS ---\n"
            "1. Only return real job postings. Skip blog posts and 'Top 10' articles. "
            "2. If you find a direct application link (Greenhouse, Lever, etc.), use it. "
            "3. FALLBACK: If a direct link is missing, provide the URL of the Google Search result or the aggregator page. "
            "4. NO HALLUCINATIONS: Do not guess or invent URLs. Use the literal URL from the search data. "
            "\nOutput ONLY a JSON list of objects with: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.9 # High variety for maximum lead discovery
                }
            )
            
            if response and response.text:
                raw_text = response.text
                # Surgical extraction of the JSON block
                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                
                if match:
                    json_str = match.group(0).strip()
                    try:
                        job_list = json.loads(json_str)
                        leads = pd.DataFrame(job_list)
                        leads.columns = [c.lower() for c in leads.columns]

                        # Post-Processing: Filtering out common article traps
                        noise = ['/blog/', '/resources/', '/advice/', 'top-10', '/news/']
                        if 'link' in leads.columns:
                            leads = leads[~leads['link'].str.contains('|'.join(noise), case=False, na=False)]
                            # Filter out placeholder ID hallucinations
                            leads = leads[~leads['link'].str.contains('a1b2c3d4|98765|12345', na=False)]

                        if not leads.empty:
                            st.success(f"Scout complete! Found {len(leads)} potential leads.")
                            st.data_editor(
                                leads,
                                column_config={
                                    "link": st.column_config.LinkColumn(
                                        "View Source",
                                        display_text="View Posting",
                                        width="medium"
                                    ),
                                },
                                hide_index=True,
                                use_container_width=True,
                                disabled=leads.columns
                            )
                            # Allow friends to download their results
                            csv = leads.to_csv(index=False).encode('utf-8')
                            st.download_button("📥 Download My Jobs", csv, "scouted_jobs.csv", "text/csv")
                        else:
                            st.warning("No technical leads found. Try loosening your keywords.")
                    except Exception as e:
                        st.error(f"Data formatting error: {e}")
                else:
                    st.warning("The search parameters were too narrow for the AI to format a list. Try again with fewer keywords.")
            else:
                st.error("Empty response from AI. The search tool might be busy—try again in 30 seconds.")
                
        except Exception as e:
            st.error(f"Scouting Error: {e}")