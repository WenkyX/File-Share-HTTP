
# File Transfer over HTTP

A simple Python-based HTTP server for sharing files and directories over a network. This project allows users to upload, download, and browse files through a web interface.

## Features

- **File Upload**: Upload files to the server via a web interface.
- **File Download**: Download individual files or directories as ZIP archives.
- **Directory Browsing**: Browse directories and view file properties including file/folder size and path.
- **Drag-and-Drop Support**: Drag and drop files directly into the web interface for upload.


## Requirements

- Python 3.7 or higher
- Required Python libraries:
  - `http.server` (built-in)
  - `cgi` (built-in)
  - `os` (built-in)
  - `json` (built-in)
  - `zipfile` (built-in)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/WenkyX/File-Share-HTTP.git
   cd File-Share-HTTP
   ```
2. Run the server:
    ```bash
    python3 share.py
    ```
    a GUI will pop up prompting you to enter in the path and port you want to use, once configured simply click the "Start server" button,
    
4. Open your browser on other devices in the same network and navigate to
    `http://192.xxx.xxx.xxx:[PORT]`

