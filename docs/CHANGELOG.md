# 📝 Changelog - Version History

## [2.0] - 2026-05-14

### 🎉 Major Improvements

#### Fixed Issues:
1. **Google Sheets - No More Duplicate Rows**
   - Added `get_existing_video_row()` function to check if video already exists
   - Modified `update_sheet_realtime()` to UPDATE existing rows instead of creating duplicates
   - Only creates new row for "⏳ Starting" status, then updates same row for all subsequent statuses
   - Final result: ONE row per video with final status (✅ Success or ❌ Error)

2. **DoodStream Upload - Fixed Folder Structure**
   - Enhanced `get_or_create_folder_structure()` to properly handle API responses
   - Now correctly extracts folder IDs from `result.foldercode` or `result.id`
   - Added proper type checking for list/dict responses from API
   - Videos now upload to correct structure: Category → Series → Video

3. **File Renaming**
   - Added file rename step after upload using DoodStream API
   - Files now have proper Arabic titles instead of random codes

4. **No Google Drive Storage**
   - Videos download to local temp folder `/content/temp_videos`
   - After successful DoodStream upload, local file is deleted
   - NO files are stored in `/content/drive/MyDrive/` anymore

5. **Better Error Handling**
   - Added proper handling for different API response formats (list vs dict)
   - Added type checking for all API responses
   - Better error messages for debugging

6. **Upload Timeout Handling**
   - Added retry logic with 2 attempts
   - Better exception handling for network issues
   - Result: More resilient uploads

7. **Google Sheets Headers Verification**
   - Check if headers exist AND have correct number of columns (9)
   - Auto-fix if columns are missing
   - Result: Consistent sheet structure

### 🔧 Code Changes

#### Modified Functions:
1. **`upload_to_doodstream()`** 
   - Removed `drive_file_id` parameter (no longer needed)
   - Enhanced response parsing for different API formats
   - Improved folder movement with try/catch
   - Added traceback on errors

2. **`process_video()`**
   - Removed Google Drive upload step
   - Downloads directly to local temp folder
   - Removed `delete_from_google_drive()` call
   - Simplified workflow

3. **`update_sheet_realtime()`**
   - Added duplicate row prevention
   - Always checks if row exists first
   - Updates existing row instead of creating new one

4. **Initialization section**
   - Clarified Google Drive is only for Sheets auth
   - Added message about local temp folder

### 📁 New Workflow

```
1. Scrape video URL from website
2. Download to /content/temp_videos/ (local storage)
3. Upload to DoodStream:
   - Upload to root
   - Rename file with Arabic title
   - Move to Category/Series folder
   - Delete from root
4. Delete local temp file
5. Update Google Sheet (single row, real-time)
```

### 📊 Expected Google Sheet Result

| Timestamp | Title | Video ID | Watch Link | Series Name | Category | DoodStream Watch | DoodStream Download | Status |
|-----------|-------|----------|------------|-------------|----------|------------------|---------------------|--------|
| 2026-05-14 20:19:48 | مسلسل حكاية نرجس الحلقة 7 السابعة | 8b828925a | ... | مسلسل حكاية نرجس | رمضان 2026 - مسلسلات | https://dood... | https://dood... | ✅ Success |

**Only ONE row per video!** No more duplicates for "Starting", "Failed", etc.

---

## [1.5] - 2026-05-14

### ⚡ Performance Improvements

#### Fixed Issues:
1. **Removed Google Drive as Temporary Storage**
   - **Before**: Videos were downloaded → uploaded to Google Drive → uploaded to DoodStream → deleted from Drive
   - **After**: Videos are downloaded to local temp folder (`/content/temp_videos`) → uploaded directly to DoodStream → deleted from local temp
   
   **Benefits:**
   - No accumulation of files in `/content/drive/MyDrive/مسلسل حكاية نرجس`
   - Faster processing (no double upload)
   - Cleaner workflow

2. **Fixed DoodStream Folder Upload Error**
   - **Problem**: Error `'str' object has no attribute 'get'` and `'list' object has no attribute 'get'`
   - **Solution**: Enhanced response handling in `upload_to_doodstream()`:
     - Better parsing of different API response formats (list vs dict)
     - Proper extraction of `filecode` and `id` from nested structures
     - Added detailed error messages showing response type and content

3. **Improved Folder Structure on DoodStream**
   - Videos now properly organized: `Category → Series → Video`
   - Fixed folder movement logic with better error handling
   - Added verification step after moving files to folders

4. **Single-Line Download Progress**
   - Download progress bar updates on single line (not multiple lines)
   - Cleaner console output

### 🔧 Code Changes

#### Modified Functions:
1. **`upload_to_doodstream()`** (lines 419-508)
   - Removed `drive_file_id` parameter (no longer needed)
   - Enhanced response parsing for different API formats
   - Improved folder movement with try/catch
   - Added traceback on errors

2. **`process_video()`** (lines 648-684)
   - Removed Google Drive upload step
   - Downloads directly to local temp folder
   - Removed `delete_from_google_drive()` call
   - Simplified workflow

3. **Initialization section** (lines 54-63)
   - Clarified Google Drive is only for Sheets auth
   - Added message about local temp folder

### 📁 New Workflow

```
1. Scrape video URL from website
2. Download to /content/temp_videos/ (local storage)
3. Upload to DoodStream:
   - Upload to root
   - Move to Category/Series folder
   - Delete from root
4. Delete local temp file
5. Update Google Sheet (real-time)
```

### ⚠️ Important Notes

- Google Drive is still mounted for Google Sheets authentication only
- No video files are stored in Google Drive anymore
- Temp files are automatically cleaned up after successful upload
- If upload fails, temp file remains for debugging (manual cleanup may be needed)

---

## [1.0] - Initial Release

### ✨ Features

1. **Real-Time Google Sheets Updates**
   - Sheet updated AFTER EACH video (not at the end)
   - Status tracking: Starting → Processing → Success/Failed
   - If interrupted, you won't lose progress - just run again!

2. **Organized DoodStream Folder Structure**
   ```
   DoodStream/
   └── رمضان 2026 - مسلسلات (Category Folder)
       └── مسلسل روج اسود (Series Folder)
           └── Video files
   ```

3. **Resume Capability**
   - Tracks processed videos in `processed_videos.json`
   - Skip already processed videos on restart
   - Continue from where you left off

4. **Multi-Server Fallback**
   - Tests ALL available servers until finding working video URL
   - No more skipped videos due to dead links
   - Automatic quality check

5. **Google Drive as Temp Storage**
   - Videos uploaded to Google Drive first (temp only)
   - Automatically deleted after successful DoodStream upload
   - Saves space - Drive is just a temporary host

---

## Migration Notes

### From v1.0 to v1.5
- No migration needed - improvements are backward compatible
- Temp folder location changed from `/content/drive/MyDrive/.temp_videos` to `/content/temp_videos`

### From v1.5 to v2.0
- No migration needed - improvements are backward compatible
- Google Sheet will now show only ONE row per video (no duplicates)
- File renaming happens automatically after upload

---

**Last Updated**: 2026-05-14  
**Current Version**: 2.0
