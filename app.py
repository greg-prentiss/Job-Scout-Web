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

    with st.spinner(f"Scouting {industry} for verified technical roles..."):
        # UPDATED PROMPT: Cross-Verification Logic to stop the "EdJoin Trap"
        prompt = (
            f"Today is {today_date}. Act as a senior recruiter specializing in {industry}. "
            f"Search for 15-20 ACTIVE, non-expired technical job listings for '{role}' in {location}. "
            f"Tech Stack: {keywords}. Salary floor: ${salary:,}+. "
            "\n--- ANTI-HALLUCINATION PROTOCOL ---\n"
            "1. VERIFICATION: You must ensure the Job Title and Company are explicitly mentioned in the search result for the link provided. "
            "2. NO SEQUENTIAL GUESSING: Do not guess URLs by incrementing ID numbers (e.g., JobPosting/123, JobPosting/124). "
            "3. EXPIRED LINKS: If a search snippet says 'This posting has expired' or 'Closed', skip it immediately. "
            "4. FALLBACK: If a deep-link is not verified, provide the direct URL to the Google Search result page for that specific job. "
            "5. EDUCATION SPECIFIC: If searching Education, ignore 'School Administrator' or 'Principal' roles. Focus on I.T. roles only. "
            "\nOutput ONLY a JSON list of objects with: title, company, salary, location, source, link."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.3 # Lowered to minimum for maximum accuracy
                }
            )
            
            if response and response.text:
                raw_text = response.text
                
                # Robust extraction: Finds the first '[' and last ']'
                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                
                if match:
                    json_str = match.group(0).strip()
                    
                    try:
                        job_list = json.loads(json_str)
                        leads = pd.DataFrame(job_list)
                        leads.columns = [c.lower() for c in leads.columns]

                        # POST-PROCESSING: Scrubbing for Hallucination Patterns
                        if 'link' in leads.columns:
                            # 1. Remove generic 'placeholder' patterns
                            placeholders = ['a1b2c3d4', '98765', '12345', 'placeholder']
                            leads = leads[~leads['link'].str.contains('|'.join(placeholders), case=False, na=False)]
                            
                            # 2. Filter out blog/advice articles
                            noise = ['/blog/', '/resources/', '/advice/', 'top-10', '/wu-news/']
                            leads = leads[~leads['link'].str.contains('|'.join(noise), case=False, na=False)]

                        st.success(f"Verified {len(leads)} technical leads for {today_date}!")
                        
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
                    except Exception as parse_error:
                        st.error(f"Data formatting error: {parse_error}")
                        with st.expander("Review Raw Data"):
                            st.code(raw_text)
                else:
                    st.warning("No data found. Try broadening your location or reducing keywords.")
            else:
                st.error("The AI returned an empty response. Please try again.")
                
        except Exception as e:
            st.error(f"Scouting Error: {e}")