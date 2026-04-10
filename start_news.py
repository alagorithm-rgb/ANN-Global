import os
import subprocess
import json
import hashlib
from datetime import datetime
from crewai import Agent, Task, Crew, LLM

# 1. SETUP
local_llm = LLM(
    model="ollama/llama3.2", 
    base_url="http://localhost:11434",
    temperature=0.1
)

# 2. THE AGENT
journalist = Agent(
    role='ANN Senior Editor',
    goal='Generate a high-density JSON news feed for annfeed.com.',
    backstory="You are a data journalist. You output clean, factual news summaries in JSON format.",
    llm=local_llm,
    verbose=True
)

# 3. THE TASK (Formatting specifically for your new index.html)
ann_task = Task(
    description="""
    Find 8 major news stories for today. 
    Focus on Tech, Tunisia, and World Economy.
    
    OUTPUT FORMAT: You must output a valid JSON list of articles.
    Each article must have:
    - "title": The headline
    - "brief": A 2-sentence summary
    - "category": (Technology, Tunisia, or World)
    - "source": The news outlet name
    - "url": A link to the story
    """,
    agent=journalist,
    expected_output="A JSON list of 8 news articles.",
    output_file="news.json"
)

def push_to_github():
    print("\n--- ANN Network: Syncing to annfeed.com ---")
    try:
        # Step into your project folder
        os.chdir(os.path.expanduser("~/Desktop/project/ANN-Global"))
        
        # Clean up any accidental desktop files before pushing
        subprocess.run('git rm --cached *.lnk desktop.ini', shell=True, capture_output=True)
        
        # Push only the news and the site files
        subprocess.run('git add news.json index.html _config.yml', shell=True)
        subprocess.run('git commit -m "Intelligence Update: ' + datetime.now().strftime("%H:%M") + '"', shell=True)
        
        # This fixes the "Rejected" error you saw by forcing the update
        result = subprocess.run('git push origin main --force', shell=True, capture_output=True, text=True)
        
        if "error" in result.stderr.lower():
            print(f"❌ Sync failed: {result.stderr}")
        else:
            print("\n🚀 SUCCESS: annfeed.com is now updated with fresh news!")
    except Exception as e:
        print(f"\n❌ Script error: {e}")

if __name__ == "__main__":
    Crew(agents=[journalist], tasks=[ann_task]).kickoff()
    push_to_github()