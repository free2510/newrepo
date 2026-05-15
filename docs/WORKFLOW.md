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

**Input**: Video URL, video title

**Process**:
1. Create sanitized filename: `[VIDEO_ID]_[TITLE].mp4`
2. Download to `/content/temp_videos/[FILENAME]`
3. Show single-line progress bar (tqdm)
4. Verify downloaded file size > 1MB
5. Return path to downloaded file

**Output**: Path to local video file

**Example Output**:
```
⬇️ 8b828925a_مسلسل_حكاية_نرجس.mp4: 100%|██████████| 118M/113M [00:00, 26.2MB/s]
✅ Download successful! Size: 112.73 MB
```

---

### Step 2c: Upload to DoodStream

**Input**: Local file path, series name, video title

**Process**:

#### Phase 1: Upload to Root
1. Call DoodStream API: `/api/upload`
2. Send file as multipart/form-data
3. Receive response with `filecode`
4. Store filecode for next steps

#### Phase 2: Rename File
1. Call DoodStream API: `/api/file/rename`
2. Parameters: `filecode`, `title` (URL-encoded Arabic title)
3. Wait 1-2 seconds for API to process
4. Verify rename successful

#### Phase 3: Create Folder Structure
1. **Get or Create Category Folder**:
   - Call `/api/list_folders` to check if exists
   - If not exists: Call `/api/folder/create` with category name
   - Store category folder code

2. **Get or Create Series Folder**:
   - Call `/api/list_folders` with parent=category to check if exists
   - If not exists: Call `/api/folder/create` with series name, parent=category
   - Store series folder code

#### Phase 4: Move to Folder
1. Call `/api/file/move` with:
   - `filecode`: Video file code
   - `fld_id`: Series folder code
2. Verify move successful
3. Fallback: If move fails, try clone + delete method

**Output**: DoodStream file code, watch URL, download URL

**Folder Structure**:
```
DoodStream/
└── رمضان 2026 - مسلسلات (Category)
    └── مسلسل حكاية نرجس (Series)
        └── مسلسل حكاية نرجس الحلقة 7 السابعة.mp4
```

**API Endpoints Used**:
- `https://doodapi.com/api/upload` - Upload file
- `https://doodapi.com/api/file/rename` - Rename file  
- `https://doodapi.com/api/list_folders` - List folders
- `https://doodapi.com/api/folder/create` - Create folder
- `https://doodapi.com/api/file/move` - Move file to folder

---

### Step 2d: Update Google Sheet

**Input**: Video data, DoodStream URLs, status

**Process**:
1. **Check if row exists**:
   - Search column C (Video ID) for matching ID
   - If found: Get row number
   - If not found: Prepare to create new row

2. **Update or Create**:
   - **If row exists**: Update columns A-I with new data
   - **If new row**: Append row with all data

3. **Columns Updated**:
   - A: Timestamp (current time)
   - B: Title (full video title)
   - C: Video ID (unique identifier)
   - D: Watch Link (original play page URL)
   - E: Series Name (extracted from title)
   - F: Category (category name)
   - G: DoodStream Watch (watch URL)
   - H: DoodStream Download (download URL)
   - I: Status (✅ Success or ❌ Error message)

**Output**: Updated Google Sheet row

**Example Sheet Row**:
| Timestamp | Title | Video ID | Watch Link | Series Name | Category | DoodStream Watch | DoodStream Download | Status |
|-----------|-------|----------|------------|-------------|----------|------------------|---------------------|--------|
| 2026-05-14 20:19:48 | مسلسل حكاية نرجس الحلقة 7 السابعة | 8b828925a | https://... | مسلسل حكاية نرجس | رمضان 2026 - مسلسلات | https://dood... | https://dood... | ✅ Success |

---

### Step 2e: Cleanup

**Process**:
1. Delete local temp file: `os.remove(downloaded_path)`
2. Mark video as processed:
   - Load `processed_videos.json`
   - Add video ID to list
   - Save back to file
3. Log completion message

**Output**: Clean temp folder, updated processed list

---

## Resume Mechanism

### How It Works

1. **Tracking File**: `processed_videos.json`
   ```json
   {
     "processed_videos": [
       "8b828925a",
       "04cb7b3d9",
       "..."]
   }
   ```

2. **On Script Start**:
   - Load `processed_videos.json`
   - For each video scraped from website:
     - Check if video_id in processed list
     - If yes: Skip (already done)
     - If no: Process normally

3. **After Each Video**:
   - Add video_id to processed list
   - Save to JSON file immediately

### Benefits

- **Interrupt Recovery**: If script stops, just run again
- **No Duplicates**: Already processed videos are skipped
- **Progress Tracking**: Know exactly which videos are done
- **Batch Processing**: Can process in multiple sessions

---

## Error Handling

### Download Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "File too small" | Server returned HTML | Try next server |
| "403 Forbidden" | Access denied | Try next server |
| "Network error" | Connection issue | Retry with timeout |
| "Timeout" | Slow server | Increase timeout, retry |

### Upload Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid API key" | Wrong key | Check API key in config |
| "Folder create failed" | API error | Retry, check folder name |
| "Move failed" | File not found | Verify upload completed |
| "Rename failed" | API rate limit | Wait 1-2 seconds, retry |

### Sheet Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Sheet not found" | Wrong ID | Check Sheet ID |
| "Permission denied" | No access | Share sheet with account |
| "Duplicate rows" | Bug | Fixed in v2.0 - updates row instead |

---

## Performance Optimization

### Current Optimizations

1. **Single-line progress bar** - Reduces console output
2. **Local temp storage** - Faster than Drive upload/download
3. **Auto-cleanup** - Deletes temp files immediately
4. **Server testing** - Stops at first working server
5. **Resume support** - Skips processed videos
6. **Real-time updates** - See progress live in sheet
7. **Direct API calls** - More reliable folder operations
8. **URL encoding** - Proper handling of Arabic titles

### Best Practices

1. **Process in batches** of 10-20 videos
2. **Monitor sheet** for errors during processing
3. **Don't interrupt** during upload (can cause duplicates)
4. **Wait between runs** if processing many videos
5. **Check temp folder** occasionally for stuck files

---

## File Locations

### During Processing

| Location | Purpose | Retained? |
|----------|---------|-----------|
| `/content/temp_videos/` | Temp video storage | ❌ Deleted after upload |
| `/content/processed_videos.json` | Resume tracking | ✅ Kept for resume |
| `/content/token.json` | Google auth token | ✅ Kept for auth |
| Google Sheets | Progress tracking | ✅ Kept permanently |
| DoodStream | Final video storage | ✅ Kept permanently |

### After Processing

- **Local temp**: Empty (all files deleted)
- **Google Drive**: Empty (never used for storage)
- **DoodStream**: Organized folders with videos
- **Google Sheet**: Complete record of all videos

---

## Next Steps

- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- See [API_REFERENCE.md](API_REFERENCE.md) for DoodStream API details
- See [CHANGELOG.md](CHANGELOG.md) for version history

---

**Last Updated**: 2026-05-14  
**Version**: 2.1
