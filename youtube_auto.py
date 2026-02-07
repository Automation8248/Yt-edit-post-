import os
import requests
import urllib.parse
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
    "title_prompt": "Write a short viral motivational quote video title in English under 60 characters. No hashtags. No quotes.",
    "desc_prompt": "Write a deep, educational and inspiring explanation (max 2 sentences) about the importance of success and learning. Plain text only. No stars. No hashtags inside text.",
    
    # 3. SEO Settings
    "seo_hashtags": "#Education #Motivation #Learning #Success #StudyMotivation #Wisdom #Shorts #Facts",
    
    # 4. Tags List (Must be more than 8)
    "tags": [
        "Education",              # Tag 1
        "Motivation",             # Tag 2
        "Learning",               # Tag 3
        "Success Mindset",        # Tag 4
        "Study Tips",             # Tag 5
        "Life Lessons",           # Tag 6
        "Wisdom",                 # Tag 7
        "Self Improvement",       # Tag 8
        "Educational Video",      # Tag 9
        "Facts",                  # Tag 10
        "Knowledge",              # Tag 11
        "Inspiration"             # Tag 12
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

def send_telegram_alert(video_id, channel_name):
    """
    Sends Telegram Alert in Specific Format:
    1. Channel Name (Bold, Red Style)
    2. Successful Message
    3. Category
    4. Link
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return

    video_link = f"https://youtu.be/{video_id}"
    
    # --- TELEGRAM FORMATTING LOGIC ---
    # Telegram API does not support CSS color/size. 
    # We use HTML <b> (Bold) and Uppercase to simulate "Big Size".
    # We use 🔴 Emoji to simulate "Red Color".
    
    formatted_name = f"<b>🔴 {channel_name.upper()} 🔴</b>"

    message = (
        f"{formatted_name}\n"
        f"Message: Upload Successful\n"
        f"Category: Education\n"
        f"{video_link}"
    )
    
    # 'parse_mode': 'HTML' is strictly required for Bold/Format
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
        print(f"--- STARTING STRICT AUTOMATION FOR: {TOPIC_NAME} ---")
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
                print(f"Target Found: {vid_id}")
                break 
        
        if not target_video:
            print("No Unlisted/Private videos found.")
            return

        vid_id = target_video["id"]
        snippet = target_video["snippet"]
        
        # --- AI & CONTENT LOGIC ---
        
        # A) TITLE GENERATION
        current_title = snippet["title"]
        new_title = current_title
        
        if len(current_title) < 10 or "upload" in current_title.lower() or "untitled" in current_title.lower():
            print("AI Writing Title...")
            ai_title = ask_pollinations_ai(CONFIG["title_prompt"])
            if ai_title:
                new_title = ai_title.replace('"', '').replace("'", "")
                if len(new_title) > 70: new_title = new_title[:67] + "..."
        
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
            # Altered Content is 'No' by default
        }
        
        youtube.videos().update(
            part="snippet,status",
            body=update_body
        ).execute()
        
        print(f"SUCCESS: Video Updated | Category: Education")
        
        # Telegram Message with Name Size/Color logic
        display_name = snippet["channelTitle"] if snippet["channelTitle"] else CHANNEL_CUSTOM_NAME
        send_telegram_alert(vid_id, display_name)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()
