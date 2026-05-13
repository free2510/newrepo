# -*- coding: utf-8 -*-
"""
Video Scraper & Uploader - Final Version
Scrapes videos from larozaa.yachts, uploads to DoodStream with organized folders,
and updates Google Sheets in REAL-TIME after each video.

Folder Structure on DoodStream:
  Ramadan 2026 - مسلسلات (Category)
    └── مسلسل روج اسود (Series)
        └── مسلسل روج اسود الحلقة 7 السابعة.mp4 (Video)

Google Sheet Updates: AFTER EACH VIDEO (real-time)
"""

import os
import re
import time
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from google.colab import drive
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from doodstream import DoodStream

# ==================== CONFIGURATION ====================
CATEGORY_URL = "https://larozaa.yachts/category.php?cat=ramadan-2026"
DOODSTREAM_API_KEY = "566462d6434dlvqu6fmesc"
GOOGLE_SHEET_ID = "1Bpvo9v6san0VsD6Y1vW26UlxYWpWDqWFVbFga-Cczjg"
CATEGORY_NAME = "رمضان 2026 - مسلسلات"
TEMP_FOLDER = "/content/drive/MyDrive/.temp_videos"
PROCESSED_FILE = "/content/processed_videos.json"

# ==================== INITIALIZATION ====================
print("=" * 60)
print("🚀 Video Processing Pipeline - REAL-TIME UPDATES")
print("=" * 60)

# Install required packages
print("\n📦 Installing dependencies...")
!pip install -q requests beautifulsoup4 tqdm doodstream gspread oauth2client

# Initialize DoodStream
dood = DoodStream(DOODSTREAM_API_KEY)

# Setup Google Drive
print("\n🔐 Mounting Google Drive...")
try:
    drive.mount("/content/drive", force_remount=False)
except Exception as e:
    print(f"Drive already mounted: {e}")

os.makedirs(TEMP_FOLDER, exist_ok=True)

# Load processed videos (for resume capability)
processed_videos = set()
if os.path.exists(PROCESSED_FILE):
    try:
        with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
            processed_videos = set(json.load(f))
        print(f"📋 Loaded {len(processed_videos)} previously processed videos")
    except:
        pass

# ==================== GOOGLE SHEETS SETUP ====================
print("\n📊 Connecting to Google Sheets...")

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = None
token_path = '/content/token.json'
credentials_path = '/content/credentials.json'

try:
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google.colab import auth
            auth.authenticate_user()
            creds = Credentials.from_authorized_user_file(token_path, SCOPES) if os.path.exists(token_path) else None
            
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    drive_service = build('drive', 'v3', credentials=creds)
    print("✅ Google Sheets + Drive connected")
except Exception as e:
    print(f"⚠️ Connection issue: {e}")
    print("Will retry on first update...")
    sheet = None
    service = None
    drive_service = None

def init_sheet():
    """Initialize Google Sheet with headers if needed"""
    global sheet, service, drive_service
    try:
        if not service:
            from google.colab import auth
            auth.authenticate_user()
            creds = Credentials.from_authorized_user_file(token_path, SCOPES) if os.path.exists(token_path) else None
            service = build('sheets', 'v4', credentials=creds)
            sheet = service.spreadsheets()
            drive_service = build('drive', 'v3', credentials=creds)
        
        # Check if sheet has headers
        result = sheet.values().get(spreadsheetId=GOOGLE_SHEET_ID, range='Sheet1!A1:Z1').execute()
        values = result.get('values', [])
        
        if not values or not values[0]:
            # Add headers
            headers = [['Timestamp', 'Title', 'Video ID', 'Watch Link', 'Series Name', 
                       'Category', 'DoodStream Watch', 'DoodStream Download', 'Status']]
            sheet.values().update(
                spreadsheetId=GOOGLE_SHEET_ID,
                range='Sheet1!A1:I1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            print("✅ Sheet headers added")
        return True
    except Exception as e:
        print(f"⚠️ Sheet init error: {e}")
        return False

def upload_to_google_drive(file_path, title):
    """Upload file to Google Drive and return file ID"""
    global drive_service
    
    try:
        if not drive_service:
            init_sheet()
        
        if not drive_service:
            print("❌ Cannot connect to Google Drive")
            return None
        
        # File metadata
        file_metadata = {
            'name': f"[TEMP] {title}",
            'parents': [TEMP_FOLDER.replace('/content/drive/MyDrive/', '')]  # Put in temp folder
        }
        
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        print(f"   ✅ Uploaded to Drive: https://drive.google.com/file/d/{file_id}/view")
        
        return file_id
        
    except Exception as e:
        print(f"❌ Drive upload error: {e}")
        return None

# ==================== SCRAPING FUNCTIONS ====================
def scrape_category_videos(url):
    """Scrape all videos from category page"""
    print(f"\n📥 Fetching videos from: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    videos = []
    # Find all video items
    video_items = soup.select('li.col-xs-6.col-sm-4.col-md-3')
    
    for item in video_items:
        try:
            link_tag = item.find('a', href=True)
            if not link_tag:
                continue
                
            video_url = link_tag['href'].strip()
            title = link_tag.get('title', '').strip()
            
            # Extract video ID
            parsed = urlparse(video_url)
            params = parse_qs(parsed.query)
            video_id = params.get('vid', [None])[0]
            
            if not video_id:
                continue
            
            # Skip if already processed
            if video_id in processed_videos:
                print(f"⏭️  Skipping (already processed): {title[:50]}...")
                continue
            
            videos.append({
                'title': title,
                'video_id': video_id,
                'watch_page_url': f"https://larozaa.yachts/play.php?vid={video_id}",
                'url': video_url
            })
        except Exception as e:
            continue
    
    print(f"✅ Found {len(videos)} new videos to process")
    return videos

def get_watch_servers(play_url):
    """Get all watch servers from play page"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(play_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    servers = []
    # Find watch list
    watch_list = soup.find('ul', class_='WatchList')
    if not watch_list:
        return servers
    
    li_tags = watch_list.find_all('li', attrs={'data-embed-url': True})
    for li in li_tags:
        server_name = li.find('strong')
        embed_url = li.get('data-embed-url', '').strip()
        
        if server_name and embed_url:
            servers.append({
                'name': server_name.get_text(strip=True),
                'url': embed_url
            })
    
    return servers

def extract_video_url(server_url):
    """Extract direct video URL from server embed page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': server_url
        }
        
        response = requests.get(server_url, headers=headers, timeout=15)
        
        # Look for video sources
        patterns = [
            r'source\s*=\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            r"data-url=['\"]([^'\"]+\.mp4[^'\"]+)['\"]",
            r"file:\s*['\"]([^'\"]+\.mp4[^'\"]+)['\"]",
            r"<source\s+src=['\"]([^'\"]+\.mp4[^'\"]+)['\"]",
            r'https?://[^\s"\'<>]+\.mp4'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            if matches:
                video_url = matches[0].strip()
                if video_url.startswith('//'):
                    video_url = 'https:' + video_url
                
                # Verify it's a valid video URL
                head = requests.head(video_url, headers=headers, timeout=10, allow_redirects=True)
                content_type = head.headers.get('Content-Type', '')
                
                if 'video' in content_type or head.status_code == 200:
                    return video_url
        
        return None
    except Exception as e:
        return None

def download_video(url, filename):
    """Download video with progress bar"""
    filepath = os.path.join(TEMP_FOLDER, filename)
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(filepath, 'wb') as f, tqdm(
            desc=f"⬇️ {filename[:40]}",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        # Verify download
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1024 * 1024:  # > 1MB
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"✅ Download successful! Size: {size_mb:.2f} MB")
            return filepath
        else:
            print(f"❌ Download failed: File too small")
            if os.path.exists(filepath):
                os.remove(filepath)
            return None
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return None

# ==================== DOODSTREAM FUNCTIONS ====================
def get_or_create_folder_structure(series_name):
    """Create Category -> Series folder structure on DoodStream"""
    
    # Step 1: Find or create Category folder
    category_folder_id = None
    try:
        files = dood.list_files()
        for item in files:
            if item.get('name') == CATEGORY_NAME and item.get('is_folder'):
                category_folder_id = item.get('id')
                print(f"📁 Found category folder: {CATEGORY_NAME} (ID: {category_folder_id})")
                break
        
        if not category_folder_id:
            print(f"📁 Creating category folder: {CATEGORY_NAME}")
            result = dood.create_folder(name=CATEGORY_NAME)
            if result and isinstance(result, dict):
                category_folder_id = result.get('id') or result.get('foldercode')
                # Refresh file list
                time.sleep(1)
                files = dood.list_files()
                for item in files:
                    if item.get('name') == CATEGORY_NAME:
                        category_folder_id = item.get('id')
                        break
            
            if not category_folder_id:
                # Try to find it anyway
                for item in files:
                    if item.get('name') == CATEGORY_NAME:
                        category_folder_id = item.get('id')
                        break
    except Exception as e:
        print(f"⚠️ Category folder error: {e}")
    
    # Step 2: Find or create Series folder inside Category
    series_folder_id = None
    if category_folder_id:
        try:
            series_files = dood.list_files(folder_id=category_folder_id)
            for item in series_files:
                if item.get('name') == series_name and item.get('is_folder'):
                    series_folder_id = item.get('id')
                    print(f"📁 Found series folder: {series_name} (ID: {series_folder_id})")
                    break
            
            if not series_folder_id:
                print(f"📁 Creating series folder: {series_name}")
                result = dood.create_folder(name=series_name, parent_id=category_folder_id)
                if result and isinstance(result, dict):
                    series_folder_id = result.get('id') or result.get('foldercode')
                    time.sleep(1)
                    # Verify creation
                    series_files = dood.list_files(folder_id=category_folder_id)
                    for item in series_files:
                        if item.get('name') == series_name:
                            series_folder_id = item.get('id')
                            break
        except Exception as e:
            print(f"⚠️ Series folder error: {e}")
    
    return category_folder_id, series_folder_id

def upload_to_doodstream(file_path, series_name, video_title, drive_file_id=None):
    """Upload video to DoodStream in correct folder, then delete from Google Drive"""
    
    cat_folder_id, series_folder_id = get_or_create_folder_structure(series_name)
    
    try:
        print(f"⬆️ Uploading to DoodStream...")
        
        # Upload to root first
        result = dood.local_upload(file_path)
        
        if not result:
            print("❌ Upload failed: No response from DoodStream")
            return None
        
        # Handle different response formats
        file_code = None
        if isinstance(result, list) and len(result) > 0:
            file_code = result[0].get('filecode') if isinstance(result[0], dict) else None
        elif isinstance(result, dict):
            file_code = result.get('result', {}).get('filecode') or result.get('filecode')
        
        if not file_code:
            print(f"❌ Could not get file code from upload. Response: {result}")
            return None
        
        print(f"✅ Uploaded! File code: {file_code}")
        
        # Move to series folder if available
        if series_folder_id:
            try:
                # Copy to folder (DoodStream API uses copy then delete original)
                move_result = dood.copy_video(file_code, series_folder_id)
                if move_result:
                    print(f"📁 Moved to series folder: {series_name}")
                    # Delete original from root
                    dood.delete_file([file_code])
                    # Get new file code from folder
                    folder_files = dood.list_files(folder_id=series_folder_id)
                    for item in folder_files:
                        if item.get('name') and video_title[:20] in item.get('name', ''):
                            file_code = item.get('id') or item.get('filecode')
                            break
            except Exception as e:
                print(f"⚠️ Could not move to folder: {e}")
        
        # Get share links
        try:
            links = dood.get_download_sources(file_code)
            watch_link = links.get('download_url') if links else f"https://doodstream.com/d/{file_code}"
            dl_link = links.get('download_url') if links else f"https://doodstream.com/download/{file_code}"
        except:
            watch_link = f"https://doodstream.com/d/{file_code}"
            dl_link = f"https://doodstream.com/download/{file_code}"
        
        # ✅ CRITICAL: Delete from Google Drive IMMEDIATELY after successful upload
        if drive_file_id:
            try:
                print(f"   🗑️ Deleting temp file from Google Drive...")
                drive_service.files().delete(fileId=drive_file_id).execute()
                print(f"   ✅ Temp file deleted from Drive!")
            except Exception as del_err:
                print(f"   ⚠️ Warning: Could not delete temp file: {del_err}")
        
        return {
            'file_code': file_code,
            'watch_link': watch_link,
            'download_link': dl_link
        }
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        # Try to cleanup even on error
        if drive_file_id:
            try:
                drive_service.files().delete(fileId=drive_file_id).execute()
            except:
                pass
        return None

# ==================== GOOGLE SHEETS UPDATE ====================
def update_sheet_realtime(video_data, status="Processing"):
    """Update Google Sheet IMMEDIATELY after each video"""
    global sheet, service
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if not service:
                init_sheet()
            
            if not service:
                print("⚠️ Cannot connect to Google Sheets")
                return False
            
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            row_data = [
                timestamp,
                video_data.get('title', ''),
                video_data.get('video_id', ''),
                video_data.get('watch_link', ''),
                video_data.get('series_name', ''),
                video_data.get('category', CATEGORY_NAME),
                video_data.get('dood_watch', ''),
                video_data.get('dood_download', ''),
                status
            ]
            
            # Append new row
            sheet.values().append(
                spreadsheetId=GOOGLE_SHEET_ID,
                range='Sheet1!A:I',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [row_data]}
            ).execute()
            
            print(f"✅ REAL-TIME UPDATE: Row added to Google Sheet")
            return True
            
        except Exception as e:
            print(f"⚠️ Sheet update attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                init_sheet()
            else:
                print("❌ Failed to update sheet after 3 attempts")
                return False
    
    return False

def save_processed_video(video_id):
    """Save processed video ID for resume capability"""
    processed_videos.add(video_id)
    try:
        with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(processed_videos), f, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Could not save progress: {e}")

# ==================== MAIN PROCESSING ====================
def extract_series_name(title):
    """Extract series name from video title"""
    # Pattern: "مسلسل XXX الحلقة YYY"
    match = re.match(r'(مسلسل\s+[^\s]+(?:\s+[^\s]+)?)\s+الحلقة', title)
    if match:
        return match.group(1).strip()
    return title.split('الحلقة')[0].strip() if 'الحلقة' in title else title[:30]

def process_video(video_info, index, total):
    """Process single video with real-time updates"""
    
    print("\n" + "=" * 60)
    print(f"🎬 [{index}/{total}] {video_info['title']}")
    print("=" * 60)
    
    video_data = {
        'title': video_info['title'],
        'video_id': video_info['video_id'],
        'watch_link': '',
        'series_name': extract_series_name(video_info['title']),
        'category': CATEGORY_NAME,
        'dood_watch': '',
        'dood_download': ''
    }
    
    # Update sheet: Starting
    update_sheet_realtime(video_data, status="⏳ Starting")
    
    # Step 1: Get watch servers
    print("   🔍 Getting watch servers...")
    servers = get_watch_servers(video_info['watch_page_url'])
    print(f"   📺 Found {len(servers)} servers")
    
    if not servers:
        update_sheet_realtime(video_data, status="❌ No servers found")
        return False
    
    # Step 2: Try servers until we find working video URL
    video_url = None
    for idx, server in enumerate(servers, 1):
        print(f"   🧪 Testing server {idx}/{len(servers)}: {server['name']}")
        
        extracted_url = extract_video_url(server['url'])
        if extracted_url:
            video_url = extracted_url
            print(f"   ✅ Working server found: {server['name']}")
            print(f"   🌐 Video URL: {video_url[:80]}...")
            video_data['watch_link'] = server['url']
            break
    
    if not video_url:
        print("   ❌ No working server found")
        update_sheet_realtime(video_data, status="❌ No working server")
        return False
    
    # Step 3: Download video to Google Drive (temp)
    safe_filename = f"{video_info['video_id']}_{video_data['series_name']}.mp4"
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in (' ', '.', '_')).strip()
    safe_filename = safe_filename.replace(' ', '_')[:100] + ".mp4"
    
    print(f"   📥 Downloading video...")
    downloaded_path = download_video(video_url, safe_filename)
    
    if not downloaded_path:
        update_sheet_realtime(video_data, status="❌ Download failed")
        return False
    
    # Upload to Google Drive first (as temp storage)
    print(f"   ☁️ Uploading to Google Drive (temp)...")
    drive_file_id = upload_to_google_drive(downloaded_path, video_info['title'])
    
    if not drive_file_id:
        update_sheet_realtime(video_data, status="❌ Drive upload failed")
        return False
    
    # Step 4: Upload to DoodStream (pass drive_file_id for cleanup)
    print(f"   ⬆️ Uploading to DoodStream...")
    dood_result = upload_to_doodstream(
        downloaded_path, 
        video_data['series_name'], 
        video_info['title'],
        drive_file_id  # ✅ Pass drive_file_id for automatic deletion
    )
    
    # Cleanup temp file
    try:
        if os.path.exists(downloaded_path):
            os.remove(downloaded_path)
            print("   🗑️ Temp file deleted")
    except:
        pass
    
    if not dood_result:
        update_sheet_realtime(video_data, status="❌ DoodStream upload failed")
        return False
    
    video_data['dood_watch'] = dood_result['watch_link']
    video_data['dood_download'] = dood_result['download_link']
    
    # Step 5: FINAL UPDATE - Success
    update_sheet_realtime(video_data, status="✅ Success")
    
    # Save progress
    save_processed_video(video_info['video_id'])
    
    print(f"   🎉 COMPLETED!")
    print(f"   📺 Watch: {dood_result['watch_link']}")
    print(f"   ⬇️ Download: {dood_result['download_link']}")
    
    return True

# ==================== EXECUTION ====================
def main():
    """Main execution function"""
    
    # Initialize sheet
    init_sheet()
    
    # Scrape videos
    videos = scrape_category_videos(CATEGORY_URL)
    
    if not videos:
        print("\n✅ All videos already processed or no videos found!")
        return
    
    # Process each video
    total = len(videos)
    success_count = 0
    
    print(f"\n🚀 Starting processing of {total} videos...")
    
    for idx, video in enumerate(videos, 1):
        try:
            if process_video(video, idx, total):
                success_count += 1
            
            # Small delay between videos
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error processing {video['title']}: {e}")
            # Still update sheet with error
            video_data = {
                'title': video['title'],
                'video_id': video['video_id'],
                'series_name': extract_series_name(video['title']),
                'dood_watch': '',
                'dood_download': ''
            }
            update_sheet_realtime(video_data, status=f"❌ Error: {str(e)[:50]}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PROCESSING COMPLETE")
    print("=" * 60)
    print(f"✅ Successfully processed: {success_count}/{total}")
    print(f"💾 Progress saved - you can resume anytime by running again")
    print(f"📄 Google Sheet updated in real-time with all results")
    print("=" * 60)

if __name__ == "__main__":
    main()
