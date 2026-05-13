# Video Scraper for Google Colab - Ready to Use

## Overview
This script scrapes videos from larozaa.yachts, downloads them to Google Drive, uploads to Doodstream, and updates a Google Sheet with all the data.

## Files
- `video_scraper_colab.ipynb` - **Recommended**: Jupyter notebook ready for Google Colab
- `video_scraper_colab.py` - Python script version

## How to Use in Google Colab

### Step 1: Open Google Colab
1. Go to https://colab.research.google.com
2. Click "Upload notebook" 
3. Upload the `video_scraper_colab.ipynb` file

### Step 2: Run the Notebook
1. Click "Runtime" → "Run all" (or run each cell sequentially)
2. When prompted, click the authentication link
3. Sign in with your Google account (the same one that has access to the Google Sheet)
4. Copy and paste the authorization code
5. The script will start processing videos

### Configuration (Already Set)
- **Source URL**: https://larozaa.yachts/category.php?cat=ramadan-2026
- **Google Sheet ID**: 1h4WDPuxUaDreza60h8VjcMLqnbKleWXw9AfMCpjfnnI
- **Doodstream API Key**: 566462d6434dlvqu6fmesc
- **Test Mode**: Processes 5 videos by default (change `max_videos` parameter to process more)

## Features

### 1. Scraping
- Extracts all video listings from the category page
- Gets video ID, title, and creates watch page URLs
- Retrieves all available streaming servers for each video

### 2. Series Organization
- Automatically extracts series name from Arabic video titles
- Creates separate folders in Google Drive for each series
- Creates separate folders in Doodstream for each series

### 3. Download & Upload Flow
1. Downloads video from working server
2. Uploads to Google Drive (in series folder)
3. Uploads to Doodstream (in series folder)
4. Cleans up local temporary file
5. Updates Google Sheet with all links

### 4. Google Sheet Columns
- Video Title (Arabic)
- Video ID
- Watch Page URL
- Server URL (working embed link)
- Google Drive Link
- Doodstream Link
- Series Name

## Customization

### Change Number of Videos to Process
In the last cell, change:
```python
results = process_videos(max_videos=5, test_mode=False)
```
to:
```python
results = process_videos(max_videos=50, test_mode=False)  # Process 50 videos
```

### Test Mode
To test without downloading/uploading:
```python
results = process_videos(max_videos=5, test_mode=True)
```

### Change Source Category
Edit the `CATEGORY_URL` variable:
```python
CATEGORY_URL = "https://larozaa.yachts/category.php?cat=YOUR_CATEGORY"
```

## Requirements
The notebook automatically installs these packages:
- requests
- beautifulsoup4
- google-api-python-client
- doodstream
- pandas
- tqdm

## Authentication
**No credentials.json file needed!** 

Google Colab's built-in authentication is used. When you run the script:
1. You'll see an authentication prompt
2. Click the link provided
3. Sign in with your Google account
4. Grant permissions
5. Copy the authorization code back to Colab

## Notes

### Arabic Text Support
- Full UTF-8 support for Arabic video titles
- Series names are extracted using regex patterns optimized for Arabic text

### Rate Limiting
- 2-second delay between processing each video to avoid being blocked
- Adjust `time.sleep(2)` in the code if needed

### Error Handling
- Tries multiple servers if first one doesn't work
- Continues processing even if individual videos fail
- Logs all errors for debugging

### Storage
- Videos are temporarily downloaded to Colab's runtime
- Automatically deleted after upload to save space
- Google Drive keeps permanent copy
- Doodstream keeps permanent copy

## Troubleshooting

### "No videos found"
- Check if the website is accessible
- Verify the category URL is correct
- The website might have changed its structure

### "Authentication failed"
- Make sure you're using the same Google account that has access to the sheet
- Check that the sheet is shared with your account

### "Upload to Doodstream failed"
- Verify your API key is correct
- Check Doodstream API status
- File might be too large or in unsupported format

### "Download failed"
- Server might be down or blocking requests
- Try increasing timeout values
- The embed URL might not have a direct video link

## API Documentation
- Doodstream API: https://doodstream.com/api-docs
- Google Drive API: https://developers.google.com/drive/api
- Google Sheets API: https://developers.google.com/sheets/api

## License
Use responsibly and respect the website's terms of service.
