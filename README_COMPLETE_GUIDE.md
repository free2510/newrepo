# 🎬 Video Scraper & Uploader - Complete Guide

## Overview
This script scrapes videos from **larozaa.yachts**, downloads them, uploads to **DoodStream** with organized folder structure, and updates **Google Sheets** in **REAL-TIME** after each video.

---

## ✨ Key Features

### 1. **Real-Time Google Sheets Updates**
- ✅ Sheet updated AFTER EACH video (not at the end)
- ✅ Status tracking: Starting → Processing → Success/Failed
- ✅ If interrupted, you won't lose progress - just run again!

### 2. **Organized DoodStream Folder Structure**
```
DoodStream/
└── رمضان 2026 - مسلسلات (Category Folder)
    └── مسلسل روج اسود (Series Folder)
        └── مسلسل روج اسود الحلقة 7 السابعة.mp4
    └── مسلسل درش (Series Folder)
        └── مسلسل درش الحلقة 30.mp4
```

### 3. **Google Drive as Temp Storage** ⚡
- Videos uploaded to Google Drive first (temp only)
- **Automatically deleted** after successful DoodStream upload
- Saves space - Drive is just a temporary host

### 4. **Resume Capability**
- Tracks processed videos in `processed_videos.json`
- Skip already processed videos on restart
- Continue from where you left off

### 5. **Multi-Server Fallback**
- Tests ALL available servers until finding working video URL
- No more skipped videos due to dead links
- Automatic quality check

---

## 📋 Configuration

Edit these values at the top of the script:

```python
CATEGORY_URL = "https://larozaa.yachts/category.php?cat=ramadan-2026"
DOODSTREAM_API_KEY = "your_api_key_here"
GOOGLE_SHEET_ID = "your_sheet_id_here"
CATEGORY_NAME = "رمضان 2026 - مسلسلات"
TEMP_FOLDER = "/content/drive/MyDrive/.temp_videos"
PROCESSED_FILE = "/content/processed_videos.json"
```

---

## 🔧 How It Works

### Step-by-Step Flow:

1. **Scrape Category Page**
   - Extract all video links from category URL
   - Parse video IDs from URLs
   - Skip already processed videos

2. **For Each Video:**
   
   a. **Get Watch Servers**
      - Visit play page: `play.php?vid=VIDEO_ID`
      - Extract all server embed URLs
      - Test each server until finding working one
   
   b. **Download Video**
      - Download to local temp file
      - Verify file size > 1MB
      - Show progress bar
   
   c. **Upload to Google Drive (Temp)** ☁️
      - Upload as `[TEMP] title.mp4`
      - Get Drive file ID
      - Store for cleanup later
   
   d. **Upload to DoodStream** ⬆️
      - Create Category folder if not exists
      - Create Series folder inside Category
      - Upload video to DoodStream
      - Move to correct folder
      - **Delete from Google Drive immediately** ✅
   
   e. **Update Google Sheet** 📊
      - Add row with: Timestamp, Title, Video ID, Watch Link, Series, Category, DoodStream links, Status
      - Update happens IMMEDIATELY after each video
   
   f. **Save Progress**
      - Mark video as processed
      - Save to JSON file for resume

3. **Cleanup**
   - Delete local temp files
   - Delete from Google Drive (already done in step d)

---

## 🚀 Usage in Google Colab

### 1. Setup
```python
# Copy entire script to Colab cell
# Run the cell
```

### 2. Authenticate
- First run will ask for Google authentication
- Allow permissions for Sheets and Drive
- Token saved for future runs

### 3. Monitor Progress
Watch the output:
```
🎬 [1/5] مسلسل روج اسود الحلقة 7 السابعة
   🔍 Getting watch servers...
   📺 Found 13 servers
   🧪 Testing server 1/13: سيرفر 1
   ✅ Working server found: سيرفر 6
   📥 Downloading video...
   ✅ Download successful! Size: 91.81 MB
   ☁️ Uploading to Google Drive (temp)...
   ✅ Uploaded to Drive
   ⬆️ Uploading to DoodStream...
   ✅ Uploaded! File code: abc123xyz
   📁 Moved to series folder: مسلسل روج اسود
   🗑️ Deleting temp file from Google Drive...
   ✅ Temp file deleted from Drive!
   ✅ REAL-TIME UPDATE: Row added to Google Sheet
   🎉 COMPLETED!
```

### 4. Check Results
- **Google Sheet**: Updated in real-time with all data
- **DoodStream**: Organized folders with videos
- **Google Drive**: Empty (all temps deleted)

---

## 📊 Google Sheet Columns

| Column | Description |
|--------|-------------|
| A: Timestamp | When video was processed |
| B: Title | Full video title |
| C: Video ID | Unique video identifier |
| D: Watch Link | Original watch page URL |
| E: Series Name | Extracted series name |
| F: Category | Category name |
| G: DoodStream Watch | DoodStream watch URL |
| H: DoodStream Download | DoodStream download URL |
| I: Status | Current status (Success/Failed/etc) |

---

## 🛠️ Troubleshooting

### Issue: "No Chrome binary" errors
- **Normal**: Selenium warnings are OK if download still works
- Script uses fallback method without browser

### Issue: "File too small" from some servers
- **Expected**: Some servers return HTML instead of video
- Script automatically tries next server

### Issue: DoodStream upload fails
- Check API key is correct
- Ensure folder names don't have special characters
- Wait 1-2 seconds between uploads

### Issue: Google Sheets not updating
- Re-authenticate: delete `/content/token.json`
- Check sheet ID is correct
- Ensure sheet has edit permissions

### Issue: Interrupted processing
- Just run script again!
- Already processed videos will be skipped
- Continues from where it stopped

---

## 🔐 Security Notes

- **API Key**: Keep your DoodStream API key private
- **Google Token**: Stored in `/content/token.json` - don't share
- **Sheet Access**: Only grant necessary permissions

---

## 📈 Performance Tips

1. **Batch Processing**: Process 5-10 videos at a time
2. **Server Selection**: Script auto-selects best server
3. **Resume Often**: Don't process 100+ videos in one run
4. **Monitor Sheet**: Check Google Sheet for any failures

---

## 🎯 What Makes This Special

✅ **Real-time updates** - See progress live in Google Sheet  
✅ **Auto-cleanup** - Google Drive stays empty  
✅ **Organized folders** - Category → Series → Video  
✅ **Resume support** - Never lose progress  
✅ **Multi-server** - Always finds working link  
✅ **Arabic support** - Handles Arabic titles perfectly  

---

## 📝 License

For personal use only. Respect copyright laws.

---

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all configuration values
3. Check Google Sheet for error messages
4. Try processing 1-2 videos first as test

---

**Happy Scraping! 🎉**
