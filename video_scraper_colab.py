# -*- coding: utf-8 -*-
"""
Video Scraper, Downloader, and Doodstream Uploader
Scrapes larozaa.yachts, downloads to Google Drive, uploads to Doodstream
Organizes by series name in folders
"""

# Install required packages
!pip install requests beautifulsoup4 google-api-python-client doodstream pandas tqdm

import requests
from bs4 import BeautifulSoup
import re
import os
import time
from urllib.parse import urlparse, parse_qs
import pandas as pd
from tqdm import tqdm
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from doodstream import DoodStream

# ==================== CONFIGURATION ====================
BASE_URL = "https://larozaa.yachts"
CATEGORY_URL = "https://larozaa.yachts/category.php?cat=ramadan-2026"
GOOGLE_SHEET_ID = "1h4WDPuxUaDreza60h8VjcMLqnbKleWXw9AfMCpjfnnI"
DOODSTREAM_API_KEY = "566462d6434dlvqu6fmesc"

# Initialize DoodStream client
dood = DoodStream(api_key=DOODSTREAM_API_KEY)

# ==================== GOOGLE DRIVE SETUP ====================
def setup_google_drive():
    """Setup Google Drive API authentication using Colab's built-in auth"""
    from google.colab import auth
    from googleapiclient.discovery import build
    
    # Authenticate using Colab's built-in auth (no credentials file needed)
    print("Authenticating with Google using Colab...")
    auth.authenticate_user()
    
    # Build services with default Colab credentials
    drive_service = build('drive', 'v3')
    sheets_service = build('sheets', 'v4')
    
    print("✓ Google Drive and Sheets connected")
    return drive_service, sheets_service

# ==================== SCRAPING FUNCTIONS ====================
def get_category_videos(category_url):
    """Scrape category page for video listings"""
    print(f"Scraping category page: {category_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    response = requests.get(category_url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all video items using the XPath equivalent
    # /html/body/div[1]/div[2]/div[4]/div/div/div/ul/li
    video_items = []
    
    # Try to find the ul containing video items
    ul_element = soup.select_one('div.col-md-9 div.row div.thumbnail')
    if not ul_element:
        # Alternative selector based on the structure
        video_containers = soup.find_all('li', class_=lambda x: x and 'col-xs-6' in x)
    else:
        video_containers = soup.find_all('li', class_=lambda x: x and 'col-' in x)
    
    for container in video_containers:
        try:
            link_tag = container.find('a', href=True)
            if link_tag:
                video_url = link_tag['href'].strip()
                title = link_tag.get('title', '').strip()
                
                # Extract vid parameter
                vid_match = re.search(r'vid=([a-zA-Z0-9]+)', video_url)
                if vid_match:
                    video_id = vid_match.group(1)
                    video_items.append({
                        'video_id': video_id,
                        'title': title,
                        'watch_page_url': f"{BASE_URL}/play.php?vid={video_id}"
                    })
        except Exception as e:
            print(f"Error parsing video item: {e}")
            continue
    
    print(f"Found {len(video_items)} videos")
    return video_items

def get_watch_servers(play_url):
    """Get watch server URLs from play page"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    try:
        response = requests.get(play_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        servers = []
        # Find WatchList ul
        watch_list = soup.find('ul', class_='WatchList')
        
        if watch_list:
            li_elements = watch_list.find_all('li', attrs={'data-embed-url': True})
            
            for li in li_elements:
                embed_url = li.get('data-embed-url', '').strip()
                embed_id = li.get('data-embed-id', '')
                server_name = li.find('strong').get_text(strip=True) if li.find('strong') else f"Server {embed_id}"
                
                if embed_url:
                    servers.append({
                        'server_id': embed_id,
                        'server_name': server_name,
                        'embed_url': embed_url
                    })
        
        return servers
    except Exception as e:
        print(f"Error getting watch servers: {e}")
        return []

def extract_direct_video_url(embed_url):
    """Try to extract direct video URL from embed page"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': embed_url,
    }
    
    try:
        response = requests.get(embed_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for video tag
        video_tag = soup.find('video')
        if video_tag and video_tag.get('src'):
            return video_tag['src']
        
        # Look for source tags
        source_tag = soup.find('source')
        if source_tag and source_tag.get('src'):
            return source_tag['src']
        
        # Look for jwplayer or similar configurations
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'sources' in script.string:
                # Try to extract URL from JavaScript
                url_match = re.search(r'["\']?(https?://[^"\']+\.mp4)["\']?', script.string)
                if url_match:
                    return url_match.group(1)
        
        return None
    except Exception as e:
        print(f"Error extracting video URL: {e}")
        return None

# ==================== GOOGLE DRIVE FUNCTIONS ====================
def create_folder_if_not_exists(drive_service, folder_name, parent_id='root'):
    """Create folder in Google Drive if it doesn't exist"""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    
    if files:
        return files[0]['id']
    else:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder['id']

def download_file(url, filename, chunk_size=8192):
    """Download file from URL"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Range': 'bytes=0-',
    }
    
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(filename, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        return True
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False

def upload_to_google_drive(drive_service, file_path, folder_id):
    """Upload file to Google Drive"""
    file_name = os.path.basename(file_path)
    
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(file_path, resumable=True)
    
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink, webContentLink'
    ).execute()
    
    # Make file publicly accessible
    drive_service.permissions().create(
        fileId=file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()
    
    return {
        'id': file['id'],
        'view_link': file.get('webViewLink', ''),
        'download_link': file.get('webContentLink', '')
    }

def delete_file_from_drive(drive_service, file_id):
    """Delete file from Google Drive"""
    try:
        drive_service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False

# ==================== DOODSTREAM FUNCTIONS ====================
def create_doodstream_folder(folder_name):
    """Create folder in Doodstream"""
    try:
        # Check if folder exists
        folders = dood.folder_list()
        for folder in folders.get('folders', []):
            if folder['name'] == folder_name:
                return folder['id']
        
        # Create new folder
        result = dood.folder_create(name=folder_name)
        if result.get('status') == 200:
            return result.get('result', {}).get('folderid')
        return None
    except Exception as e:
        print(f"Error creating Doodstream folder: {e}")
        return None

def upload_to_doodstream(file_path, folder_id=None):
    """Upload file to Doodstream"""
    try:
        # Get upload URL
        upload_info = dood.upload_url()
        if upload_info.get('status') != 200:
            print("Failed to get upload URL")
            return None
        
        upload_url = upload_info.get('result', {}).get('url')
        
        # Upload file
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(upload_url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 200:
                file_code = result.get('result', {}).get('filecode')
                
                # Move to folder if specified
                if folder_id and file_code:
                    dood.folder_move(folder_id=folder_id, file_codes=file_code)
                
                # Get share link
                share_info = dood.file_share(file_code)
                if share_info.get('status') == 200:
                    return {
                        'file_code': file_code,
                        'share_link': share_info.get('result', {}).get('url', ''),
                        'download_link': f"https://doodstream.com/d/{file_code}"
                    }
        
        return None
    except Exception as e:
        print(f"Error uploading to Doodstream: {e}")
        return None

# ==================== GOOGLE SHEETS FUNCTIONS ====================
def update_google_sheet(sheets_service, sheet_id, data):
    """Update Google Sheet with video data"""
    # Prepare data for sheet
    values = [['Video Title', 'Video ID', 'Watch Page URL', 'Server URL', 
               'Google Drive Link', 'Doodstream Link', 'Series Name']]
    
    for item in data:
        values.append([
            item.get('title', ''),
            item.get('video_id', ''),
            item.get('watch_page_url', ''),
            item.get('server_url', ''),
            item.get('google_drive_link', ''),
            item.get('doodstream_link', ''),
            item.get('series_name', '')
        ])
    
    body = {
        'values': values
    }
    
    # Clear existing data and write new data
    sheets_service.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range='Sheet1!A:G'
    ).execute()
    
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='Sheet1!A1',
        valueInputOption='RAW',
        body=body
    ).execute()
    
    print("Google Sheet updated successfully")

# ==================== MAIN PROCESSING ====================
def extract_series_name(title):
    """Extract series name from video title"""
    # Common patterns in Arabic titles
    # Example: "مسلسل درش الحلقة 30" -> "درش"
    patterns = [
        r'مسلسل\s+(\S+)\s+الحلقة',  # مسلسلات followed by series name then الحلقة
        r'مسلسل\s+(\S+)',  # مسلسلات followed by series name
        r'(\S+)\s+الحلقة',  # Series name before الحلقة
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return match.group(1)
    
    # If no pattern matches, return first word
    words = title.split()
    if len(words) > 0:
        return words[0]
    
    return "Unknown"

def process_videos(max_videos=None, test_mode=False):
    """Main processing function"""
    print("=" * 50)
    print("Starting Video Processing Pipeline")
    print("=" * 50)
    
    # Setup Google services
    print("\nSetting up Google Drive and Sheets...")
    drive_service, sheets_service = setup_google_drive()
    
    # Scrape category page
    print("\nScraping category page...")
    videos = get_category_videos(CATEGORY_URL)
    
    if not videos:
        print("No videos found!")
        return
    
    # Limit number of videos for testing
    if max_videos:
        videos = videos[:max_videos]
    
    results = []
    
    # Process each video
    for i, video in enumerate(videos, 1):
        print(f"\n{'='*50}")
        print(f"Processing video {i}/{len(videos)}: {video['title']}")
        print(f"{'='*50}")
        
        video_result = video.copy()
        video_result['series_name'] = extract_series_name(video['title'])
        
        # Get watch servers
        print("Getting watch servers...")
        servers = get_watch_servers(video['watch_page_url'])
        
        if not servers:
            print("No servers found, skipping...")
            continue
        
        # Try first server (or iterate through servers)
        selected_server = servers[0]  # Start with first server
        video_result['server_url'] = selected_server['embed_url']
        print(f"Selected server: {selected_server['server_name']}")
        
        # Extract direct video URL
        print("Extracting direct video URL...")
        video_url = extract_direct_video_url(selected_server['embed_url'])
        
        if not video_url:
            print("Could not extract direct URL, trying next server...")
            for server in servers[1:]:
                video_url = extract_direct_video_url(server['embed_url'])
                if video_url:
                    video_result['server_url'] = server['embed_url']
                    print(f"Found working server: {server['server_name']}")
                    break
        
        if not video_url:
            print("No working video URL found, skipping...")
            continue
        
        print(f"Video URL: {video_url}")
        
        # Download video
        if not test_mode:
            filename = f"{video_result['video_id']}.mp4"
            print(f"Downloading video: {filename}")
            
            if download_file(video_url, filename):
                print("Download successful!")
                
                # Create series folder in Google Drive
                series_folder_id = create_folder_if_not_exists(
                    drive_service, 
                    video_result['series_name']
                )
                
                # Upload to Google Drive
                print("Uploading to Google Drive...")
                drive_info = upload_to_google_drive(drive_service, filename, series_folder_id)
                video_result['google_drive_link'] = drive_info['view_link']
                print(f"Google Drive link: {drive_info['view_link']}")
                
                # Create series folder in Doodstream
                print("Creating Doodstream folder...")
                dood_folder_id = create_doodstream_folder(video_result['series_name'])
                
                # Upload to Doodstream
                print("Uploading to Doodstream...")
                dood_info = upload_to_doodstream(filename, dood_folder_id)
                
                if dood_info:
                    video_result['doodstream_link'] = dood_info['share_link']
                    print(f"Doodstream link: {dood_info['share_link']}")
                else:
                    print("Failed to upload to Doodstream")
                    video_result['doodstream_link'] = ''
                
                # Delete local file
                print("Cleaning up local file...")
                os.remove(filename)
                
                # Note: We keep file in Google Drive as backup
                # Uncomment below to delete from Google Drive after Doodstream upload
                # delete_file_from_drive(drive_service, drive_info['id'])
            else:
                print("Download failed!")
                video_result['google_drive_link'] = ''
                video_result['doodstream_link'] = ''
        else:
            print("Test mode - skipping download and upload")
            video_result['google_drive_link'] = 'Test Mode'
            video_result['doodstream_link'] = 'Test Mode'
        
        results.append(video_result)
        
        # Rate limiting
        time.sleep(2)
    
    # Update Google Sheet
    print("\nUpdating Google Sheet...")
    update_google_sheet(sheets_service, GOOGLE_SHEET_ID, results)
    
    print("\n" + "=" * 50)
    print("Processing Complete!")
    print(f"Successfully processed {len(results)} videos")
    print("=" * 50)
    
    return results

# ==================== RUN THE SCRIPT ====================
if __name__ == "__main__":
    # Run with test_mode=False for actual processing
    # Set max_videos to limit number of videos processed (useful for testing)
    results = process_videos(max_videos=5, test_mode=False)
    
    # Display results
    if results:
        df = pd.DataFrame(results)
        print("\nResults Summary:")
        print(df[['title', 'video_id', 'series_name']].to_string())
