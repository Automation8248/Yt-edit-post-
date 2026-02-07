import os
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# --- CONFIGURATION ---
TAGS_TO_ADD = ["Automation", "Python", "Tech", "Viral"]  # Yahan apne tags dalein
CHANNEL_CUSTOM_NAME = "Lucas Hart" # Telegram message ke liye channel name

def get_youtube_service():
    # GitHub Secrets se credentials uthana
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

def send_telegram_alert(video_id, channel_name):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Telegram secrets missing, skipping alert.")
        return

    video_link = f"https://youtu.be/{video_id}"
    
    # Message Format (As per your request)
    message = (
        f"📢 {channel_name}\n\n"
        f"✅ Successful! Video public ho chuka hai.\n\n"
        f"🔗 {video_link}"
    )
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    
    try:
        requests.post(url, json=payload)
        print("Telegram message sent.")
    except Exception as e:
        print(f"Telegram error: {e}")

def main():
    try:
        youtube = get_youtube_service()
        
        # 1. Channel ki latest uploads find karna
        request = youtube.search().list(
            part="snippet",
            forMine=True,
            type="video",
            maxResults=5  # Last 5 videos check karega
        )
        response = request.execute()
        
        target_video_id = None
        current_tags = []
        
        # 2. Check karna ki kaunsa video UNLISTED hai
        for item in response.get("items", []):
            vid_id = item["id"]["videoId"]
            
            # Detail check karo (Privacy Status ke liye)
            vid_request = youtube.videos().list(
                part="snippet,status",
                id=vid_id
            )
            vid_response = vid_request.execute()
            
            if not vid_response["items"]:
                continue
                
            video_data = vid_response["items"][0]
            privacy = video_data["status"]["privacyStatus"]
            
            if privacy == "unlisted":
                target_video_id = vid_id
                # Existing tags bacha ke rakhne ke liye (optional)
                current_tags = video_data["snippet"].get("tags", [])
                channel_title = video_data["snippet"]["channelTitle"]
                print(f"Found Unlisted Video: {target_video_id}")
                break # Pehla unlisted video milte hi ruk jao
        
        if not target_video_id:
            print("No unlisted videos found today.")
            return

        # 3. Video Update Karna (Public + Tags + Not Made for Kids)
        # Naye tags purane tags ke saath merge karna
        final_tags = list(set(current_tags + TAGS_TO_ADD))
        
        update_body = {
            "id": target_video_id,
            "snippet": {
                "categoryId": video_data["snippet"]["categoryId"],
                "title": video_data["snippet"]["title"],
                "description": video_data["snippet"]["description"],
                "tags": final_tags, # Tags Added
                "channelTitle": channel_title
            },
            "status": {
                "privacyStatus": "public", # Public Set
                "selfDeclaredMadeForKids": False # Not Made for Kids
            }
        }
        
        youtube.videos().update(
            part="snippet,status",
            body=update_body
        ).execute()
        
        print(f"Video {target_video_id} updated successfully!")
        
        # 4. Send Telegram Alert
        # Agar API se channel name nahi aaya to custom use karega
        display_name = channel_title if channel_title else CHANNEL_CUSTOM_NAME
        send_telegram_alert(target_video_id, display_name)

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
