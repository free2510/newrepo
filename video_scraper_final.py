# ╔════════════════════════════════════════════════════════════════════╗
# ║  🎬 VIDEO SCRAPER - LAROZAA → GDRIVE → DOODSTREAM [FINAL FIXED]   ║
# ╚════════════════════════════════════════════════════════════════════╝

# 📦 INSTALL DEPENDENCIES
print("📦 Installing dependencies...")
!pip install -q requests beautifulsoup4 lxml gspread pandas tqdm selenium webdriver-manager
!pip install -q google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

import requests, re, time, os, sys, logging, json
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
from urllib.parse import urlparse, parse_qs, unquote, urljoin
import warnings
warnings.filterwarnings('ignore')

# Google Auth & Drive
from google.colab import auth, drive
import gspread
from google.auth import default
from googleapiclient.discovery import build

# Selenium for JavaScript rendering
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure encoding for Arabic support
logging.getLogger('google_auth_httplib2').setLevel(logging.ERROR)
requests.packages.urllib3.disable_warnings()

# ═══════════════════════════════════════════════════════════════════
# ⚙️ CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

CONFIG = {
    'BASE_URL': 'https://larozaa.yachts',
    'CATEGORY_URL': 'https://larozaa.yachts/category.php?cat=ramadan-2026',
    
    # CSS Selectors (updated based on your HTML)
    'VIDEO_LIST_SELECTOR': 'div.pm-video-thumb > a',
    'WATCH_SERVERS_SELECTOR': 'ul.WatchList > li[data-embed-url]',
    
    # Google Sheet - YOUR SHEET ID
    'SHEET_ID': '1h4WDPuxUaDreza60h8VjcMLqnbKleWXw9AfMCpjfnnI',
    'SHEET_NAME': 'Sheet1',
    
    # Google Drive Temp Folder
    'DRIVE_TEMP_FOLDER': '/content/drive/MyDrive/VideoTemp',
    
    # DoodStream API
    'DOOD_API_KEY': '566462d6434dlvqu6fmesc',
    'SERIES_FOLDER_NAME': 'رمضان 2026 - مسلسلات',
    
    # Video Validation Settings
    'MIN_FILE_SIZE_MB': 5,
    'MAX_FILE_SIZE_MB': 2000,
    'VERIFY_CONTENT_TYPE': True,
    'VERIFY_MAGIC_BYTES': True,
    'VIDEO_EXTENSIONS': ['.mp4', '.m3u8', '.mkv', '.avi', '.mov', '.flv'],
    
    # Process Control
    'MAX_VIDEOS': 5,  # Start with 5 for testing
    'DOWNLOAD_VIDEO': True,
    'UPLOAD_TO_DOOD': True,
    'TEST_ALL_SERVERS': True,
    'REQUEST_DELAY': 2,
    'SERVER_TIMEOUT': 30,
    'DOWNLOAD_TIMEOUT': 900,
    
    # Selenium settings
    'USE_SELENIUM': True,
    'SELENIUM_TIMEOUT': 30
}

# Create temp folder
os.makedirs(CONFIG['DRIVE_TEMP_FOLDER'], exist_ok=True)

# ═══════════════════════════════════════════════════════════════════
# 🔧 HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def extract_video_id(url):
    """Extract video ID from URL"""
    parsed = parse_qs(urlparse(url).query)
    return parsed.get('vid', [None])[0]

def get_headers(referer=None):
    """Return headers to avoid blocking"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': referer or CONFIG['BASE_URL'],
        'Origin': CONFIG['BASE_URL'],
    }
    return headers

def is_video_content_type(content_type):
    """Check if content type is video"""
    if not content_type:
        return False
    video_types = ['video/', 'application/octet-stream', 'application/x-mpegURL']
    return any(vt in content_type.lower() for vt in video_types)

def check_magic_bytes(filepath):
    """Check magic bytes to verify file is video"""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
        if len(header) < 4:
            return False
        # MP4/M4V: ftyp
        if header[4:8] == b'ftyp':
            return True
        # MKV/WebM: 1A 45 DF A3
        if header[:4] == b'\x1a\x45\xdf\xa3':
            return True
        # AVI: RIFF....AVI
        if header[0:4] == b'RIFF' and header[8:12] == b'AVI ':
            return True
        # MOV: moov or free
        if b'moov' in header or b'free' in header:
            return True
        # M3U8: #EXTM3U
        if header[:7] == b'#EXTM3U':
            return True
        # FLV: FLV\x01
        if header[:4] == b'FLV\x01':
            return True
        return False
    except:
        return False

def get_file_size_mb(filepath):
    """Get file size in MB"""
    try:
        return os.path.getsize(filepath) / (1024 * 1024)
    except:
        return 0

def init_selenium():
    """Initialize Selenium WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(CONFIG['SELENIUM_TIMEOUT'])
    return driver

def extract_direct_video_url_with_selenium(embed_url, play_link=None):
    """Extract direct video URL using Selenium to render JavaScript"""
    driver = None
    try:
        print(f"   🌐 Using Selenium to load: {embed_url[:60]}...")
        
        driver = init_selenium()
        driver.get(embed_url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Try to find video element
        try:
            video_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
            src = video_element.get_attribute('src')
            if src and src.startswith('http'):
                print(f"   ✅ Found video source: {src[:80]}...")
                return src
        except:
            pass
        
        # Try to find iframe
        try:
            iframe = driver.find_element(By.TAG_NAME, "iframe")
            iframe_src = iframe.get_attribute('src')
            if iframe_src:
                print(f"   📺 Found iframe: {iframe_src[:80]}...")
                # Recursively try the iframe URL
                if iframe_src != embed_url:
                    return extract_direct_video_url_with_selenium(iframe_src, play_link)
        except:
            pass
        
        # Try to extract from page source
        page_source = driver.page_source
        
        # Look for common video URL patterns
        patterns = [
            r'["\']?(https?://[^\s\'"]+?\.(?:mp4|m3u8|mkv|avi|mov|flv)[^\s\'"]*)["\']?',
            r'(?:file|src|source)["\']?\s*[:=]\s*["\']([^"\']+?\.(?:mp4|m3u8|mkv|avi|mov|flv)[^"\']*)["\']',
            r'https?://[^\s]+?/master\.m3u8[^\s]*',
            r'https?://[^\s]+?/playlist\.m3u8[^\s]*',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, page_source, re.I)
            for match in matches:
                url = match.group(1).strip()
                if url.startswith('//'):
                    url = 'https:' + url
                if any(ext in url.lower() for ext in CONFIG['VIDEO_EXTENSIONS']):
                    print(f"   ✅ Extracted from pattern: {url[:80]}...")
                    return url
        
        # If embed URL itself looks like a video URL
        if any(ext in embed_url.lower() for ext in CONFIG['VIDEO_EXTENSIONS']):
            return embed_url
            
        print(f"   ⚠️ Could not extract direct URL")
        return None
        
    except Exception as e:
        print(f"   ⚠️ Selenium error: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def extract_direct_video_url(embed_url, play_link=None):
    """Extract direct video URL from embed page"""
    # First try with Selenium (more reliable for JS-heavy sites)
    if CONFIG['USE_SELENIUM']:
        direct_url = extract_direct_video_url_with_selenium(embed_url, play_link)
        if direct_url:
            return direct_url
    
    # Fallback to requests method
    headers = get_headers(referer=play_link or CONFIG['BASE_URL'])
    try:
        resp = requests.get(embed_url, headers=headers, timeout=CONFIG['SERVER_TIMEOUT'], allow_redirects=True)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'lxml')

        # 1. Look for <video> tag
        video_tag = soup.find('video')
        if video_tag:
            src = video_tag.get('src')
            if not src:
                source = video_tag.find('source')
                src = source.get('src') if source else None
            if src:
                return src if src.startswith('http') else urljoin(embed_url, src)

        # 2. Look for common patterns in JavaScript
        patterns = [
            r'["\']?(https?://[^\s\'"]+?\.(?:mp4|m3u8|mkv|avi|mov|flv)[^\s\'"]*)["\']?',
            r'(?:file|src|source)["\']?\s*[:=]\s*["\']([^"\']+?\.(?:mp4|m3u8|mkv|avi|mov|flv)[^"\']*)["\']',
        ]
        for pattern in patterns:
            matches = re.finditer(pattern, resp.text, re.I)
            for match in matches:
                url = match.group(1).strip()
                if url.startswith('//'):
                    url = 'https:' + url
                if any(ext in url.lower() for ext in CONFIG['VIDEO_EXTENSIONS']):
                    return url

        # 3. If URL itself looks like video URL
        if any(ext in embed_url.lower() for ext in CONFIG['VIDEO_EXTENSIONS']):
            return embed_url

        return None
    except Exception as e:
        print(f"⚠️ Error extracting URL: {e}")
        return None

def get_video_list(category_url):
    """Get list of videos from category page"""
    headers = get_headers()
    response = requests.get(category_url, headers=headers, timeout=30)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')

    videos = []
    for elem in soup.select(CONFIG['VIDEO_LIST_SELECTOR']):
        href = elem.get('href', '')
        title = elem.get('title', '').strip() or elem.get_text(strip=True)
        vid = extract_video_id(href)

        if vid and title:
            series_name = title.split('الحلقة')[0].strip() if 'الحلقة' in title else title
            videos.append({
                'video_id': vid,
                'title': title,
                'series_name': series_name,
                'category_link': href if href.startswith('http') else urljoin(CONFIG['BASE_URL'], href),
                'play_link': f"{CONFIG['BASE_URL']}/play.php?vid={vid}",
                'server_name': None,
                'server_url': None,
                'direct_video_url': None,
                'drive_link': None,
                'dood_watch': None,
                'dood_download': None,
                'dood_filecode': None,
                'download_size_mb': 0,
                'status': 'Pending',
                'error': None,
                'notes': ''
            })
    return videos

def get_watch_servers(play_link):
    """Get all watch servers from play page"""
    headers = get_headers(referer=play_link)
    servers = []
    try:
        response = requests.get(play_link, headers=headers, timeout=25)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')

        for elem in soup.select(CONFIG['WATCH_SERVERS_SELECTOR']):
            embed_url = elem.get('data-embed-url', '').strip()
            name = elem.get_text(strip=True) or f"سيرفر {len(servers)+1}"
            if embed_url and name:
                servers.append({
                    'name': name,
                    'url': embed_url,
                    'tested': False,
                    'working': None
                })
        print(f"   🔍 Found {len(servers)} servers")
    except Exception as e:
        print(f"⚠️ Error getting servers: {e}")
    return servers

def test_server_working(embed_url, play_link, timeout=20):
    """Test if server is working"""
    try:
        headers = get_headers(referer=play_link)
        
        # Test accessibility
        try:
            resp = requests.head(embed_url, headers=headers, timeout=timeout, allow_redirects=True)
            if resp.status_code >= 400:
                resp = requests.get(embed_url, headers=headers, timeout=timeout, stream=True)
                resp.close()
        except:
            pass
        
        # Try to extract direct URL
        direct_url = extract_direct_video_url(embed_url, play_link)
        
        if direct_url:
            # Test the direct URL
            try:
                r = requests.head(direct_url, headers=headers, timeout=10, allow_redirects=True)
                if r.status_code < 400:
                    content_type = r.headers.get('Content-Type', '')
                    size = r.headers.get('Content-Length')
                    
                    # Check if it's video content
                    if size:
                        size_mb = int(size) / (1024*1024)
                        if size_mb < CONFIG['MIN_FILE_SIZE_MB']:
                            return False, None, f"Size too small: {size_mb:.2f}MB"
                    
                    return True, direct_url, None
            except:
                pass
            return True, direct_url, None
        
        # If we can access the embed page, consider it working
        return True, embed_url, None
    except Exception as e:
        return False, None, str(e)

def download_video_to_drive(video_url, filename, folder_path, play_link=None):
    """Download video to Google Drive with validation"""
    filepath = os.path.join(folder_path, filename)
    headers = get_headers(referer=play_link or CONFIG['BASE_URL'])

    try:
        print(f"   📥 Starting download: {filename[:40]}...")

        with requests.get(video_url, headers=headers, stream=True, timeout=CONFIG['DOWNLOAD_TIMEOUT']) as r:
            r.raise_for_status()

            # Check content type
            content_type = r.headers.get('Content-Type', '')
            if CONFIG['VERIFY_CONTENT_TYPE'] and not is_video_content_type(content_type):
                print(f"   ⚠️ Warning: Content-Type: {content_type}")

            total = int(r.headers.get('content-length', 0))

            # Initial size check
            if total > 0:
                total_mb = total / (1024*1024)
                print(f"   📏 Expected size: {total_mb:.2f} MB")
                if total_mb < CONFIG['MIN_FILE_SIZE_MB']:
                    return None, f"File too small: {total_mb:.2f}MB"
                if total_mb > CONFIG['MAX_FILE_SIZE_MB']:
                    return None, f"File too large: {total_mb:.2f}MB"

            # Download
            downloaded = 0
            with open(filepath, 'wb') as f:
                with tqdm(total=total if total > 0 else None, unit='B', unit_scale=True,
                         desc=f"   ⬇️ {filename[:30]}") as pbar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            pbar.update(len(chunk))

            # Final validation
            actual_size_mb = get_file_size_mb(filepath)
            print(f"   📦 Actual size: {actual_size_mb:.2f} MB")

            if actual_size_mb < CONFIG['MIN_FILE_SIZE_MB']:
                os.remove(filepath)
                return None, f"Downloaded file too small: {actual_size_mb:.2f}MB"

            if actual_size_mb > CONFIG['MAX_FILE_SIZE_MB']:
                os.remove(filepath)
                return None, f"Downloaded file too large: {actual_size_mb:.2f}MB"

            # Magic bytes check
            if CONFIG['VERIFY_MAGIC_BYTES']:
                if not check_magic_bytes(filepath):
                    _, ext = os.path.splitext(filename)
                    if ext.lower() not in CONFIG['VIDEO_EXTENSIONS']:
                        os.remove(filepath)
                        return None, "File failed magic bytes check"

            print(f"   ✅ Download successful!")
            return filepath, None

    except requests.exceptions.Timeout:
        print(f"   ❌ Download timeout")
        if os.path.exists(filepath):
            os.remove(filepath)
        return None, "Download timeout"
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Network error: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return None, f"Network error: {str(e)}"
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return None, f"Unexpected error: {str(e)}"

def upload_file_to_gdrive(file_path, folder_name=None):
    """Upload file to Google Drive and get shareable link"""
    try:
        # Authenticate
        auth.authenticate_user()
        creds, _ = default()
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Get file metadata
        file_metadata = {'name': os.path.basename(file_path)}
        
        if folder_name:
            # Find or create folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
            else:
                folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
                folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                folder_id = folder.get('id')
            
            file_metadata['parents'] = [folder_id]
        
        # Upload file
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        # Make file publicly accessible
        drive_service.permissions().create(fileId=file['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
        
        # Get shareable link
        file_info = drive_service.files().get(fileId=file['id'], fields='webViewLink, webContentLink').execute()
        
        print(f"   ✅ Uploaded to Drive: {file_info.get('webViewLink')}")
        return file_info.get('webViewLink')
        
    except Exception as e:
        print(f"   ⚠️ Drive upload error: {e}")
        return None

# Import for Drive upload
from googleapiclient.http import MediaFileUpload

def create_dood_folder(api_key, folder_name, parent_id=None):
    """Create folder on DoodStream"""
    try:
        params = {'key': api_key, 'name': folder_name}
        if parent_id:
            params['parent_id'] = parent_id

        resp = requests.get("https://doodapi.co/api/folder/create", params=params, timeout=20)
        result = resp.json()

        if result.get('status') == 200:
            return result['result'].get('fld_id')

        # If folder exists, find it
        if 'already exists' in result.get('msg', '').lower() or result.get('status') == 400:
            print(f"📁 Folder '{folder_name}' exists, searching...")
            list_resp = requests.get("https://doodapi.co/api/folder/list", 
                                   params={'key': api_key}, timeout=20)
            list_result = list_resp.json()
            if list_result.get('status') == 200:
                folders = list_result.get('result', [])
                for fld in folders:
                    if fld.get('name') == folder_name:
                        print(f"✅ Found folder: {folder_name} (ID: {fld.get('fld_id')})")
                        return fld.get('fld_id')

        print(f"⚠️ Folder creation error: {result.get('msg')}")
        return None
    except Exception as e:
        print(f"⚠️ Folder creation exception: {e}")
        return None


def upload_to_doodstream_remote(api_key, video_url, folder_id=None, title=None):
    """Upload to DoodStream using remote URL"""
    try:
        params = {
            'key': api_key,
            'url': video_url,
        }
        if folder_id:
            params['fld_id'] = folder_id
        if title:
            params['new_title'] = title

        print(f"   📡 Sending remote upload request...")
        resp = requests.get("https://doodapi.co/api/upload/url", 
                          params=params, 
                          timeout=120)
        result = resp.json()

        print(f"   📡 Remote upload response: status={result.get('status')}, msg={result.get('msg')}")

        if result.get('status') == 200:
            filecode = result['result'].get('filecode')
            if filecode:
                return {
                    'watch': f"https://doodstream.com/e/{filecode}",
                    'download': f"https://doodstream.com/d/{filecode}",
                    'filecode': filecode
                }
        else:
            print(f"⚠️ Remote upload error: {result.get('msg')}")
        return None
    except Exception as e:
        print(f"⚠️ Remote upload exception: {e}")
        return None


def upload_to_doodstream_local(api_key, file_path, folder_id=None, title=None):
    """Upload to DoodStream using local file"""
    try:
        # Step 1: Get upload server
        print(f"   🔄 [1/2] Getting upload server from DoodStream...")
        resp = requests.get(f"https://doodapi.co/api/upload/server?key={api_key}", timeout=20)
        server_result = resp.json()

        if server_result.get('status') != 200:
            print(f"⚠️ Failed to get upload server: {server_result.get('msg')}")
            return None

        upload_server = server_result['result']
        print(f"   📡 Upload server: {upload_server[:60]}...")

        # Step 2: Upload file
        print(f"   🔄 [2/2] Uploading file to server...")
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'video/mp4')}
            upload_url = f"{upload_server}?{api_key}"

            resp = requests.post(upload_url, files=files, timeout=600)
            result = resp.json()

        print(f"   📡 Local upload response: status={result.get('status')}, msg={result.get('msg')}")

        if result.get('status') == 200 and result.get('result'):
            file_info = result['result']
            if isinstance(file_info, list) and len(file_info) > 0:
                file_info = file_info[0]

            filecode = file_info.get('filecode')
            if filecode:
                return {
                    'watch': f"https://doodstream.com/e/{filecode}",
                    'download': f"https://doodstream.com/d/{filecode}",
                    'filecode': filecode
                }

        print(f"⚠️ Local upload failed: {result.get('msg', 'Unknown error')}")
        return None
    except Exception as e:
        print(f"⚠️ Local upload exception: {e}")
        import traceback
        traceback.print_exc()
        return None


def upload_to_doodstream(api_key, file_path=None, video_url=None, folder_id=None, title=None):
    """Unified upload function: tries remote first, then local"""
    # Try remote upload first
    if video_url and any(ext in video_url.lower() for ext in CONFIG['VIDEO_EXTENSIONS']):
        print(f"   ⬆️ Trying remote upload: {video_url[:70]}...")
        result = upload_to_doodstream_remote(api_key, video_url, folder_id, title)
        if result:
            print(f"   ✅ Remote upload successful!")
            return result
        else:
            print(f"   ⚠️ Remote upload failed, trying local...")

    # Try local upload
    if file_path and os.path.exists(file_path):
        print(f"   ⬆️ Trying local upload: {os.path.basename(file_path)}")
        result = upload_to_doodstream_local(api_key, file_path, folder_id, title)
        if result:
            print(f"   ✅ Local upload successful!")
            return result

    print(f"   ❌ All DoodStream upload methods failed")
    return None


def write_to_sheet(data_list, sheet_id, sheet_name):
    """Write data to Google Sheet"""
    try:
        sh = gc.open_by_key(sheet_id)
        try:
            worksheet = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=sheet_name, rows=2000, cols=16)

        headers = [
            'Title', 'Series', 'Video ID', 'Category Link', 'Play Link',
            'Server', 'Server URL', 'Direct Video URL',
            'Drive Link', 'Drive Size (MB)',
            'Dood Watch', 'Dood Download', 'Dood FileCode',
            'Status', 'Error', 'Notes'
        ]

        rows = [headers]
        for d in data_list:
            row = [
                d.get('title', ''),
                d.get('series_name', ''),
                d.get('video_id', ''),
                d.get('category_link', ''),
                d.get('play_link', ''),
                d.get('server_name', ''),
                d.get('server_url', ''),
                d.get('direct_video_url', ''),
                d.get('drive_link', ''),
                d.get('download_size_mb', 0),
                d.get('dood_watch', ''),
                d.get('dood_download', ''),
                d.get('dood_filecode', ''),
                d.get('status', ''),
                d.get('error', ''),
                d.get('notes', '')
            ]
            rows.append(row)

        worksheet.clear()
        worksheet.update('A1', rows)

        try:
            worksheet.columns_auto_resize(1, len(headers) + 1)
        except:
            pass

        print(f"✅ Updated sheet: {len(rows)-1} rows")
        return True
    except Exception as e:
        print(f"❌ Sheet error: {e}")
        import traceback
        traceback.print_exc()
        return False

# ═══════════════════════════════════════════════════════════════════
# 🚀 MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════

def run_pipeline():
    print(f"\n🔐 Authenticating with Google...")
    auth.authenticate_user()
    creds, _ = default()
    global gc
    gc = gspread.authorize(creds)
    drive.mount('/content/drive', force_remount=False)
    print("✅ Authentication + Drive ready")

    print(f"\n📥 Fetching videos from: {CONFIG['CATEGORY_URL']}")
    videos = get_video_list(CONFIG['CATEGORY_URL'])

    if CONFIG['MAX_VIDEOS']:
        videos = videos[:CONFIG['MAX_VIDEOS']]

    print(f"✅ Found {len(videos)} videos")

    # DoodStream folders
    main_folder_id = None
    series_folders = {}
    if CONFIG['UPLOAD_TO_DOOD']:
        main_folder_id = create_dood_folder(CONFIG['DOOD_API_KEY'], CONFIG['SERIES_FOLDER_NAME'])
        if main_folder_id:
            print(f"📁 Main DoodStream folder: {CONFIG['SERIES_FOLDER_NAME']} (ID: {main_folder_id})")

    results = []

    for i, v in enumerate(tqdm(videos, desc="🔄 Processing videos"), 1):
        print(f"\n{'='*60}")
        print(f"🎬 [{i}/{len(videos)}] {v['title']}")
        print(f"{'='*60}")
        time.sleep(CONFIG['REQUEST_DELAY'])

        # 1️⃣ Get servers
        servers = get_watch_servers(v['play_link'])
        if not servers:
            v['status'] = '❌ No Servers'
            v['error'] = 'No servers found'
            results.append(v)
            write_to_sheet(results, CONFIG['SHEET_ID'], CONFIG['SHEET_NAME'])
            continue

        # 2️⃣ Test all servers until we find one that works
        downloaded_path = None
        download_error = None
        used_server = None
        direct_url = None

        for srv_idx, srv in enumerate(servers, 1):
            print(f"\n   🧪 [{srv_idx}/{len(servers)}] Testing: {srv['name']}")

            is_working, direct_url, test_error = test_server_working(srv['url'], v['play_link'])
            srv['tested'] = True
            srv['working'] = is_working

            if not is_working:
                print(f"   ❌ Not working: {test_error}")
                continue

            print(f"   ✅ Server working, attempting download...")

            # Clean filename
            safe_title = re.sub(r'[^\w\u0600-\u06FF\-\.]', '_', v['title'][:50]).strip()
            filename = f"{v['video_id']}_{safe_title}.mp4"

            # Try download
            downloaded_path, dl_error = download_video_to_drive(
                direct_url or srv['url'],
                filename,
                CONFIG['DRIVE_TEMP_FOLDER'],
                play_link=v['play_link']
            )

            if downloaded_path:
                used_server = srv
                v['download_size_mb'] = round(get_file_size_mb(downloaded_path), 2)
                print(f"   🎉 Download successful! Size: {v['download_size_mb']} MB")
                break
            else:
                print(f"   ❌ Download failed from this server: {dl_error}")
                download_error = dl_error

        # 3️⃣ Process result
        if downloaded_path and used_server:
            v['server_name'] = used_server['name']
            v['server_url'] = used_server['url']
            v['direct_video_url'] = direct_url or used_server['url']
            
            # Upload to Google Drive
            print(f"   ☁️ Uploading to Google Drive...")
            drive_link = upload_file_to_gdrive(downloaded_path, v['series_name'])
            v['drive_link'] = drive_link if drive_link else f"local:{downloaded_path}"
            v['status'] = '✅ Downloaded'

            # 4️⃣ Upload to DoodStream
            if CONFIG['UPLOAD_TO_DOOD']:
                series = v['series_name']
                if series not in series_folders:
                    folder_id = create_dood_folder(CONFIG['DOOD_API_KEY'], series, main_folder_id)
                    if folder_id:
                        series_folders[series] = folder_id
                        print(f"   📁 Series folder: {series[:30]}...")

                folder_id = series_folders.get(series) or main_folder_id

                print(f"   ⬆️ Uploading to DoodStream...")
                dood_result = upload_to_doodstream(
                    CONFIG['DOOD_API_KEY'],
                    file_path=downloaded_path,
                    video_url=v['direct_video_url'],
                    folder_id=folder_id,
                    title=v['title']
                )

                if dood_result:
                    v['dood_watch'] = dood_result['watch']
                    v['dood_download'] = dood_result['download']
                    v['dood_filecode'] = dood_result['filecode']
                    v['status'] = '✅ Uploaded to Dood'
                    print(f"   🎉 Uploaded to DoodStream!")
                else:
                    v['status'] = '⚠️ Dood Upload Failed'
                    v['error'] = 'Failed to upload to DoodStream'

                # Delete temp file
                if os.path.exists(downloaded_path):
                    try:
                        os.remove(downloaded_path)
                        print(f"   🗑️ Deleted temp file")
                    except:
                        pass
        else:
            v['status'] = '❌ Download Failed'
            v['error'] = f"All servers failed: {download_error or 'No working server'}"
            v['notes'] = f"Tried {len(servers)} servers"
            print(f"   ❌ Download failed from all servers")

        results.append(v)
        write_to_sheet(results, CONFIG['SHEET_ID'], CONFIG['SHEET_NAME'])

    # Final report
    print(f"\n{'='*60}")
    print("✨ Process complete!")
    print(f"{'='*60}")

    summary = {}
    for r in results:
        status = r['status']
        summary[status] = summary.get(status, 0) + 1

    for status, count in summary.items():
        print(f"• {status}: {count}")

    print(f"\n📊 Sheet link: https://docs.google.com/spreadsheets/d/{CONFIG['SHEET_ID']}")

    return results

# ═══════════════════════════════════════════════════════════════════
# ▶️ Run the script
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_pipeline()
