# 📡 DoodStream API Reference

Complete reference for DoodStream API integration used in the video scraper.

---

## Overview

The script uses the official [DoodStream API](https://doodstream.com/api-docs) to:
- Upload video files
- Create folder structure
- Rename files
- Move files to folders
- Get account information

**Base URL**: `https://doodstream.com/api`  
**Authentication**: API Key via query parameter `?key=YOUR_API_KEY`

---

## API Endpoints Used

### 1. Account Info

**Endpoint**: `/api/account/info`  
**Method**: GET  
**Purpose**: Verify API key and get account details

**Request**:
```
GET https://doodstream.com/api/account/info?key=YOUR_API_KEY
```

**Response**:
```json
{
  "msg": "OK",
  "status": 200,
  "result": {
    "email": "user@example.com",
    "storage": {
      "used": "1234567890",
      "limit": "999999999999"
    }
  }
}
```

**Used in Script**: Initial validation (optional)

---

### 2. Upload File

**Endpoint**: `/api/upload`  
**Method**: POST (multipart/form-data)  
**Purpose**: Upload video file to root directory

**Request**:
```
POST https://doodstream.com/api/upload?key=YOUR_API_KEY
Content-Type: multipart/form-data

file: [binary video file]
```

**Response**:
```json
{
  "msg": "OK",
  "status": 200,
  "result": [
    {
      "filecode": "abc123xyz",
      "name": "video.mp4",
      "size": "123456789"
    }
  ]
}
```

**Note**: Response can be:
- **List**: `{"result": [{...}]}` - Most common
- **Dict**: `{"result": {...}}` - Sometimes returned

**Used in Script**: `upload_to_doodstream()` function

**Implementation**:
```python
import requests

def upload_file(file_path, api_key):
    url = f"https://doodstream.com/api/upload?key={api_key}"
    files = {"file": open(file_path, "rb")}
    response = requests.post(url, files=files)
    result = response.json()
    
    # Handle both list and dict responses
    if isinstance(result.get('result'), list):
        filecode = result['result'][0]['filecode']
    elif isinstance(result.get('result'), dict):
        filecode = result['result']['filecode']
    else:
        raise Exception("Unexpected response format")
    
    return filecode
```

---

### 3. Rename File

**Endpoint**: `/api/rename`  
**Method**: GET  
**Purpose**: Rename uploaded file with proper title

**Request**:
```
GET https://doodstream.com/api/rename?key=YOUR_API_KEY&filecode=FILECODE&title=NEW_TITLE
```

**Parameters**:
- `filecode`: File code from upload response
- `title`: New filename (supports Arabic/Unicode)

**Response**:
```json
{
  "msg": "OK",
  "status": 200
}
```

**Used in Script**: After upload, before moving to folder

**Important Notes**:
- Wait 1-2 seconds after upload before renaming
- Title can contain Arabic characters
- Special characters are handled automatically

**Implementation**:
```python
import requests
import time

def rename_file(filecode, new_title, api_key):
    # Wait for upload to process
    time.sleep(2)
    
    url = f"https://doodstream.com/api/rename?key={api_key}"
    params = {
        "filecode": filecode,
        "title": new_title
    }
    response = requests.get(url, params=params)
    return response.json()
```

---

### 4. Create Folder

**Endpoint**: `/api/folder/create`  
**Method**: GET  
**Purpose**: Create new folder (category or series)

**Request**:
```
GET https://doodstream.com/api/folder/create?key=YOUR_API_KEY&name=FOLDER_NAME&parent=PARENT_CODE
```

**Parameters**:
- `name`: Folder name (supports Arabic/Unicode)
- `parent`: Parent folder code (optional, omit for root)

**Response**:
```json
{
  "msg": "OK",
  "status": 200,
  "result": {
    "foldercode": "xyz789abc",
    "name": "Folder Name",
    "parent": "parent_code_or_null"
  }
}
```

**Note**: If folder already exists, returns existing folder code

**Used in Script**: `get_or_create_folder_structure()` function

**Implementation**:
```python
import requests

def create_folder(name, parent_code=None, api_key=None):
    url = f"https://doodstream.com/api/folder/create?key={api_key}"
    params = {"name": name}
    
    if parent_code:
        params["parent"] = parent_code
    
    response = requests.get(url, params=params)
    result = response.json()
    
    # Extract folder code from response
    if 'result' in result:
        folder_data = result['result']
        if isinstance(folder_data, list):
            folder_code = folder_data[0].get('foldercode') or folder_data[0].get('id')
        elif isinstance(folder_data, dict):
            folder_code = folder_data.get('foldercode') or folder_data.get('id')
        return folder_code
    
    return None
```

---

### 5. Move File to Folder

**Endpoint**: `/api/file/move`  
**Method**: GET  
**Purpose**: Move uploaded file to folder

**Request**:
```
GET https://doodstream.com/api/file/move?key=YOUR_API_KEY&filecode=FILECODE&foldercode=FOLDERCODE
```

**Parameters**:
- `filecode`: File code from upload
- `foldercode`: Destination folder code

**Response**:
```json
{
  "msg": "OK",
  "status": 200
}
```

**Used in Script**: After rename, move to Category/Series folder

**Implementation**:
```python
import requests

def move_to_folder(filecode, foldercode, api_key):
    url = f"https://doodstream.com/api/file/move?key={api_key}"
    params = {
        "filecode": filecode,
        "foldercode": foldercode
    }
    response = requests.get(url, params=params)
    return response.json()
```

---

### 6. Get File Info

**Endpoint**: `/api/file/info`  
**Method**: GET  
**Purpose**: Get file details and URLs

**Request**:
```
GET https://doodstream.com/api/file/info?key=YOUR_API_KEY&filecode=FILECODE
```

**Response**:
```json
{
  "msg": "OK",
  "status": 200,
  "result": {
    "filecode": "abc123xyz",
    "name": "Video Title.mp4",
    "size": "123456789",
    "download_url": "https://doodstream.com/d/abc123xyz",
    "protected_embed": "https://doodstream.com/e/abc123xyz"
  }
}
```

**Used in Script**: To get watch/download URLs after upload

---

## Complete Upload Flow

```python
import requests
import time

def complete_upload_flow(file_path, category_name, series_name, video_title, api_key):
    """
    Complete workflow for uploading video to DoodStream with folder structure
    """
    
    # Step 1: Upload file to root
    print("Uploading file...")
    upload_url = f"https://doodstream.com/api/upload?key={api_key}"
    files = {"file": open(file_path, "rb")}
    upload_response = requests.post(upload_url, files=files).json()
    
    # Extract filecode (handle both list and dict)
    result = upload_response.get('result')
    if isinstance(result, list):
        filecode = result[0]['filecode']
    elif isinstance(result, dict):
        filecode = result.get('filecode') or result.get('id')
    else:
        raise Exception("Unexpected upload response")
    
    print(f"Uploaded! Filecode: {filecode}")
    
    # Step 2: Rename file
    print("Renaming file...")
    time.sleep(2)  # Wait for upload to process
    rename_url = f"https://doodstream.com/api/rename?key={api_key}"
    rename_params = {"filecode": filecode, "title": video_title}
    rename_response = requests.get(rename_url, params=rename_params).json()
    
    if rename_response.get('msg') != 'OK':
        print(f"Warning: Rename may have failed: {rename_response}")
    
    # Step 3: Create/get category folder
    print(f"Creating category folder: {category_name}")
    category_code = create_folder(category_name, None, api_key)
    time.sleep(1)  # Rate limiting
    
    # Step 4: Create/get series folder inside category
    print(f"Creating series folder: {series_name}")
    series_code = create_folder(series_name, category_code, api_key)
    time.sleep(1)  # Rate limiting
    
    # Step 5: Move file to series folder
    print("Moving file to folder...")
    move_url = f"https://doodstream.com/api/file/move?key={api_key}"
    move_params = {"filecode": filecode, "foldercode": series_code}
    move_response = requests.get(move_url, params=move_params).json()
    
    if move_response.get('msg') != 'OK':
        raise Exception(f"Move failed: {move_response}")
    
    # Step 6: Get final URLs
    watch_url = f"https://doodstream.com/e/{filecode}"
    download_url = f"https://doodstream.com/d/{filecode}"
    
    return {
        "filecode": filecode,
        "watch_url": watch_url,
        "download_url": download_url,
        "category": category_name,
        "series": series_name
    }


def create_folder(name, parent_code, api_key):
    """Helper function to create folder and extract code"""
    url = f"https://doodstream.com/api/folder/create?key={api_key}"
    params = {"name": name}
    if parent_code:
        params["parent"] = parent_code
    
    response = requests.get(url, params=params).json()
    result = response.get('result')
    
    # Handle different response formats
    if isinstance(result, list):
        data = result[0]
    elif isinstance(result, dict):
        data = result
    else:
        raise Exception(f"Unexpected folder response: {response}")
    
    # Extract folder code (can be 'foldercode' or 'id')
    folder_code = data.get('foldercode') or data.get('id')
    return folder_code
```

---

## Error Handling

### Common Errors

| HTTP Status | Error | Solution |
|-------------|-------|----------|
| 400 | Invalid parameters | Check filecode, foldercode, title |
| 401 | Invalid API key | Verify API key in dashboard |
| 403 | Permission denied | Check API access enabled |
| 429 | Rate limited | Add delays between requests |
| 500 | Server error | Retry after delay |

### Response Format Variations

The DoodStream API can return different formats:

**Format 1 - List** (most common):
```json
{
  "msg": "OK",
  "status": 200,
  "result": [{"filecode": "abc123"}]
}
```

**Format 2 - Dict**:
```json
{
  "msg": "OK",
  "status": 200,
  "result": {"filecode": "abc123"}
}
```

**Format 3 - Nested**:
```json
{
  "msg": "OK",
  "status": 200,
  "result": [{"result": {"foldercode": "xyz789"}}]
}
```

**Script handles all formats**:
```python
def extract_code(response):
    result = response.get('result')
    
    if isinstance(result, list):
        # Try first item
        item = result[0]
        if isinstance(item, dict):
            return item.get('filecode') or item.get('foldercode') or item.get('id')
        elif isinstance(item, str):
            return item
    
    elif isinstance(result, dict):
        return result.get('filecode') or result.get('foldercode') or result.get('id')
    
    return None
```

---

## Rate Limiting

### Best Practices

1. **Wait between API calls**:
   - Upload → Rename: 2 seconds
   - Between folder operations: 1 second
   - Between uploads: 1-2 seconds

2. **Batch processing**:
   - Process 5-10 videos at a time
   - Wait 5-10 seconds between batches

3. **Retry logic**:
   ```python
   import time
   
   def upload_with_retry(file_path, api_key, max_retries=2):
       for attempt in range(max_retries):
           try:
               return upload_file(file_path, api_key)
           except Exception as e:
               if attempt < max_retries - 1:
                   print(f"Upload failed, retrying in 5s...")
                   time.sleep(5)
               else:
                   raise
   ```

---

## Testing

### Test Upload Script

```python
import requests

API_KEY = "your_api_key_here"

# Test 1: Account Info
response = requests.get(f"https://doodstream.com/api/account/info?key={API_KEY}")
print("Account:", response.json())

# Test 2: Create Folder
response = requests.get(
    f"https://doodstream.com/api/folder/create?key={API_KEY}&name=Test Folder"
)
print("Folder:", response.json())

# Test 3: Upload File (requires actual file)
# files = {"file": open("test.mp4", "rb")}
# response = requests.post(f"https://doodstream.com/api/upload?key={API_KEY}", files=files)
# print("Upload:", response.json())
```

---

## References

- **Official Documentation**: https://doodstream.com/api-docs
- **API Base URL**: https://doodstream.com/api
- **Support**: Check DoodStream dashboard for API support

---

**Last Updated**: 2026-05-14  
**Version**: 2.0
