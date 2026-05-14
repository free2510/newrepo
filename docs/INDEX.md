# 📚 Video Scraper Project Documentation

Welcome to the complete documentation for the **Video Scraper & Uploader** project.

## 📖 Documentation Index

### Main Documentation
- **[README.md](README.md)** - Complete project guide and overview
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and all changes
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Installation and configuration instructions
- **[WORKFLOW.md](WORKFLOW.md)** - Detailed workflow explanation
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[API_REFERENCE.md](API_REFERENCE.md)** - DoodStream API integration details

### Quick Reference
- **Google Sheets Setup**: See [SETUP_GUIDE.md](SETUP_GUIDE.md) → Google Sheets Configuration
- **DoodStream API Key**: See [SETUP_GUIDE.md](SETUP_GUIDE.md) → Authentication
- **Folder Structure**: See [WORKFLOW.md](WORKFLOW.md) → DoodStream Organization
- **Common Errors**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 🎯 Latest Updates (v2.0)

### ✅ Folder Structure Fixed
Videos now upload to the correct folder structure in DoodStream:
```
📁 Category (e.g., رمضان 2026 - مسلسلات)
  └── 📁 Series (e.g., مسلسل حكاية نرجس)
      └── 🎬 Video (e.g., مسلسل حكاية نرجس الحلقة 7 السابعة)
```

### 🔧 Key Improvements
- Uses DoodStream API `/api/file/clone?fld_id=` endpoint to move files to folders
- Renames files with clean Arabic titles before moving
- Deletes original from root after successful copy
- Proper error handling with 10-15 second timeouts
- No more duplicate rows in Google Sheets

### 📊 Workflow
1. Download video to local temp folder (`/content/temp_videos`)
2. Upload to DoodStream root
3. Rename with Arabic title
4. Copy to series folder using API
5. Delete from root
6. Update Google Sheets (single row, final status)
7. Delete local temp file

---
*Last Updated: May 2026 | Version: 2.0*

## 🚀 Quick Start

1. **Setup**: Follow [SETUP_GUIDE.md](SETUP_GUIDE.md)
2. **Configure**: Edit API keys and sheet ID in the script
3. **Run**: Execute in Google Colab
4. **Monitor**: Check Google Sheet for real-time updates

## 📁 Project Structure

```
/workspace/
├── docs/
│   ├── INDEX.md (this file)
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── SETUP_GUIDE.md
│   ├── WORKFLOW.md
│   ├── TROUBLESHOOTING.md
│   └── API_REFERENCE.md
├── video_scraper_final.py (main script)
├── .gitignore
└── __pycache__/
```

## 🔗 External Resources

- [DoodStream API Documentation](https://doodstream.com/api-docs)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [Google Drive API](https://developers.google.com/drive/api)

---

**Last Updated**: 2026-05-14  
**Version**: 2.0
