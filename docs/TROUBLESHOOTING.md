# 🛠️ Troubleshooting Guide

Common issues and their solutions for the Video Scraper & Uploader.

---

## Table of Contents

- [Installation Issues](#installation-issues)
- [Authentication Issues](#authentication-issues)
- [Scraping Issues](#scraping-issues)
- [Download Issues](#download-issues)
- [Upload Issues](#upload-issues)
- [Google Sheets Issues](#google-sheets-issues)
- [DoodStream Issues](#doodstream-issues)
- [Performance Issues](#performance-issues)

---

## Installation Issues

### Issue: "ModuleNotFoundError: No module named 'requests'"

**Cause**: Missing Python dependencies

**Solution**:
```python
!pip install requests beautifulsoup4 selenium gspread google-auth google-auth-oauthlib google-auth-httplib2 pydrive tqdm
```

### Issue: "pip install failed"

**Cause**: Network issue or incompatible version

**Solution**:
```python
!pip install --upgrade pip
!pip install requests beautifulsoup4 selenium gspread google-auth google-auth-oauthlib google-auth-httplib2 pydrive tqdm --force-reinstall
```

---

## Authentication Issues

### Issue: "No Chrome binary" / Selenium errors

**Symptoms**:
```
⚠️ Selenium error: Message: unknown error: cannot find Chrome binary
```

**Cause**: Selenium trying to use Chrome in Colab (not configured)

**Solution**: 
- **This is NORMAL** - Script has fallback to use requests without browser
- As long as download works, you can ignore these warnings
- The script will automatically try next server if one fails

### Issue: Google Authentication Failed

**Symptoms**:
```
Error: Could not authenticate with Google
```

**Solution**:
1. Delete token file: `!rm /content/token.json`
2. Re-run the script
3. Click authorization link carefully
4. Ensure you're signed in with correct Google account
5. Grant ALL requested permissions
6. Copy authorization code completely (no extra spaces)
7. Paste code back in notebook

### Issue: "Permission denied" for Google Sheet

**Cause**: Sheet not shared with your account

**Solution**:
1. Open your Google Sheet
2. Click "Share" button (top-right)
3. Add your Google account email
4. Set permission to "Editor"
5. Save and re-run script

### Issue: Drive already mounted message

**Symptoms**:
```
Drive already mounted at /content/drive; to attempt to forcibly remount...
```

**Solution**: 
- **This is NORMAL** - Just informational message
- Script only needs Drive mounted for Google Sheets auth
- No files are stored in Drive anymore

---

## Scraping Issues

### Issue: "Found 0 videos"

**Cause**: Website structure changed or wrong URL

**Solution**:
1. Verify category URL is correct
2. Check website is accessible: Open URL in browser
3. Inspect page source to verify video links exist
4. Update script if website HTML structure changed
5. Try different category URL

### Issue: Video titles have special characters

**Cause**: Arabic/special characters in titles

**Solution**:
- Script handles this automatically
- Filenames are sanitized before saving
- No action needed unless upload fails

---

## Download Issues

### Issue: "File too small" from servers

**Symptoms**:
```
❌ Download failed from this server: Downloaded file too small: 0.02MB
```

**Cause**: Server returned HTML page instead of video

**Solution**:
- **This is EXPECTED** - Script automatically tries next server
- Some servers always return HTML (ads/landing pages)
- Script will continue testing until finding working server
- If all servers fail, video is marked as failed in sheet

### Issue: "403 Forbidden" error

**Symptoms**:
```
❌ Network error: 403 Client Error: Forbidden for url
```

**Cause**: Server blocking automated access

**Solution**:
- Script automatically tries next server
- If all servers give 403, website may have anti-bot protection
- Try again later or use different category

### Issue: Download timeout

**Symptoms**:
```
TimeoutError: Connection timed out
```

**Cause**: Slow server or network issue

**Solution**:
- Script has retry logic built-in
- Wait for retry attempt
- If persistent, server may be down
- Try next video or come back later

### Issue: "Content-Type: text/html" warning

**Symptoms**:
```
⚠️ Warning: Content-Type: text/html; charset=UTF-8
```

**Cause**: Server returning HTML instead of video

**Solution**:
- Script detects this and marks download as failed
- Automatically tries next server
- No action needed

---

## Upload Issues

### Issue: "'str' object has no attribute 'get'"

**Symptoms**:
```
❌ Could not get file code from upload. Response type: <class 'dict'>
```

**Cause**: API response format changed or unexpected

**Solution**:
- **Fixed in v2.0** - Enhanced response parsing
- Update script to latest version
- Script now handles both list and dict responses

### Issue: "'list' object has no attribute 'get'"

**Symptoms**:
```
❌ Upload error: 'list' object has no attribute 'get'
```

**Cause**: API returned list instead of dict

**Solution**:
- **Fixed in v2.0** - Better type checking
- Update script to latest version
- Added proper handling for nested structures

### Issue: "Invalid API key"

**Symptoms**:
```
❌ Upload failed: Invalid API key
```

**Cause**: Wrong or missing API key

**Solution**:
1. Check `DOODSTREAM_API_KEY` in script config
2. Ensure no extra spaces or quotes
3. Verify API key in DoodStream dashboard
4. Try regenerating API key
5. Ensure API access is enabled on your account

### Issue: Folder creation failed

**Symptoms**:
```
❌ Could not create folder: Ramadan 2026
```

**Cause**: API rate limit or invalid folder name

**Solution**:
- Script waits 1-2 seconds between API calls
- Check folder name doesn't have invalid characters
- Retry - may be temporary API issue
- Verify API has folder creation permissions

### Issue: File move failed

**Symptoms**:
```
❌ Could not move file to folder
```

**Cause**: File not found or folder doesn't exist

**Solution**:
- Verify upload completed successfully
- Check folder was created
- Script has retry logic - wait for retry
- May need to manually move file in DoodStream

### Issue: Upload timeout (KeyboardInterrupt)

**Symptoms**:
```
KeyboardInterrupt during upload
```

**Cause**: Large file or slow connection

**Solution**:
- **Fixed in v2.0** - Added retry logic with 2 attempts
- Script will retry failed uploads
- Process fewer videos per batch
- Check internet connection stability

---

## Google Sheets Issues

### Issue: Duplicate rows in sheet

**Symptoms**: Multiple rows for same video

**Cause**: Script creating new row for each status update

**Solution**:
- **Fixed in v2.0** - Script now checks for existing rows
- Updates existing row instead of creating duplicate
- Only ONE row per video with final status
- Update script to latest version

### Issue: Sheet not updating

**Symptoms**: Google Sheet stays empty

**Cause**: Authentication or permission issue

**Solution**:
1. Check Sheet ID is correct in config
2. Verify sheet is shared with your account
3. Delete `/content/token.json` and re-authenticate
4. Check sheet has correct headers (9 columns)
5. Ensure you have editor permissions

### Issue: Wrong number of columns

**Symptoms**: Data appears in wrong columns

**Cause**: Sheet headers don't match expected format

**Solution**:
1. Ensure Row 1 has exactly these headers:
   ```
   A: Timestamp
   B: Title
   C: Video ID
   D: Watch Link
   E: Series Name
   F: Category
   G: DoodStream Watch
   H: DoodStream Download
   I: Status
   ```
2. Delete any extra columns
3. Script auto-fixes missing columns in v2.0

### Issue: "httplib2 transport" warnings

**Symptoms**:
```
WARNING:google_auth_httplib2:httplib2 transport does not support per-request timeout
```

**Cause**: Google library limitation

**Solution**:
- **This is NORMAL** - Just a warning, not an error
- Script continues to work normally
- Can be ignored safely

---

## DoodStream Issues

### Issue: Videos not in correct folder

**Symptoms**: Videos appear in root instead of Category/Series folders

**Cause**: Move operation failed or skipped

**Solution**:
- **Fixed in v2.0** - Enhanced folder movement logic
- Script now renames BEFORE moving
- Better error handling for move operation
- Verify folder structure in DoodStream dashboard

### Issue: Files have random codes as names

**Symptoms**: `abc123xyz.mp4` instead of Arabic title

**Cause**: Rename operation failed

**Solution**:
- **Fixed in v2.0** - Added rename step after upload
- Script waits 1-2 seconds for API to process
- Retry if rename fails
- Update to latest version

### Issue: API rate limiting

**Symptoms**:
```
❌ Upload failed: Too many requests
```

**Cause**: Making too many API calls too fast

**Solution**:
- Script has built-in delays (1-2 seconds)
- Process videos in smaller batches (5-10 at a time)
- Wait between batches
- Don't run multiple instances simultaneously

---

## Performance Issues

### Issue: Script running very slow

**Cause**: Testing many dead servers or slow downloads

**Solution**:
- Normal for first few servers to fail
- Script finds working server eventually
- If consistently slow, website may have issues
- Try processing fewer videos per batch

### Issue: Console output too verbose

**Cause**: Many lines of progress bar output

**Solution**:
- **Fixed** - Single-line progress bar in latest version
- Progress updates in place instead of new lines
- Cleaner console output

### Issue: Interrupted processing

**Cause**: Manual interrupt or timeout

**Solution**:
- **Script supports resume!**
- Just run script again
- Already processed videos will be skipped
- Continues from where it stopped
- Check `processed_videos.json` for tracking

---

## Quick Reference

### Common Error Messages

| Error | Severity | Action |
|-------|----------|--------|
| "No Chrome binary" | ⚠️ Warning | Ignore - normal |
| "File too small" | ⚠️ Expected | Tries next server |
| "httplib2 transport" | ⚠️ Warning | Ignore - normal |
| "403 Forbidden" | ❌ Error | Tries next server |
| "Invalid API key" | ❌ Error | Fix API key in config |
| "Sheet not found" | ❌ Error | Check Sheet ID |
| "Duplicate rows" | ✅ Fixed | Update to v2.0 |
| "Upload timeout" | ✅ Fixed | Retry logic added |

### When to Update Script

Update to v2.0 if you experience:
- ❌ Duplicate rows in Google Sheet
- ❌ Upload errors with 'str' or 'list' attributes
- ❌ Files not renamed properly
- ❌ Videos not in correct folders
- ❌ Multiple progress bar lines

### Getting Help

If issue not listed here:
1. Check [README.md](README.md) for overview
2. Review [WORKFLOW.md](WORKFLOW.md) for process details
3. See [CHANGELOG.md](CHANGELOG.md) for recent fixes
4. Check Google Sheet for specific error messages
5. Try processing 1-2 videos as test

---

**Last Updated**: 2026-05-14  
**Version**: 2.0
