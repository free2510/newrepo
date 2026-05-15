# 📡 DoodStream API Reference

Complete reference for DoodStream API integration used in the video scraper.

---

## Overview

The script uses the official [DoodStream API](https://doodstream.com/api-docs) to:
- Upload video files
- Create folder structure (Category → Series → Video)
- Rename files with Arabic titles
- Move files to folders
- List existing folders

**Base URL**: `https://doodapi.co/api`  (Updated from doodapi.com)  
**Authentication**: API Key via query parameter `?key=YOUR_API_KEY`

---

## API Endpoints Used

### 1. List Folders

**Endpoint**: `/api/folder/list`  (Updated from /api/list_folders)  
**Method**: GET  
**Purpose**: List all folders/files in root or specific folder

**Request (Root)**:
```
GET https://doodapi.co/api/folder/list?key=YOUR_API_KEY
```

**Request (Specific Folder)**:
```
GET https://doodapi.co/api/folder/list?key=YOUR_API_KEY&fld_id=FOLDER_ID
```

**Parameters**:
- `key`: Your API key
- `fld_id`: (Optional) Folder ID to list contents of. If omitted, lists root folders.

**Response**:
```json
{
  "msg": "OK",
  "status": 200,
  "result": {
    "folders": [
      {
        "name": "Folder Name",
        "code": "xyz789",
        "fld_id": "123"
      }
    ],
    "files": [
      {
        "name": "video.mp4",
        "filecode": "abc123",
        "download_url": "https://dood.to/d/abc123"
      }
    ]
  }
}
```

**Used in Script**: `get_or_create_folder_structure()` - Check if category/series folders exist

**Important Notes**:
- Response structure is `{"result": {"folders": [...], "files": [...]}}` NOT a flat array
- Folder IDs are in `fld_id` field (not `id`)
- Folder codes are in `code` field (not `foldercode`)
- Use either `fld_id` or `code` for folder operations

---

### 2. Create Folder

**Endpoint**: `/api/folder/create`  
**Method**: GET  
**Purpose**: Create new folder (category or series)

**Request**:
```
GET https://doodapi.co/api/folder/create?key=YOUR_API_KEY&name=FOLDER_NAME&parent_id=PARENT_ID
```

**Parameters**:
- `key`: Your API key
- `name`: Folder name (URL-encoded for Arabic support) - **Required**
- `parent_id`: (Optional) Parent folder ID for nested folders. Omit for root-level folders.

**Response**:
```json
{
  "msg": "OK",
  "status": 200,
  "result": {
    "fld_id": "1234567"
  }
}
```

**Note**: The response contains `fld_id` directly in the result object.

**Used in Script**: `get_or_create_folder_structure()` - Create category and series folders

---

### 3. Upload File

**Endpoint**: `/api/upload`  
**Method**: POST (multipart/form-data)  
**Purpose**: Upload video file to root directory

**Request**:
```
POST https://doodapi.co/api/upload?key=YOUR_API_KEY
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

**Used in Script**: `upload_to_doodstream()` function via `dood.local_upload()`

---

### 4. Rename File

**Endpoint**: `/api/file/rename`  
**Method**: GET  
**Purpose**: Rename uploaded file with proper title

**Request**:
```
GET https://doodapi.co/api/file/rename?key=YOUR_API_KEY&file_code=FILECODE&title=NEW_TITLE
```

**Parameters**:
- `key`: Your API key
- `file_code`: File code from upload response
- `title`: New filename (URL-encoded for Arabic support)

**Response**:
```json
{
  "msg": "OK",
  "status": 200
}
```

**Used in Script**: After upload, before moving to folder

---

### 5. Move File to Folder

**Endpoint**: `/api/file/move`  
**Method**: GET  
**Purpose**: Move uploaded file to folder

**Request**:
```
GET https://doodapi.co/api/file/move?key=YOUR_API_KEY&file_code=FILECODE&fld_id=FOLDER_ID
```

**Parameters**:
- `key`: Your API key
- `file_code`: File code from upload
- `fld_id`: Destination folder ID

**Response**:
```json
{
  "msg": "OK",
  "status": 200
}
```

**Used in Script**: After rename, move to Category/Series folder

---

## Error Handling

### Common Errors

| HTTP Status | Error | Solution |
|-------------|-------|----------|
| 400 | Invalid parameters | Check filecode, fld_id, title encoding |
| 401 | Invalid API key | Verify API key in dashboard |
| 403 | Permission denied | Check API access enabled |
| 404 | Not Found | Wrong endpoint (use doodapi.co not doodapi.com) |
| 429 | Rate limited | Add delays between requests (1-2 seconds) |
| 500 | Server error | Retry after delay |

---

## References

- **Official Documentation**: https://doodstream.com/api-docs
- **API Base URL**: https://doodapi.co/api  (Updated from doodapi.com)
- **Support**: Check DoodStream dashboard for API support

---

**Last Updated**: 2026-05-15  
**Version**: 3.0

### Changelog v3.0 (Latest Update)

- **Fixed API domain**: Changed from `doodapi.com` to `doodapi.co` (correct domain)
- **Fixed folder list endpoint**: Changed from `/api/list_folders` to `/api/folder/list`
- **Fixed response parsing**: Updated to handle `{"result": {"folders": [...]}}` structure
- **Fixed folder create parameter**: Changed from `parent` to `parent_id` (correct API param)
- **Added strict folder requirement**: Upload now aborts if folder structure cannot be created
- **Added cleanup logic**: Files are deleted if they cannot be moved to correct folder
- **Updated documentation**: All examples now use correct endpoints and response formats

### Changelog v2.2

- Added `response.raise_for_status()` to all API calls for better error handling
- Added debug logging for folder creation responses
- Fixed Google Sheets URLs to return clean URLs instead of JSON objects
- Improved error messages for HTTP and JSON parsing errors
- Updated documentation with new error handling patterns
