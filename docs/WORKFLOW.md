# 🔄 Workflow - How the Video Scraper Works

This document explains the complete workflow of the video scraper and uploader.

---

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     VIDEO PROCESSING WORKFLOW                    │
└─────────────────────────────────────────────────────────────────┘

1. SCRAPE CATEGORY PAGE
   └─→ Extract video links from larozaa.yachts

2. FOR EACH VIDEO:

   a. Get Watch Servers
      └─→ Visit play.php?vid=VIDEO_ID
      └─→ Extract all server embed URLs
      └─→ Test each server until finding working one

   b. Download Video
      └─→ Download to /content/temp_videos/
      └─→ Verify file size > 1MB
      └─→ Show single-line progress bar

   c. Upload to DoodStream ⬆️
      └─→ Upload to DoodStream root via API
      └─→ Rename file with Arabic title via API
      └─→ Create Category folder (if not exists) via API
      └─→ Create Series folder inside Category via API
      └─→ Move video to Series folder via API
      └─→ Delete from root (automatic after move)

   d. Update Google Sheet
      └─→ Check if row already exists
      └─→ If exists: UPDATE row
      └─→ If new: CREATE row
      └─→ Add: Timestamp, Title, Video ID, Watch Link,
               Series, Category, DoodStream links, Status

   e. Cleanup
      └─→ Delete local temp file
      └─→ Mark video as processed in JSON

3. RESUME SUPPORT
   └─→ Track processed videos in processed_videos.json
   └─→ Skip already processed on restart
```

---

## Detailed Steps

### Step 1: Scrape Category Page

**Input**: Category URL (e.g., `https://larozaa.yachts/category.php?cat=ramadan-2026`)

**Process**:
1. Send HTTP GET request to category URL
2. Parse HTML with BeautifulSoup
3. Extract all video links matching pattern: `play.php?vid=VIDEO_ID`
4. Parse video IDs from URLs
5. Check against `processed_videos.json` to skip already processed
6. Build list of new videos to process

**Output**: List of video dictionaries with:
- `title`: Full video title
- `video_id`: Unique identifier
- `url`: Play page URL
- `series_name`: Extracted series name

---

### Step 2a: Get Watch Servers

**Input**: Video ID

**Process**:
1. Visit play page: `https://larozaa.yachts/play.php?vid=VIDEO_ID`
2. Parse HTML to find all server embed URLs
3. Extract server names and URLs
4. For each server:
   - Load URL with requests (with timeout)
   - Check if video URL is present in response
   - Verify content-type is video (not HTML)
   - Check file size > 1MB
5. Return first working server URL

**Output**: Working video URL for download

**Error Handling**:
- If server returns HTML instead of video → Try next server
- If requests fails → Try next server
- If all servers fail → Mark video as failed in sheet

---

### Step 2b: Download Video

**Input**: Direct video URL (MP4)

**Process**:
1. Generate safe filename: `{video_id}_{series_name}.mp4`
2. Download to `/content/temp_videos/` (local storage, NOT Google Drive)
3. Show single-line progress bar with tqdm
4. Verify downloaded file size > 1MB
5. If verification fails, delete partial file

**Output**: Path to downloaded video file

**Why Local Temp Storage?**
- Faster than uploading to Google Drive then downloading
- Saves Google Drive quota
- Automatic cleanup after upload

---

### Step 2c: Upload to DoodStream

**Input**: Local video file path, series name, video title

**Process**:

#### Phase 1: Upload to Root
```python
result = dood.local_upload(file_path)
file_code = extract_filecode(result)
```

#### Phase 2: Rename File
```python
rename_url = f"https://doodapi.com/api/file/rename?key={API_KEY}&file_code={file_code}&title={quote(video_title)}"
requests.get(rename_url)
```

#### Phase 3: Create Folder Structure

**Category Folder** (`رمضان 2026 - مسلسلات`):
```python
# List existing folders
response = requests.get(f"https://doodapi.com/api/list_folders?key={API_KEY}")
response.raise_for_status()  # Catch HTTP errors
folders = response.json().get('result', [])

# Find or create category folder
for folder in folders:
    if folder['name'] == CATEGORY_NAME:
        category_id = folder['id']
        break

if not category_id:
    create_url = f"https://doodapi.com/api/folder/create?key={API_KEY}&name={quote(CATEGORY_NAME)}"
    result = requests.get(create_url)
    result.raise_for_status()
    category_id = extract_folder_code(result.json())
```

**Series Folder** (e.g., `مسلسل حكاية نرجس`):
```python
# List folders inside category
list_url = f"https://doodapi.com/api/list_folders?key={API_KEY}&fld_id={category_id}"
response = requests.get(list_url)
response.raise_for_status()
series_folders = response.json().get('result', [])

# Find or create series folder
for folder in series_folders:
    if folder['name'] == series_name:
        series_id = folder['id']
        break

if not series_id:
    create_url = f"https://doodapi.com/api/folder/create?key={API_KEY}&name={quote(series_name)}&parent={category_id}"
    result = requests.get(create_url)
    result.raise_for_status()
    print(f"Create folder response: {result.json()}")  # Debug logging
    series_id = extract_folder_code(result.json())
```

#### Phase 4: Move to Series Folder
```python
move_url = f"https://doodapi.com/api/file/move?key={API_KEY}&file_code={file_code}&fld_id={series_id}"
response = requests.get(move_url)

if response.json().get('msg') != 'OK':
    # Fallback: clone + delete
    copy_url = f"https://doodapi.com/api/file/clone?key={API_KEY}&file_code={file_code}&fld_id={series_id}"
    copy_resp = requests.get(copy_url).json()
    if copy_resp.get('msg') == 'OK':
        dood.delete_file([file_code])
```

**Output**: Dictionary with filecode, watch_url, download_url

**Folder Structure Created**:
```
DoodStream/
└── رمضان 2026 - مسلسلات (Category)
    └── مسلسل حكاية نرجس (Series)
        └── مسلسل حكاية نرجس الحلقة 7 السابعة.mp4 (Video)
```

---

### Step 2d: Update Google Sheet

**Input**: Video data dictionary

**Process**:
1. Check if video ID already exists in sheet (Column C)
2. If exists: UPDATE that row with new data
3. If new: APPEND new row

**Sheet Columns**:
| Column | Header | Example |
|--------|--------|---------|
| A | Timestamp | 2026-05-15 00:07:04 |
| B | Title | مسلسل حكاية نرجس الحلقة 7 السابعة |
| C | Video ID | 8b828925a |
| D | Watch Link | https://mp4plus.org/embed-vwh1wabjso5l.html |
| E | Series Name | مسلسل حكاية نرجس |
| F | Category | رمضان 2026 - مسلسلات |
| G | DoodStream Watch | https://doodstream.com/d/99iueh3f2ek4 |
| H | DoodStream Download | https://doodstream.com/download/99iueh3f2ek4 |
| I | Status | ✅ Success |

**Clean URLs**: The script generates clean URLs directly without using the DoodStream library:
```python
def get_doodstream_links(file_code):
    """Returns clean URLs, not JSON objects"""
    return {
        'watch_link': f"https://doodstream.com/d/{file_code}",
        'download_link': f"https://doodstream.com/download/{file_code}"
    }
```

**Real-Time Updates**:
- Initial status: "⏳ Starting"
- Final status: "✅ Success" or "❌ Error: [reason]"
- Updates happen IMMEDIATELY after each video completes

---

### Step 2e: Cleanup

**Process**:
1. Delete local temp file from `/content/temp_videos/`
2. Add video ID to `processed_videos.json`
3. Save updated processed list

**Why Cleanup?**
- Frees up disk space for next video
- Prevents running out of storage in Google Colab
- Ensures clean state for resume

---

### Step 3: Resume Support

**Tracking File**: `/content/processed_videos.json`

**Format**:
```json
[
  "8b828925a",
  "04cb7b3d9",
  "32bf9141a"
]
```

**How It Works**:
1. On startup, load processed video IDs from JSON file
2. When scraping category, skip videos with IDs in the set
3. After successful upload, add video ID to set and save
4. User can run script multiple times to process remaining videos

**Benefits**:
- No duplicate uploads
- Can process large batches in multiple sessions
- Survives script crashes or Colab disconnections

---

## Error Handling

### Network Errors
- **Timeout**: 15 seconds for API calls, 10 seconds for folder listing
- **Retry Logic**: 3 attempts for Google Sheets updates
- **Fallback Methods**: Clone+delete if move fails

### API Errors
- **HTTP Errors**: `response.raise_for_status()` catches 4xx/5xx errors
- **JSON Parsing**: Wrapped in try-except to handle empty responses
- **Debug Logging**: Print API responses for troubleshooting

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Expecting value: line 1 column 1" | Empty API response | Added `raise_for_status()` |
| JSON in Google Sheets | Using library method | Direct URL construction |
| Folder not created | API error | Debug logging added |
| Rate limiting | Too many requests | Added delays between calls |

---

## Performance Optimizations

1. **Single-Line Progress Bars**: Prevents log spam during downloads
2. **Direct API Calls**: More reliable than library methods
3. **URL Encoding**: Proper handling of Arabic characters
4. **HTTP Error Checking**: Catch errors before JSON parsing
5. **Local Temp Storage**: Faster than Google Drive round-trip
6. **Resume Capability**: Process in batches, resume anytime

---

## Complete Flow Example

Let's trace processing one video:

**Video**: "مسلسل حكاية نرجس الحلقة 7 السابعة"

1. **Scrape**: Found in category page with video_id=`8b828925a`
2. **Check**: Not in `processed_videos.json` → Process it
3. **Servers**: Found 12 servers, tested 1-6, server 6 works
4. **Download**: Downloaded 112.73 MB to `/content/temp_videos/8b828925a_مسلسل_حكاية_نرجس.mp4`
5. **Upload**: Uploaded to DoodStream root → filecode=`99iueh3f2ek4`
6. **Rename**: Renamed to "مسلسل حكاية نرجس الحلقة 7 السابعة"
7. **Folders**: 
   - Category "رمضان 2026 - مسلسلات" exists → use it
   - Series "مسلسل حكاية نرجس" created inside category
8. **Move**: Moved file to series folder
9. **Sheet**: Updated Google Sheet row with clean URLs
10. **Cleanup**: Deleted local temp file
11. **Track**: Added `8b828925a` to processed_videos.json

**Result**:
- ✅ Video uploaded to correct folder structure
- ✅ Google Sheet updated with clean URLs
- ✅ Local storage cleaned up
- ✅ Progress saved for resume

---

## Version History

### v2.2 (2026-05-15)
- Added `response.raise_for_status()` to all API calls
- Added debug logging for folder creation
- Fixed Google Sheets to show clean URLs instead of JSON
- Improved error messages for HTTP and JSON errors

### v2.1 (2026-05-14)
- Implemented direct API calls for folder operations
- Added URL encoding for Arabic folder names
- Changed rename endpoint to `/api/file/rename`
- Changed move method to `/api/file/move` with fallback
- Updated documentation

### v2.0 (2026-05-13)
- Real-time Google Sheets updates
- Local temp storage (not Google Drive)
- Resume capability with JSON tracking
- Single-line progress bars

---

**Last Updated**: 2026-05-15  
**Version**: 2.2
