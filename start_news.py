import os
import subprocess
from crewai import Agent, Task, Crew, LLM

# 1. SETUP
local_llm = LLM(
    model="ollama/llama3.2", 
    base_url="http://localhost:11434",
    temperature=0.1
)

# 2. THE AGENT (Simplified to prevent loops)
journalist = Agent(
    role='ANN Senior Editor',
    goal='Write a professional 12-story news report for April 8, 2026.',
    backstory="You are a master of HTML and Markdown. You write beautiful news grids.",
    llm=local_llm,
    verbose=True
)

# 3. THE TASK (Forcing the HTML Layout)
ann_task = Task(
    description="""
    Write a 12-story news report for April 8, 2026. 
    Include 4 stories for TECH, 4 for TUNISIA, and 4 for WORLD.
    
    YOU MUST START THE OUTPUT WITH THIS EXACT FRONT-MATTER:
    ---
    layout: default
    title: ANN | GLOBAL INTELLIGENCE
    ---

    Format the news using professional Markdown tables with Headlines, Summaries, and Links.
    """,
    agent=journalist,
    expected_output="A full Markdown news report starting with the --- header.",
    output_file="index.md"
)

def push_to_github():
    print("\n--- ANN Network: Syncing to Web ---")
    # Forces the script to look at the Desktop folder
    os.chdir(os.path.expanduser("~/Desktop"))
    try:
        subprocess.run('git add index.md', shell=True)
        subprocess.run('git commit -m "ANN Intelligence Launch"', shell=True)
        subprocess.run('git push origin main', shell=True)
        print("\n🚀 SUCCESS: Site updated!")
    except Exception as e:
        print(f"\n❌ Push failed: {e}")

if __name__ == "__main__":
    crew = Crew(agents=[journalist], tasks=[ann_task])
    crew.kickoff()
    push_to_github()