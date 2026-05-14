# 🔧 Setup Guide - Video Scraper & Uploader

This guide will help you set up and configure the video scraper script.

## Prerequisites

- Google Colab account (or Python 3.8+ environment)
- DoodStream account with API access
- Google account with Sheets and Drive access
- Internet connection

---

## Step 1: Get DoodStream API Key

1. **Sign up/Login** to [DoodStream](https://doodstream.com)
2. Go to **Account Settings** → **API**
3. Copy your **API Key**
4. Keep it secure - don't share it publicly

---

## Step 2: Create Google Sheet

1. **Create a new Google Sheet**:
   - Go to [Google Sheets](https://sheets.google.com)
   - Click "+ Blank" to create a new sheet
   - Name it "Video Tracker" or similar

2. **Set up headers** (Row 1):
   ```
   A1: Timestamp
   B1: Title
   C1: Video ID
   D1: Watch Link
   E1: Series Name
   F1: Category
   G1: DoodStream Watch
   H1: DoodStream Download
   I1: Status
   ```

3. **Get Sheet ID**:
   - Look at the URL: `https://docs.google.com/spreadsheets/d/SHEET_ID/edit`
   - Copy the `SHEET_ID` part (long string between `/d/` and `/edit`)

4. **Share the sheet**:
   - Click "Share" button
   - Add your Google account email with "Editor" permissions

---

## Step 3: Configure the Script

Edit these values at the top of `video_scraper_final.py`:

```python
# === CONFIGURATION ===
CATEGORY_URL = "https://larozaa.yachts/category.php?cat=ramadan-2026"
DOODSTREAM_API_KEY = "your_api_key_here"  # ← Paste your API key
GOOGLE_SHEET_ID = "your_sheet_id_here"    # ← Paste your Sheet ID
CATEGORY_NAME = "رمضان 2026 - مسلسلات"
TEMP_FOLDER = "/content/temp_videos"
PROCESSED_FILE = "/content/processed_videos.json"
# =====================
```

---

## Step 4: Run in Google Colab

### Option A: Full Script

1. **Open Google Colab**: [colab.research.google.com](https://colab.research.google.com)
2. **Create new notebook**
3. **Copy entire script** from `video_scraper_final.py`
4. **Paste into cell**
5. **Run the cell** (Shift + Enter or click play button)

### Option B: Step-by-Step

#### Cell 1: Install Dependencies
```python
!pip install requests beautifulsoup4 selenium gspread google-auth google-auth-oauthlib google-auth-httplib2 pydrive tqdm
```

#### Cell 2: Mount Google Drive & Authenticate
```python
from google.colab import drive
drive.mount('/content/drive')

# Authenticate Google Sheets
import gspread
from google.auth import default
creds, _ = default()
gc = gspread.authorize(creds)
```

#### Cell 3: Run Script
```python
# Paste the main script here
# Make sure to update configuration values first
```

---

## Step 5: First Run Authentication

On first run, you'll be asked to:

1. **Authenticate with Google**:
   - Click the authorization link
   - Sign in with your Google account
   - Grant permissions for Sheets and Drive
   - Copy the authorization code
   - Paste it back in the notebook

2. **Token saved**:
   - Token is saved to `/content/token.json`
   - Future runs won't require re-authentication

---

## Step 6: Monitor Progress

Watch the output in Colab:

```
🎬 [1/40] مسلسل حكاية نرجس الحلقة 7 السابعة
   🔍 Getting watch servers...
   📺 Found 12 servers
   🧪 Testing server 1/12: سيرفر 1
   ✅ Working server found: سيرفر 6
   📥 Downloading video...
⬇️ 8b828925a_مسلسل_حكاية_نرجس.mp4: 100%|██████████| 118M/113M [00:00, 26.2MB/s]
   ✅ Download successful! Size: 112.73 MB
   ⬆️ Uploading to DoodStream...
   ✅ Uploaded! File code: abc123xyz
   📁 Moved to series folder: مسلسل حكاية نرجس
   ✅ REAL-TIME UPDATE: Row added to Google Sheet
   🎉 COMPLETED!
```

Check your **Google Sheet** - it should update in real-time!

---

## Configuration Options

### Required Settings

| Setting | Description | Example |
|---------|-------------|---------|
| `CATEGORY_URL` | URL of category page to scrape | `https://larozaa.yachts/category.php?cat=ramadan-2026` |
| `DOODSTREAM_API_KEY` | Your DoodStream API key | `abc123xyz456` |
| `GOOGLE_SHEET_ID` | ID of your Google Sheet | `1abc2def3ghi4jkl5mno6pqr7stu8vwx9yz` |
| `CATEGORY_NAME` | Category name for folder structure | `رمضان 2026 - مسلسلات` |

### Optional Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TEMP_FOLDER` | `/content/temp_videos` | Local temp storage location |
| `PROCESSED_FILE` | `/content/processed_videos.json` | Resume tracking file |

---

## Troubleshooting Setup Issues

### Issue: "Invalid API Key"
- Double-check your DoodStream API key
- Ensure no extra spaces or characters
- Try regenerating the key in DoodStream settings

### Issue: "Sheet not found"
- Verify Sheet ID is correct
- Ensure sheet is shared with your account
- Check sheet is not private/restricted

### Issue: "Authentication failed"
- Delete `/content/token.json` and re-run
- Ensure you granted all permissions
- Try using incognito mode for authentication

### Issue: "Permission denied"
- Make sure your Google account has editor access to the sheet
- Check Drive sharing settings
- Re-authenticate if needed

---

## Best Practices

1. **Test with 1-2 videos first** before processing large batches
2. **Monitor Google Sheet** for any errors during processing
3. **Keep API key secure** - don't commit it to version control
4. **Backup your sheet** regularly
5. **Process in batches** of 10-20 videos to avoid timeouts

---

## Next Steps

- See [WORKFLOW.md](WORKFLOW.md) for detailed workflow explanation
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- See [API_REFERENCE.md](API_REFERENCE.md) for DoodStream API details

---

**Need Help?** Check the [README.md](README.md) for overview and support information.
