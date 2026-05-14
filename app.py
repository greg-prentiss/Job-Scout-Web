import streamlit as st
import pandas as pd
from google.genai import Client
import json
import datetime

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
        # UPDATED PROMPT: Explicitly ordering the Search-Result Fallback
        prompt = (
            f"Today is {today_date}. Act as a senior recruiter. "
            f"Find 15-20 active job listings for '{role}' in {location}. "
            f"Prioritize matches for: {keywords}. Target salary: ${salary:,}+. "
            "\n--- THE UNIVERSAL FALLBACK PROTOCOL ---\n"
            "1. You must provide a URL for every job found. "
            "2. If you find a direct application link (Greenhouse, Lever, Company Career Page), use it. "
            "3. FALLBACK: If a direct link is not obvious, you MUST provide the URL of the Google Search result "
            "or the job board aggregator page (Indeed, LinkedIn, ZipRecruiter) where the job was seen. "
            "4. NEVER synthesize or guess a URL. If a URL is not explicitly in the search data, use the search source URL. "
            "\nOutput the results as a JSON list of objects with these keys: title, company, salary, location, source, link."
        )

        try:
            # FORCED JSON MODE: This removes the need for regex parsing
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.6,
                    'response_mime_type': 'application/json'
                }
            )
            
            # Since we forced JSON mode, response.text will be a clean JSON string
            job_list = json.loads(response.text)
            
            if job_list and len(job_list) > 0:
                leads = pd.DataFrame(job_list)
                leads.columns = [c.lower() for c in leads.columns]

                # Filter: Final check to remove obvious hallucinations (IDs like a1b2c3d4)
                placeholders = ['a1b2c3d4', '98765', '12345', 'placeholder']
                if 'link' in leads.columns:
                    leads = leads[~leads['link'].str.contains('|'.join(placeholders), case=False, na=False)]

                st.success(f"Scout complete! Found {len(leads)} potential leads.")
                
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
                
                csv = leads.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, "jobs.csv", "text/csv")
            else:
                st.warning("The scout found 0 results. Try removing a keyword to broaden the search.")
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")