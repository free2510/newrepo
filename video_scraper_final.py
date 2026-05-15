# -*- coding: utf-8 -*-
"""
Video Scraper & Uploader - Final Version
Scrapes videos from larozaa.yachts, uploads to DoodStream with organized folders,
and updates Google Sheets in REAL-TIME after each video.

Folder Structure on DoodStream:
  رمضان 2026 - مسلسلات (Category)
    └── مسلسل حكاية نرجس (Series)
        └── مسلسل حكاية نرجس الحلقة 7 السابعة.mp4 (Video)

Google Sheet Updates: AFTER EACH VIDEO (real-time)

API Endpoints Used (per https://doodstream.com/api-docs):
- Folder List: GET https://doodapi.co/api/folder/list?key={key}&fld_id={folder_id}
  Response: {"msg": "OK", "result": {"folders": [{"name": "...", "code": "...", "fld_id": "..."}], "files": [...]}}
- Folder Create: GET https://doodapi.co/api/folder/create?key={key}&name={name}&parent_id={parent_id}
  Response: {"msg": "OK", "result": {"fld_id": "1234567"}}
- File Rename: GET https://doodapi.co/api/file/rename?key={key}&file_code={code}&title={title}
  Response: {"msg": "OK"}
- File Move: GET https://doodapi.co/api/file/move?key={key}&file_code={code}&fld_id={folder_id}
  Response: {"msg": "OK"}
- File Clone: GET https://doodapi.co/api/file/clone?key={key}&file_code={code}&fld_id={folder_id}
  Response: {"msg": "OK"}

Key Changes (Latest Update - v4.0):
1. Added 15-second delays between ALL API requests (per DoodStream API docs requirement)
2. Fixed API endpoints from doodapi.com to doodapi.co (correct domain)
3. Updated folder list API to use /api/folder/list instead of /api/list_folders
4. Updated response parsing to handle {"result": {"folders": [...]}} structure
5. Changed folder create parameter from 'parent' to 'parent_id' (correct API param)
6. Added strict folder structure requirement - upload aborts if folders can't be created
7. Added cleanup logic to delete files if they can't be moved to correct folder

Workflow with Rate Limiting:
1. Create Category Folder → Wait 15s
2. Create Series Folder → Wait 15s
3. Upload Video → Wait 15s
4. Rename File → Wait 15s
5. Move to Folder → Wait 15s
6. Complete
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
TEMP_FOLDER = "/content/temp_videos"  # Local temp folder (NOT Google Drive)
PROCESSED_FILE = "/content/processed_videos.json"

# Track which videos we've already created rows for in this session
session_processed_rows = set()

# ==================== INITIALIZATION ====================
print("=" * 60)
print("🚀 Video Processing Pipeline - REAL-TIME UPDATES")
print("=" * 60)

# Install required packages (Google Colab magic command)
print("\n📦 Installing dependencies...")
import subprocess
subprocess.run(["pip", "install", "-q", "requests", "beautifulsoup4", "tqdm", "doodstream", "gspread", "oauth2client"], check=True)

# Initialize DoodStream
dood = DoodStream(DOODSTREAM_API_KEY)

# Setup Google Drive (only needed for Sheets auth, not for video storage)
print("\n🔐 Authenticating with Google...")
try:
    drive.mount("/content/drive", force_remount=False)
except Exception as e:
    print(f"Drive already mounted: {e}")

# Create local temp folder (NOT in Google Drive)
os.makedirs(TEMP_FOLDER, exist_ok=True)
print(f"📁 Local temp folder ready: {TEMP_FOLDER}")

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
    # Note: drive_service is only used for Google Sheets auth, not for video storage
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

def upload_to_google_drive(file_path, title, series_name=None):
    """Upload file to Google Drive and return file ID"""
    global drive_service
    
    try:
        if not drive_service:
            init_sheet()
        
        if not drive_service:
            print("❌ Cannot connect to Google Drive")
            return None
        
        # Find or create series folder in MyDrive
        parent_id = ''  # Root of MyDrive
        if series_name:
            try:
                # Search for series folder
                query = f"name='{series_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                result = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                files = result.get('files', [])
                
                if files:
                    parent_id = files[0].get('id')
                    print(f"   📁 Using series folder: {series_name}")
                else:
                    # Create series folder
                    folder_metadata = {
                        'name': series_name,
                        'mimeType': 'application/vnd.google-apps.folder'
                    }
                    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                    parent_id = folder.get('id')
                    print(f"   📁 Created series folder: {series_name}")
            except Exception as e:
                print(f"   ⚠️ Folder error: {e}")
                parent_id = ''  # Fallback to root if folder creation fails
        
        # File metadata - use root if parent_id is empty string
        file_metadata = {
            'name': f"[TEMP] {title}",
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
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
    """Download video with single-line progress bar"""
    filepath = os.path.join(TEMP_FOLDER, filename)
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        # Use a single-line progress bar that updates in place
        with open(filepath, 'wb') as f, tqdm(
            desc=f"⬇️ {filename[:30]}",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            bar_format='{l_bar}{bar}| {n:.1f}/{total_fmt} [{remaining}, {rate_fmt}]',
            mininterval=0.5,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        # Verify download
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1024 * 1024:  # > 1MB
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"\n   ✅ Download successful! Size: {size_mb:.2f} MB")
            return filepath
        else:
            print(f"\n   ❌ Download failed: File too small")
            if os.path.exists(filepath):
                os.remove(filepath)
            return None
            
    except Exception as e:
        print(f"\n   ❌ Download error: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return None

# ==================== DOODSTREAM FUNCTIONS ====================
def get_or_create_folder_structure(series_name):
    """Create Category -> Series folder structure on DoodStream
    
    API Endpoints (per https://doodstream.com/api-docs):
    - Create: GET https://doodapi.co/api/folder/create?key={key}&name={name}&parent_id={parent_id}
      Response: {"msg": "OK", "result": {"fld_id": "1234567"}}
    - List: GET https://doodapi.co/api/folder/list?key={key}&fld_id={folder_id}&only_folders=1
      Response: {"msg": "OK", "result": {"folders": [{"name": "...", "code": "...", "fld_id": "..."}], "files": [...]}}
    
    IMPORTANT: 15 second delay required between API requests per DoodStream API docs
    """
    
    # Step 1: Find or create Category folder in root
    category_folder_id = None
    try:
        # List folders in root (fld_id parameter is required, use empty or omit for root)
        list_url = f"https://doodapi.co/api/folder/list?key={DOODSTREAM_API_KEY}"
        try:
            response = requests.get(list_url, timeout=10)
            response.raise_for_status()
            result_data = response.json().get('result', {})
            folders = result_data.get('folders', []) if isinstance(result_data, dict) else []
        except Exception as list_err:
            print(f"⚠️ List folders API error: {list_err}")
            folders = []
        
        for item in folders:
            if item.get('name') == CATEGORY_NAME:
                category_folder_id = item.get('fld_id') or item.get('code')
                print(f"📁 Found category folder: {CATEGORY_NAME} (ID: {category_folder_id})")
                break
        
        if not category_folder_id:
            print(f"📁 Creating category folder: {CATEGORY_NAME}")
            # Create folder in root (no parent_id needed)
            create_url = f"https://doodapi.co/api/folder/create?key={DOODSTREAM_API_KEY}&name={requests.utils.quote(CATEGORY_NAME)}"
            result = requests.get(create_url, timeout=15).json()
            
            # 15 second delay after create request
            time.sleep(15)
            
            if result and result.get('msg') == 'OK':
                res_data = result.get('result', {})
                if isinstance(res_data, dict):
                    category_folder_id = res_data.get('fld_id')
                
                if category_folder_id:
                    print(f"✅ Created category folder: {CATEGORY_NAME} (ID: {category_folder_id})")
            
            if not category_folder_id:
                # Try to find it in the list anyway
                try:
                    response = requests.get(list_url, timeout=10)
                    response.raise_for_status()
                    result_data = response.json().get('result', {})
                    folders = result_data.get('folders', []) if isinstance(result_data, dict) else []
                    for item in folders:
                        if item.get('name') == CATEGORY_NAME:
                            category_folder_id = item.get('fld_id') or item.get('code')
                            break
                except:
                    pass
    except Exception as e:
        print(f"⚠️ Category folder error: {e}")
    
    # Step 2: Find or create Series folder inside Category
    series_folder_id = None
    if category_folder_id:
        try:
            # List files/folders in category folder
            list_url = f"https://doodapi.co/api/folder/list?key={DOODSTREAM_API_KEY}&fld_id={category_folder_id}"
            try:
                response = requests.get(list_url, timeout=10)
                response.raise_for_status()
                result_data = response.json().get('result', {})
                series_folders = result_data.get('folders', []) if isinstance(result_data, dict) else []
            except Exception as list_err:
                print(f"⚠️ List series folders API error: {list_err}")
                series_folders = []
            
            for item in series_folders:
                if item.get('name') == series_name:
                    series_folder_id = item.get('fld_id') or item.get('code')
                    print(f"📁 Found series folder: {series_name} (ID: {series_folder_id})")
                    break
            
            if not series_folder_id:
                print(f"📁 Creating series folder: {series_name}")
                # Create folder inside category folder with parent_id
                create_url = f"https://doodapi.co/api/folder/create?key={DOODSTREAM_API_KEY}&name={requests.utils.quote(series_name)}&parent_id={category_folder_id}"
                result = requests.get(create_url, timeout=15)
                result.raise_for_status()
                result_json = result.json()
                
                # 15 second delay after create request
                time.sleep(15)
                
                print(f"   📋 Create folder response: {result_json}")
                
                if result_json and result_json.get('msg') == 'OK':
                    res_data = result_json.get('result', {})
                    if isinstance(res_data, dict):
                        series_folder_id = res_data.get('fld_id')
                    
                    if series_folder_id:
                        print(f"✅ Created series folder: {series_name} (ID: {series_folder_id})")
                
                if not series_folder_id:
                    # Try to find it anyway
                    try:
                        response = requests.get(list_url, timeout=10)
                        response.raise_for_status()
                        result_data = response.json().get('result', {})
                        series_folders = result_data.get('folders', []) if isinstance(result_data, dict) else []
                        for item in series_folders:
                            if item.get('name') == series_name:
                                series_folder_id = item.get('fld_id') or item.get('code')
                                break
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ Series folder error: {e}")
    
    return category_folder_id, series_folder_id

def upload_to_doodstream(file_path, series_name, video_title):
    """Upload video to DoodStream in correct folder structure: Category > Series > Video
    
    API Endpoints (per https://doodstream.com/api-docs):
    - Upload: Uses doodstream library local_upload (uploads to root)
    - Rename: GET https://doodapi.co/api/file/rename?key={key}&file_code={code}&title={title}
    - Move: GET https://doodapi.co/api/file/move?key={key}&file_code={code}&fld_id={folder_id}
    
    IMPORTANT: If folder structure cannot be created, DO NOT upload the video.
    The video MUST be placed in the correct folder structure.
    IMPORTANT: 15 second delay required between API requests per DoodStream API docs
    """
    
    # Step 0: Create/get folder structure FIRST - must succeed before upload
    print(f"📁 Ensuring folder structure exists: {CATEGORY_NAME} > {series_name}")
    cat_folder_id, series_folder_id = get_or_create_folder_structure(series_name)
    target_folder_id = series_folder_id if series_folder_id else cat_folder_id
    
    # CRITICAL: If we can't create the folder structure, abort upload
    if not target_folder_id:
        print("❌ ERROR: Could not create folder structure. Aborting upload.")
        print("   The video MUST be placed in: Ramadan 2026 - مسلسلات > [Series Name]")
        return None
    
    try:
        print(f"⬆️ Uploading to DoodStream...")
        
        # Clean the title first: remove .mp4 extension and extra spaces
        clean_title = video_title.replace('.mp4', '').strip()
        clean_title = ' '.join(clean_title.split())
        
        # Step 1: Upload to root (library doesn't support folder upload directly)
        result = dood.local_upload(file_path)
        
        if not result:
            print("❌ Upload failed: No response from DoodStream")
            return None
        
        # Step 2: Extract file_code from response (handle all formats)
        file_code = None
        
        # Format 1: {'result': [{'filecode': '...', ...}], ...}
        if isinstance(result, dict) and 'result' in result:
            res_data = result['result']
            if isinstance(res_data, list) and len(res_data) > 0:
                file_code = res_data[0].get('filecode')
            elif isinstance(res_data, dict):
                file_code = res_data.get('filecode')
        # Format 2: [{'filecode': '...', ...}]
        elif isinstance(result, list) and len(result) > 0:
            file_code = result[0].get('filecode')
        # Format 3: {'filecode': '...', ...}
        elif isinstance(result, dict):
            file_code = result.get('filecode')
        
        if not file_code:
            print(f"❌ Could not get file code from upload. Response: {result}")
            return None
        
        print(f"✅ Uploaded to root! File code: {file_code}")
        
        # 15 second delay after upload
        time.sleep(15)
        
        # Step 3: Rename file to proper title
        try:
            rename_url = f"https://doodapi.co/api/file/rename?key={DOODSTREAM_API_KEY}&file_code={file_code}&title={requests.utils.quote(clean_title)}"
            rename_resp = requests.get(rename_url, timeout=10).json()
            
            # 15 second delay after rename
            time.sleep(15)
            
            if rename_resp.get('msg') == 'OK':
                print(f"✅ Renamed file to: {clean_title}")
            else:
                print(f"⚠️ Rename response: {rename_resp}")
        except Exception as e:
            print(f"⚠️ Could not rename file: {e}")
        
        # Step 4: Move to series folder using API (move directly instead of clone+delete)
        # This is REQUIRED - video must be in correct folder
        print(f"📁 Moving to folder: {series_name} (ID: {target_folder_id})")
        
        move_url = f"https://doodapi.co/api/file/move?key={DOODSTREAM_API_KEY}&file_code={file_code}&fld_id={target_folder_id}"
        move_resp = requests.get(move_url, timeout=15).json()
        
        # 15 second delay after move
        time.sleep(15)
        
        if move_resp.get('msg') == 'OK':
            print(f"✅ Moved to folder successfully")
        else:
            print(f"⚠️ Move to folder response: {move_resp}")
            # Fallback: Try clone + delete if move fails
            try:
                copy_url = f"https://doodapi.co/api/file/clone?key={DOODSTREAM_API_KEY}&file_code={file_code}&fld_id={target_folder_id}"
                copy_resp = requests.get(copy_url, timeout=15).json()
                
                # 15 second delay after clone
                time.sleep(15)
                
                if copy_resp.get('msg') == 'OK':
                    print(f"✅ Copied to folder (fallback method)")
                    delete_result = dood.delete_file([file_code])
                    if delete_result and delete_result.get('msg') == 'OK':
                        print(f"✅ Deleted original from root")
                else:
                    print(f"❌ CRITICAL: Could not move file to folder. Upload aborted.")
                    # Delete the uploaded file since it's in wrong location
                    dood.delete_file([file_code])
                    return None
            except Exception as fallback_err:
                print(f"⚠️ Fallback also failed: {fallback_err}")
                print(f"❌ CRITICAL: Could not place file in correct folder. Deleting uploaded file.")
                dood.delete_file([file_code])
                return None
        
        # Build final URLs
        watch_url = f"https://dsvplay.com/e/{file_code}"
        download_url = f"https://dsvplay.com/d/{file_code}"
        
        print(f"✅ Upload complete!")
        print(f"   👁️ Watch: {watch_url}")
        print(f"   ⬇️ Download: {download_url}")
        
        return {
            'filecode': file_code,
            'watch_url': watch_url,
            'download_url': download_url,
            'title': clean_title
        }
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_doodstream_links(file_code):
    """Get watch and download links from DoodStream - returns clean URLs only"""
    # Construct clean URLs directly without using library that returns JSON
    watch_link = f"https://doodstream.com/d/{file_code}"
    dl_link = f"https://doodstream.com/download/{file_code}"
    
    return {
        'file_code': file_code,
        'watch_link': watch_link,
        'download_link': dl_link
    }

def delete_from_google_drive(drive_file_id):
    """Delete file from Google Drive"""
    global drive_service
    
    if not drive_file_id:
        return False
    
    try:
        if not drive_service:
            init_sheet()
        
        if not drive_service:
            print("   ⚠️ Cannot connect to Google Drive for deletion")
            return False
        
        print(f"   🗑️ Deleting temp file from Google Drive...")
        drive_service.files().delete(fileId=drive_file_id).execute()
        print(f"   ✅ Temp file deleted from Drive!")
        return True
        
    except Exception as del_err:
        print(f"   ⚠️ Warning: Could not delete temp file: {del_err}")
        return False

# ==================== GOOGLE SHEETS UPDATE ====================
def get_existing_video_row(video_id):
    """Check if video already exists in sheet and return row number"""
    global sheet, service
    
    try:
        if not service:
            init_sheet()
        
        if not service:
            return None
        
        # Get all data from sheet
        result = sheet.values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range='Sheet1!A:I'
        ).execute()
        
        values = result.get('values', [])
        
        # Skip header row (index 0), start from row 2 (index 1)
        for idx, row in enumerate(values[1:], start=2):
            if len(row) >= 3 and row[2] == video_id:  # Column C is Video ID
                return idx
        
        return None
        
    except Exception as e:
        print(f"⚠️ Error checking existing row: {e}")
        return None

def update_sheet_realtime(video_data, status="Processing", is_final=False):
    """Update Google Sheet IMMEDIATELY after each video - updates existing row or creates new one"""
    global sheet, service, session_processed_rows
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if not service:
                init_sheet()
            
            if not service:
                print("⚠️ Cannot connect to Google Sheets")
                return False
            
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            video_id = video_data.get('video_id', '')
            
            # Check if this video already has a row in the sheet
            existing_row = get_existing_video_row(video_id)
            
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
            
            if existing_row:
                # Update existing row instead of creating duplicate
                range_name = f'Sheet1!A{existing_row}:I{existing_row}'
                sheet.values().update(
                    spreadsheetId=GOOGLE_SHEET_ID,
                    range=range_name,
                    valueInputOption='RAW',
                    body={'values': [row_data]}
                ).execute()
                print(f"✅ REAL-TIME UPDATE: Row {existing_row} updated in Google Sheet")
            else:
                # Only add new row for initial "Starting" status or final status
                # Don't create duplicate rows for intermediate statuses
                if status != "⏳ Starting" and status != "✅ Success" and not status.startswith("❌"):
                    return True  # Skip intermediate status updates
                
                sheet.values().append(
                    spreadsheetId=GOOGLE_SHEET_ID,
                    range='Sheet1!A:I',
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body={'values': [row_data]}
                ).execute()
                print(f"✅ REAL-TIME UPDATE: New row added to Google Sheet")
            
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
    
    # Step 3: Download video to local temp folder (NOT Google Drive)
    safe_filename = f"{video_info['video_id']}_{video_data['series_name']}.mp4"
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in (' ', '.', '_')).strip()
    safe_filename = safe_filename.replace(' ', '_')[:100] + ".mp4"
    
    print(f"   📥 Downloading video to temp folder...")
    downloaded_path = download_video(video_url, safe_filename)
    
    if not downloaded_path:
        update_sheet_realtime(video_data, status="❌ Download failed")
        return False
    
    # Step 4: Upload to DoodStream (directly from local temp file)
    print(f"   ⬆️ Uploading to DoodStream...")
    file_code = upload_to_doodstream(
        downloaded_path, 
        video_data['series_name'], 
        video_info['title']
    )
    
    # Cleanup local temp file AFTER DoodStream upload
    try:
        if os.path.exists(downloaded_path):
            os.remove(downloaded_path)
            print("   🗑️ Local temp file deleted")
    except:
        pass
    
    if not file_code:
        update_sheet_realtime(video_data, status="❌ DoodStream upload failed")
        return False
    
    # Get watch and download links
    links = get_doodstream_links(file_code)
    video_data['dood_watch'] = links['watch_link']
    video_data['dood_download'] = links['download_link']
    
    # Step 5: FINAL UPDATE - Success
    update_sheet_realtime(video_data, status="✅ Success")
    
    # Save progress
    save_processed_video(video_info['video_id'])
    
    print(f"   🎉 COMPLETED!")
    print(f"   📺 Watch: {links['watch_link']}")
    print(f"   ⬇️ Download: {links['download_link']}")
    
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
