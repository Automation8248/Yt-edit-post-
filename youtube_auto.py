import os
import requests
import urllib.parse
import re  # Regex for filename detection
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ==========================================
# 👇 STRICT CONFIGURATION (Education Mode) 👇
# ==========================================

TOPIC_NAME = "Education_Motivation"

CONFIG = {
    # 1. Category Setting (STRICTLY Education)
    "category_id": "27",  
    
    # 2. AI Prompts (No Stars, No Hashtags in text)
    "title_prompt": "Write a short viral motivational quote video title in English under 60 characters. No hashtags. No quotes. No emoji.",
    "desc_prompt": "Write a deep, educational and inspiring explanation (max 2 sentences) about the importance of success and learning. Plain text only. No stars. No hashtags inside text.",
    
    # 3. SEO Settings
    "seo_hashtags": "#Education #Motivation #Learning #Success #StudyMotivation #Wisdom #Shorts #Facts",
    
    # 4. Tags List (Must be more than 8)
    "tags": [
        "Education", "Motivation", "Learning", "Success Mindset", 
        "Study Tips", "Life Lessons", "Wisdom", "Self Improvement", 
        "Educational Video", "Facts", "Knowledge", "Inspiration"
    ]
}

CHANNEL_CUSTOM_NAME = "My Education Channel"

# ==========================================
# 👆 CONFIGURATION END 👆
# ==========================================

def get_youtube_service():
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not client_id or not refresh_token:
        raise ValueError("Secrets missing! Check GitHub Settings.")

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )
    return build("youtube", "v3", credentials=creds)

def ask_pollinations_ai(prompt):
    """AI se unique text generate karna"""
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}?seed={os.urandom(4).hex()}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return None
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def should_replace_title(title):
    """
    Check karta hai ki kya Title badalne ki zarurat hai.
    Agar title filename jaisa dikhta hai to True return karega.
    """
    # 1. Agar title bahut chhota hai
    if len(title) < 5:
        return True
    
    # 2. Agar title mein 'Untitled' ya 'Upload' word hai
    if "untitled" in title.lower() or "upload" in title.lower():
        return True
        
    # 3. Agar title mein Spaces nahi hain (e.g., VID_20250207) -> Filename hai
    if " " not in title:
        return True
        
    # 4. Agar title mein Date format hai (e.g., 2025-02-07)
    if re.search(r'\d{4}-\d{2}-\d{2}', title):
        return True
        
    return False

def send_telegram_alert(video_id, channel_name):
    """
    Telegram Message Format:
    Channel Name (Big Red)
    Message
    Category
    Link
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return

    video_link = f"https://youtu.be/{video_id}"
    
    # Red & Bold Simulation using Emoji and HTML
    formatted_name = f"<b>🔴 {channel_name.upper()} 🔴</b>"

    message = (
        f"{formatted_name}\n"
        f"Message: Upload Successful\n"
        f"Category: Education\n"
        f"{video_link}"
    )
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id, 
        'text': message, 
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }
    
    requests.post(url, json=payload)

def main():
    try:
        print(f"--- STARTING AUTOMATION ---")
        youtube = get_youtube_service()
        
        # 1. Latest Video Search
        request = youtube.search().list(
            part="snippet",
            forMine=True,
            type="video",
            maxResults=5
        )
        response = request.execute()
        
        target_video = None
        
        # 2. Find Unlisted/Private Video
        for item in response.get("items", []):
            vid_id = item["id"]["videoId"]
            
            vid_request = youtube.videos().list(
                part="snippet,status,contentDetails",
                id=vid_id
            )
            vid_response = vid_request.execute()
            
            if not vid_response["items"]:
                continue
                
            video_data = vid_response["items"][0]
            privacy = video_data["status"]["privacyStatus"]
            
            if privacy in ["private", "unlisted"]:
                target_video = video_data
                print(f"Target Found: {vid_id} | Current Title: {video_data['snippet']['title']}")
                break 
        
        if not target_video:
            print("No Unlisted/Private videos found.")
            return

        vid_id = target_video["id"]
        snippet = target_video["snippet"]
        
        # --- AI & CONTENT LOGIC ---
        
        # A) TITLE GENERATION (Updated Logic)
        current_title = snippet["title"]
        new_title = current_title
        
        # Check karega ki kya title filename/date jaisa hai
        if should_replace_title(current_title):
            print("Detected generic/filename title. Generating new AI Title...")
            ai_title = ask_pollinations_ai(CONFIG["title_prompt"])
            if ai_title:
                new_title = ai_title.replace('"', '').replace("'", "")
                if len(new_title) > 70: new_title = new_title[:67] + "..."
        else:
            print("Existing title looks good. Keeping it.")
        
        # B) DESCRIPTION GENERATION
        print("AI Writing Description...")
        ai_desc = ask_pollinations_ai(CONFIG["desc_prompt"])
        if not ai_desc:
            ai_desc = "Learn and grow with these motivational quotes."
            
        final_description = f"{ai_desc}\n\n{CONFIG['seo_hashtags']}"
        
        # C) TAGS LOGIC (STRICT CHECK >= 8)
        final_tags = CONFIG["tags"]
        if len(final_tags) < 8:
            final_tags.extend(["Viral", "Trending", "Must Watch", "New Video"])

        # --- UPDATE VIDEO ---
        
        update_body = {
            "id": vid_id,
            "snippet": {
                "categoryId": CONFIG["category_id"], # Fixed to 27
                "title": new_title,
                "description": final_description,
                "tags": final_tags, # 8+ Tags
                "channelTitle": snippet["channelTitle"]
            },
            "status": {
                "privacyStatus": "public",       # Public
                "selfDeclaredMadeForKids": False, # Not Made For Kids
                "embeddable": True,
                "license": "youtube"
            }
            # IMP: Altered Content 'No' Logic
            # Hum yahan koi bhi AI label metadata nahi bhej rahe hain.
            # YouTube API by default isse "Altered Content: No" manta hai.
        }
        
        youtube.videos().update(
            part="snippet,status",
            body=update_body
        ).execute()
        
        print(f"SUCCESS: Video Public | Title: {new_title}")
        
        # Telegram Message
        display_name = snippet["channelTitle"] if snippet["channelTitle"] else CHANNEL_CUSTOM_NAME
        send_telegram_alert(vid_id, display_name)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
