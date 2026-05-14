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

    with st.spinner(f"Scouting verified sources for {role} roles..."):
        # UPDATED PROMPT: Prioritizing "Search Result Fallback" over hallucinated deep links
        prompt = (
            f"Today is {today_date}. Act as a senior technical recruiter. "
            f"Find 15-20 active job listings for '{role}' in {location}. "
            f"Priorities: {keywords}. Target: ${salary:,}+. "
            "\n--- VERIFICATION PROTOCOL ---\n"
            "1. provide a WORKING URL for every job found. "
            "2. If a direct application deep-link is visible in the search results, use it. "
            "3. FALLBACK: If a direct deep-link is not visible, you MUST provide the URL of the Google Search result "
            "or the job board page (Indeed, LinkedIn, etc.) where the job was seen. "
            "4. NEVER guess or synthesize a URL (e.g., no 'a1b2c3d4' or '98765' placeholders). "
            "5. It is better to provide a search result link than a broken 404 link. "
            "\nReturn ONLY a JSON list of objects. No markdown. No preamble. "
            "Keys: title, company, salary, location, source, link."
        )

        try:
            # Reverted: No response_mime_type to stay compatible with Google Search tool
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={
                    'tools': [{'google_search': {}}],
                    'temperature': 0.4 
                }
            )
            
            raw_text = response.text
            
            # HARDENED EXTRACTION: Using regex to find the first valid list block
            # This prevents "Extra Data" errors by ignoring anything outside the brackets.
            match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            
            if match:
                json_str = match.group(0).strip()
                
                # Manual trim if the AI provided text after the final bracket
                # This ensures json.loads only sees the list
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

                # Post-Processing: Kill common hallucinated ID patterns
                placeholders = ['a1b2c3d4', '98765', '12345', 'placeholder']
                if 'link' in leads.columns:
                    leads = leads[~leads['link'].str.contains('|'.join(placeholders), case=False, na=False)]

                st.success(f"Scout complete! Found {len(leads)} potential leads.")
                
                st.data_editor(
                    leads,
                    column_config={
                        "link": st.column_config.LinkColumn(
                            "Verified Source",
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
                st.warning("The scout found data but couldn't isolate the list. Try running it once more.")
            
        except Exception as e:
            st.error(f"Scouting Error: {e}")
            with st.expander("Debug: View Raw Output"):
                st.code(raw_text)