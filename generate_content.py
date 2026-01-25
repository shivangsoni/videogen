"""
YouTube Shorts Content Generator using Free LLM API (Groq)
Generates script.txt, metadata.txt, and youtube_publish.txt for new folders
"""

import os
import json
import requests
from pathlib import Path

# Groq API (free tier available at console.groq.com)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_groq_api_key():
    """Get Groq API key from environment or .env file"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip('"\'')
                        break
    return api_key

def generate_with_groq(prompt: str, api_key: str) -> str:
    """Call Groq API to generate content"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama-3.3-70b-versatile",  # Free model on Groq
        "messages": [
            {
                "role": "system",
                "content": "You are a viral YouTube Shorts script writer. Create punchy, impactful content that hooks viewers in 2 seconds and delivers value in under 60 seconds. Use short sentences. Be direct. No fluff."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.8,
        "max_tokens": 1000
    }
    
    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def generate_content_for_topic(topic: str, keywords: str, api_key: str, folder_name: str = None) -> dict:
    """Generate all content files for a topic"""
    
    prompt = f"""Create a YouTube Shorts script about: {topic}
Keywords to use: {keywords}

Follow this EXACT format:

SCRIPT:
Hook (0-2s):
[One powerful opening line that stops scrolling]

Core:
[4-6 short punchy lines, each on its own line]
[Use line breaks between thoughts]
[Keep each line under 10 words]

End (CTA):
[Call to action - save/follow/share]

TITLE:
[Catchy YouTube title under 60 chars, use emotion words]

DESCRIPTION:
[3-4 lines with emojis, include the hook and CTA]

Return ONLY the content in this format, no explanations."""

    response = generate_with_groq(prompt, api_key)
    
    # Parse the response
    content = {
        "script": "",
        "title": "",
        "description": "",
        "keywords": keywords,
        "folder_name": folder_name or ""
    }
    
    lines = response.strip().split("\n")
    current_section = None
    
    for line in lines:
        line_lower = line.lower().strip()
        
        if line_lower.startswith("script:"):
            current_section = "script"
            continue
        elif line_lower.startswith("title:"):
            current_section = "title"
            continue
        elif line_lower.startswith("description:"):
            current_section = "description"
            continue
        
        if current_section == "script":
            content["script"] += line + "\n"
        elif current_section == "title":
            if line.strip():
                content["title"] = line.strip()
                current_section = None
        elif current_section == "description":
            content["description"] += line + "\n"
    
    # Clean up
    content["script"] = content["script"].strip()
    content["description"] = content["description"].strip()
    
    return content

def create_folder_structure(content: dict, base_path: str = "youtubeshorts"):
    """Create the folder with all required files"""
    folder_path = Path(base_path) / content["folder_name"]
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # script.txt
    script_path = folder_path / "script.txt"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content["script"])
    print(f"  Created: {script_path}")
    
    # metadata.txt
    metadata_path = folder_path / "metadata.txt"
    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write(f"keywords: {content['keywords']}")
    print(f"  Created: {metadata_path}")
    
    # youtube_publish.txt
    publish_path = folder_path / "youtube_publish.txt"
    with open(publish_path, "w", encoding="utf-8") as f:
        f.write(f"Title: {content['title']}\n")
        f.write(f"Description:\n")
        f.write(f"    {content['description'].replace(chr(10), chr(10) + '    ')}")
    print(f"  Created: {publish_path}")
    
    return folder_path

# Topics to generate content for
TOPICS = [
    {
        "topic": "The power of saying no. Protect your time. Every yes to something unimportant is a no to your dreams.",
        "keywords": "boundaries, time management, priorities, success",
        "folder": "sayingno"
    },
    {
        "topic": "Why successful people wake up at 5am. Quiet hours, no distractions, compound advantage over time.",
        "keywords": "waking up early, success habits, productivity, discipline",
        "folder": "wakeup5am"
    },
    {
        "topic": "The 1% rule: Improve 1% daily. After one year you'll be 37 times better. Small gains compound.",
        "keywords": "self improvement, compound growth, habits, consistency",
        "folder": "onepercent"
    },
    {
        "topic": "Your circle determines your future. You become the average of the 5 people you spend most time with.",
        "keywords": "relationships, success, environment, growth mindset",
        "folder": "yourcircle"
    },
    {
        "topic": "The 90-90-1 rule: For the next 90 days, spend the first 90 minutes on your most important goal. Watch your life transform.",
        "keywords": "focus, goals, productivity, time management",
        "folder": "ninetyninety"
    }
]

def main():
    api_key = get_groq_api_key()
    
    if not api_key:
        print("=" * 50)
        print("GROQ API KEY NOT FOUND")
        print("=" * 50)
        print("\nGet a FREE API key at: https://console.groq.com")
        print("\nThen add to your .env file:")
        print('GROQ_API_KEY=your_key_here')
        print("\nOr set environment variable:")
        print("$env:GROQ_API_KEY = 'your_key_here'")
        return
    
    print("=" * 50)
    print("YOUTUBE SHORTS CONTENT GENERATOR")
    print("=" * 50)
    print(f"\nGenerating {len(TOPICS)} folders...\n")
    
    created_folders = []
    
    for i, topic_info in enumerate(TOPICS, 1):
        print(f"\n[{i}/{len(TOPICS)}] Generating content...")
        print(f"  Topic: {topic_info['topic'][:50]}...")
        print(f"  Folder: {topic_info['folder']}")
        
        try:
            content = generate_content_for_topic(
                topic_info["topic"],
                topic_info["keywords"],
                api_key,
                topic_info["folder"]
            )
            
            folder_path = create_folder_structure(content)
            created_folders.append(folder_path)
            
            print(f"  [OK] Created folder: {content['folder_name']}")
            print(f"  Title: {content['title']}")
            
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"\nCreated {len(created_folders)} folders:")
    for folder in created_folders:
        print(f"  - {folder}")
    
    print("\nTo generate videos, run:")
    print("  python batch_video_generator.py --all")
    
    print("\nTo generate for a specific folder:")
    print("  python batch_video_generator.py --folder <folder_name>")

if __name__ == "__main__":
    main()
