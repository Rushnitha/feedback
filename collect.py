# Make sure you've run: pip install google-api-python-client
from googleapiclient.discovery import build
import json

# --- START: YOUR CONFIGURATION ---
# TODO: Paste your API key here
API_KEY = "AIzaSyAQOXz0E2cl_5wibaDMy2csgFMElzRl_0Q" 

# The keyword you want to search for
SEARCH_QUERY = input("what do you want to search about :")
# --- END: YOUR CONFIGURATION ---


def main():
    if API_KEY == "YOUR_API_KEY_GOES_HERE":
        print("Error: Please paste your API key into the API_KEY variable.")
        return

    # 1. Build the YouTube API client
    # This 'youtube' object is what you'll use to call the API
    youtube = build('youtube', 'v3', developerKey=API_KEY)

    print(f"Searching for videos about: '{SEARCH_QUERY}'...\n")

    # 2. Call the search.list method
    search_request = youtube.search().list(
        q=SEARCH_QUERY,
        part="snippet", # 'snippet' contains basic info like title, channel, etc.
        type="video",   # We only want videos, not channels or playlists
        maxResults=5    # Ask for the top 5 results
    )
    
    # The 'execute()' method sends the request
    search_response = search_request.execute()

    # --- 3. Process the Search Results ---
    
    # Get the first video from the results
    first_video = search_response['items'][0]
    video_id = first_video['id']['videoId']
    video_title = first_video['snippet']['title']

    print(f"--- Found Video ---")
    print(f"Title: {video_title}")
    print(f"Video ID: {video_id}\n")


    # --- 4. Get Video Details (Statistics) ---
    print(f"Fetching stats for video ID: {video_id}...")
    
    video_request = youtube.videos().list(
        part="statistics,snippet", # Ask for 'statistics' and 'snippet'
        id=video_id                # Specify the video ID
    )
    video_response = video_request.execute()

    if not video_response['items']:
        print("Error: Video details not found.")
        return

    video_item = video_response['items'][0]
    view_count = video_item['statistics'].get('viewCount', 0)
    like_count = video_item['statistics'].get('likeCount', 0)
    comment_count = video_item['statistics'].get('commentCount', 0)
    
    print(f"Views: {view_count} | Likes: {like_count} | Comments: {comment_count}\n")


    # --- 5. Get Video Comments ---
    print(f"Fetching top comments for video ID: {video_id}...")

    try:
        comment_request = youtube.commentThreads().list(
            part="snippet",     # 'snippet' contains the comment text
            videoId=video_id,
            maxResults=10,      # Get the first 10 comment threads
            order="relevance"   # Or use "time" for most recent
        )
        comment_response = comment_request.execute()

        print("\n--- Top Comments ---")
        for item in comment_response['items']:
            # Get the actual comment text
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            author = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
            
            # Print with a nice format
            print(f"Author: {author}")
            print(f"Comment: {comment}\n" + "-"*20 + "\n")

    except Exception as e:
        print(f"\nCould not retrieve comments. They may be disabled for this video.")
        print(f"Error details: {e}")


if __name__ == "__main__":
    main()