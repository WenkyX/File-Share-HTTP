import http.server
import socketserver
import socket
import os
import zipfile
import io
from urllib.parse import parse_qs, urlparse, unquote
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-port", type=int, help="Port number")
parser.add_argument("-path", type=str, help="Path to directory")

args = parser.parse_args()

def get_local_ip():
    try:
        # Doesn't actually connect to the internet, just figures out your outbound IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS (no data sent)
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        return f"Error: {e}"



# print(f"Port: {args.port}")
# print(f"Path: {args.path}")

PORT = args.port or 8700
DIRECTORY_TO_SERVE = args.path or "./"
os.chdir(DIRECTORY_TO_SERVE)
HTML_TEMPLATE = os.path.join(os.path.dirname(__file__), "index.html")
# HTML_TEMPLATE = """
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <meta charset="UTF-8">
#         <title>Directory Listing</title>
#         <style>
#                 body {
#                     background-color: rgb(30, 34, 41);
#                     color: white
#                 }
#                 a {
#                     color: #999999;
#                     font-weight: bold;
#                     text-decoration:none;
#                 }
#                 .fileList {
#                     border: 1px solid gray;
#                     display: flex;
#                     width: fit-content;
#                     padding: 10px;
#                 }
#                 .files{
#                     border: 2px solid gray;
#                     border-radius: 5px;
#                     /* padding: 10px; */
#                     list-style-type: none;
#                     margin: 5px;
#                 }
#                 ul{
#                     padding:0;
#                     display:flex;
#                     flex-wrap: wrap;
#                 }
#                 #contextMenu {
#                     position: absolute;
#                     display: none;
#                     background-color: #fff;
#                     border: 1px solid #ccc;
#                     box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
#                     z-index: 1000;
#                 }
#                 #contextMenu a {
#                     display: block;
#                     padding: 10px;
#                     text-decoration: none;
#                     color: black;
#                 }
#                 #contextMenu a:hover {
#                     background-color: #ddd;
#                 }

#                 img {
#                     width: 50px;
#                     height:50px;
#                     filter: invert(1);
#                 }
#                 .icon {
#                     flex-direction: column;
#                     display: flex;
#                     align-items: center;
#                     margin: 10px;
#                 }
#         </style>
#         <script>
#             document.addEventListener("DOMContentLoaded", function() {
#                 const contextMenu = document.getElementById("contextMenu");
#                 let currentItem = null;

#                 // Function to display the context menu
#                 document.addEventListener("contextmenu", function(event) {
#                     event.preventDefault();
#                     currentItem = event.target.closest(".file");
#                     console.log(currentItem);


#                     if (currentItem && currentItem.classList.contains("file")) {
#                         contextMenu.style.display = "block";
#                         contextMenu.style.left = `${event.pageX}px`;
#                         contextMenu.style.top = `${event.pageY}px`;
#                     }
#                 });

#                 // Hide the context menu if clicking elsewhere
#                 document.addEventListener("click", function() {
#                     contextMenu.style.display = "none";
#                 });

#                 // Add the "Download as ZIP" action
#                 document.getElementById("downloadZip").addEventListener("click", function() {
#                     if (currentItem) {
#                         // Use the item name or path to download the ZIP
#                         const itemName = currentItem.getAttribute('href') + "/";
#                         console.log(itemName);
#                         window.location.href = `/download_zip?file=${encodeURIComponent(itemName)}`;
#                         contextMenu.style.display = "none";
#                     }
#                 });
#                 document.getElementById("downloadFile").addEventListener("click", function() {
#                     console.log(currentItem);
#                     const link = document.createElement('a');
#                     link.href = currentItem.getAttribute('href');
#                     link.download = currentItem.id || '';
#                     document.body.appendChild(link);
#                     link.click();
#                     document.body.removeChild(link);
#                 });
#             });

#             // Dynamically load files and make them clickable for the context menu
#             fetch("/file_list")
#                 .then(response => response.json())
#                 .then(files => {
#                     const fileListDiv = document.getElementById("fileList");
#                     files.forEach(file => {
#                         const fileElement = document.createElement("div");
#                         fileElement.textContent = file;
#                         fileElement.classList.add("file");
#                         fileListDiv.appendChild(fileElement);
#                     });
#                 });
#         </script>
#     </head>
#     <body>
#         <div id="contextMenu">
#             <a href="#" id="downloadZip">Download as ZIP</a>
#             <a href="#" id="downloadFile">Download File</a>
#         </div>
#         <h2>Contents of '{{myfolder}}'</h2>
#             <div class="fileList">
#                 <ul>
#                     {{file_list}}
#                 </ul>
#             </div>
#         <br>
#         <!-- <a href="/download"><button>Download All as ZIP</button></a> -->
#     </body>
#     </html>
# """

# FOLDER_SVG = "data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPCEtLSBTdmcgVmVjdG9yIEljb25zIDogaHR0cDovL3d3dy5vbmxpbmV3ZWJmb250cy5jb20vaWNvbiAtLT4KPCFET0NUWVBFIHN2ZyBQVUJMSUMgIi0vL1czQy8vRFREIFNWRyAxLjEvL0VOIiAiaHR0cDovL3d3dy53My5vcmcvR3JhcGhpY3MvU1ZHLzEuMS9EVEQvc3ZnMTEuZHRkIj4KPHN2ZyB2ZXJzaW9uPSIxLjEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4IiB2aWV3Qm94PSIwIDAgMjU2IDI1NiIgZW5hYmxlLWJhY2tncm91bmQ9Im5ldyAwIDAgMjU2IDI1NiIgeG1sOnNwYWNlPSJwcmVzZXJ2ZSI+CjxtZXRhZGF0YT4gU3ZnIFZlY3RvciBJY29ucyA6IGh0dHA6Ly93d3cub25saW5ld2ViZm9udHMuY29tL2ljb24gPC9tZXRhZGF0YT4KPGc+PGc+PGc+PHBhdGggc3Ryb2tlLXdpZHRoPSIyIiBmaWxsLW9wYWNpdHk9IjAiIHN0cm9rZT0iIzAwMDAwMCIgIGQ9Ik0yMC4zLDM4Yy0yLjYsMS4zLTQuNSwyLjgtNi4yLDQuOWMtNC41LDUuNy00LjIsMC4yLTQuMSw4OC40bDAuMiw3OS4xbDEuOCwzYzEuMiwxLjgsMywzLjYsNC44LDQuOGwzLDEuOGg5Mi4xaDkyLjFsMy42LTEuOGM0LjQtMi4yLDkuOS03LjYsMTEuNy0xMS42YzAuNy0xLjcsNy4xLTI0LjUsMTQuMS01MC45YzExLjYtNDMuNCwxMi44LTQ4LjEsMTIuNS01MS40Yy0wLjQtNC43LTIuOC04LjUtNi43LTExYy0yLjgtMS44LTMuMy0xLjgtMTAuNy0ybC03LjctMC4ybC0wLjQtNC43Yy0wLjUtNy0yLjMtMTEuMS02LjctMTUuNmMtMi42LTIuNi00LjgtNC4xLTcuMy01LjFsLTMuNi0xLjVsLTY2LjEtMC4ybC02Ni4xLTAuMmwtMC4yLTcuNGMtMC4yLTYuMi0wLjQtNy44LTEuNi05LjljLTIuMS00LjEtNC43LTYuNy04LjctOC43bC0zLjctMS44SDQwLjJIMjQuMUwyMC4zLDM4eiBNNTcuMSw0NC42YzEuNiwwLjgsMy4zLDIuMyw0LjIsMy44YzEuNiwyLjQsMS42LDIuNywxLjgsMTNsMC4yLDEwLjVoNjkuM2M2OS4yLDAsNjkuMywwLDcyLDEuM2MzLDEuNSw2LjEsNC42LDcuMyw3LjZjMC41LDEuMiwwLjgsMy44LDAuOCw2djMuOWgtNzcuNWMtNDkuNSwwLTc4LjUsMC4yLTgwLjYsMC42Yy0xLjgsMC40LTQuNywxLjMtNi41LDIuMWMtNCwxLjgtOS44LDcuNC0xMS42LDExLjNjLTAuNywxLjUtNS4zLDE3LjktMTAuMiwzNi4ybC05LDMzLjRsLTAuMi02MC4xYy0wLjEtNDIuMSwwLTYwLjksMC41LTYyLjVjMC44LTIuOCwzLjktNi40LDYuNC03LjRjMS4zLTAuNiw1LjYtMC44LDE2LTAuOEM1My40LDQzLjQsNTQuNiw0My40LDU3LjEsNDQuNnogTTIzNC45LDk5LjRjMi4xLDEsMy45LDMuOSwzLjksNi4yYzAsMS45LTI1LjQsOTYuMi0yNi40LDk4LjNjLTEuNCwyLjctNSw1LjktOC40LDcuNWwtMy4xLDEuNWgtODkuMmMtNzYuOSwwLTg5LjQtMC4xLTkwLjktMC45Yy0yLjEtMS4xLTMuOS00LjctMy42LTcuMmMwLjUtMy45LDI1LjQtOTUsMjYuNS05Ny4zYzEuNS0zLDYuMS03LDkuMy04LjFjMi4yLTAuNywxNC41LTAuOSw5MS4xLTAuOUMyMjMuOSw5OC41LDIzMy4xLDk4LjYsMjM0LjksOTkuNHoiLz48L2c+PC9nPjwvZz4KPC9zdmc+"
FOLDER_SVG = "data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPCEtLSBTdmcgVmVjdG9yIEljb25zIDogaHR0cDovL3d3dy5vbmxpbmV3ZWJmb250cy5jb20vaWNvbiAtLT4KPCFET0NUWVBFIHN2ZyBQVUJMSUMgIi0vL1czQy8vRFREIFNWRyAxLjEvL0VOIiAiaHR0cDovL3d3dy53My5vcmcvR3JhcGhpY3MvU1ZHLzEuMS9EVEQvc3ZnMTEuZHRkIj4KPHN2ZyB2ZXJzaW9uPSIxLjEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4IiB2aWV3Qm94PSIwIDAgMjU2IDI1NiIgZW5hYmxlLWJhY2tncm91bmQ9Im5ldyAwIDAgMjU2IDI1NiIgeG1sOnNwYWNlPSJwcmVzZXJ2ZSI+CjxtZXRhZGF0YT4gU3ZnIFZlY3RvciBJY29ucyA6IGh0dHA6Ly93d3cub25saW5ld2ViZm9udHMuY29tL2ljb24gPC9tZXRhZGF0YT4KPGc+PGc+PGc+PHBhdGggZmlsbD0iIzAwMDAwMCIgZD0iTTIwLjMsMzhjLTIuNiwxLjMtNC41LDIuOC02LjIsNC45Yy00LjUsNS43LTQuMiwwLjItNC4xLDg4LjRsMC4yLDc5LjFsMS44LDNjMS4yLDEuOCwzLDMuNiw0LjgsNC44bDMsMS44aDkyLjFoOTIuMWwzLjYtMS44YzQuNC0yLjIsOS45LTcuNiwxMS43LTExLjZjMC43LTEuNyw3LjEtMjQuNSwxNC4xLTUwLjljMTEuNi00My40LDEyLjgtNDguMSwxMi41LTUxLjRjLTAuNC00LjctMi44LTguNS02LjctMTFjLTIuOC0xLjgtMy4zLTEuOC0xMC43LTJsLTcuNy0wLjJsLTAuNC00LjdjLTAuNS03LTIuMy0xMS4xLTYuNy0xNS42Yy0yLjYtMi42LTQuOC00LjEtNy4zLTUuMWwtMy42LTEuNWwtNjYuMS0wLjJsLTY2LjEtMC4ybC0wLjItNy40Yy0wLjItNi4yLTAuNC03LjgtMS42LTkuOWMtMi4xLTQuMS00LjctNi43LTguNy04LjdsLTMuNy0xLjhINDAuMkgyNC4xTDIwLjMsMzh6IE01Ny4xLDQ0LjZjMS42LDAuOCwzLjMsMi4zLDQuMiwzLjhjMS42LDIuNCwxLjYsMi43LDEuOCwxM2wwLjIsMTAuNWg2OS4zYzY5LjIsMCw2OS4zLDAsNzIsMS4zYzMsMS41LDYuMSw0LjYsNy4zLDcuNmMwLjUsMS4yLDAuOCwzLjgsMC44LDZ2My45aC03Ny41Yy00OS41LDAtNzguNSwwLjItODAuNiwwLjZjLTEuOCwwLjQtNC43LDEuMy02LjUsMi4xYy00LDEuOC05LjgsNy40LTExLjYsMTEuM2MtMC43LDEuNS01LjMsMTcuOS0xMC4yLDM2LjJsLTksMzMuNGwtMC4yLTYwLjFjLTAuMS00Mi4xLDAtNjAuOSwwLjUtNjIuNWMwLjgtMi44LDMuOS02LjQsNi40LTcuNGMxLjMtMC42LDUuNi0wLjgsMTYtMC44QzUzLjQsNDMuNCw1NC42LDQzLjQsNTcuMSw0NC42eiBNMjM0LjksOTkuNGMyLjEsMSwzLjksMy45LDMuOSw2LjJjMCwxLjktMjUuNCw5Ni4yLTI2LjQsOTguM2MtMS40LDIuNy01LDUuOS04LjQsNy41bC0zLjEsMS41aC04OS4yYy03Ni45LDAtODkuNC0wLjEtOTAuOS0wLjljLTIuMS0xLjEtMy45LTQuNy0zLjYtNy4yYzAuNS0zLjksMjUuNC05NSwyNi41LTk3LjNjMS41LTMsNi4xLTcsOS4zLTguMWMyLjItMC43LDE0LjUtMC45LDkxLjEtMC45QzIyMy45LDk4LjUsMjMzLjEsOTguNiwyMzQuOSw5OS40eiIvPjwvZz48L2c+PC9nPgo8L3N2Zz4="
UNKNOWN_SVG = "data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiA/PgoKPCEtLSBVcGxvYWRlZCB0bzogU1ZHIFJlcG8sIHd3dy5zdmdyZXBvLmNvbSwgR2VuZXJhdG9yOiBTVkcgUmVwbyBNaXhlciBUb29scyAtLT4KPHN2ZyB3aWR0aD0iODAwcHgiIGhlaWdodD0iODAwcHgiIHZpZXdCb3g9IjAgMCA0MDAgNDAwIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgoKPGRlZnM+Cgo8c3R5bGU+LmNscy0xe2ZpbGw6IzEwMTAxMDt9PC9zdHlsZT4KCjwvZGVmcz4KCjx0aXRsZS8+Cgo8ZyBpZD0ieHh4LXdvcmQiPgoKPHBhdGggY2xhc3M9ImNscy0xIiBkPSJNMzI1LDEwNUgyNTBhNSw1LDAsMCwxLTUtNVYyNWE1LDUsMCwxLDEsMTAsMFY5NWg3MGE1LDUsMCwxLDEsMCwxMFoiLz4KCjxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTMyNSwxNTQuODNhNSw1LDAsMCwxLTUtNVYxMDIuMDdMMjQ3LjkzLDMwSDEwMEEyMCwyMCwwLDAsMCw4MCw1MHY5OC4xN2E1LDUsMCwwLDEtMTAsMFY1MGEzMCwzMCwwLDAsMSwzMC0zMEgyNTBhNSw1LDAsMCwxLDMuNTQsMS40Nmw3NSw3NUE1LDUsMCwwLDEsMzMwLDEwMHY0OS44M0E1LDUsMCwwLDEsMzI1LDE1NC44M1oiLz4KCjxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTMwMCwzODBIMTAwYTMwLDMwLDAsMCwxLTMwLTMwVjI3NWE1LDUsMCwwLDEsMTAsMHY3NWEyMCwyMCwwLDAsMCwyMCwyMEgzMDBhMjAsMjAsMCwwLDAsMjAtMjBWMjc1YTUsNSwwLDAsMSwxMCwwdjc1QTMwLDMwLDAsMCwxLDMwMCwzODBaIi8+Cgo8cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik0yNzUsMjgwSDEyNWE1LDUsMCwwLDEsMC0xMEgyNzVhNSw1LDAsMCwxLDAsMTBaIi8+Cgo8cGF0aCBjbGFzcz0iY2xzLTEiIGQ9Ik0yMDAsMzMwSDEyNWE1LDUsMCwwLDEsMC0xMGg3NWE1LDUsMCwwLDEsMCwxMFoiLz4KCjxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTMyNSwyODBINzVhMzAsMzAsMCwwLDEtMzAtMzBWMTczLjE3YTMwLDMwLDAsMCwxLDMwLTMwaC4ybDI1MCwxLjY2YTMwLjA5LDMwLjA5LDAsMCwxLDI5LjgxLDMwVjI1MEEzMCwzMCwwLDAsMSwzMjUsMjgwWk03NSwxNTMuMTdhMjAsMjAsMCwwLDAtMjAsMjBWMjUwYTIwLDIwLDAsMCwwLDIwLDIwSDMyNWEyMCwyMCwwLDAsMCwyMC0yMFYxNzQuODNhMjAuMDYsMjAuMDYsMCwwLDAtMTkuODgtMjBsLTI1MC0xLjY2WiIvPgoKPHBhdGggY2xhc3M9ImNscy0xIiBkPSJNMjAzLjM4LDIyMC42OWgtNy42MnYtNS4yN2E3LjE0LDcuMTQsMCwwLDEsMS4wNy00LjE4LDI1LDI1LDAsMCwxLDQuNzEtNC4zNHE1LjU1LTQuMjYsNS41NS05YTcuNTksNy41OSwwLDAsMC0yLjE3LTUuNyw3Ljc1LDcuNzUsMCwwLDAtNS42NC0yLjExcS04LDAtOS40OSwxMS4xM2wtOC41Mi0xLjUycS43OC04LjMyLDYuMTUtMTMuMDdhMTguNzgsMTguNzgsMCwwLDEsMTIuODctNC43NSwxNy42NywxNy42NywwLDAsMSwxMi4zNCw0LjQzLDE0LjMsMTQuMywwLDAsMSw0Ljg4LDExLDE0LjgyLDE0LjgyLDAsMCwxLTEuMzUsNi4yMywxNC40OCwxNC40OCwwLDAsMS0zLjA3LDQuNTcsOTIsOTIsMCwwLDEtNy4yNyw1LjY4LDUuNTIsNS41MiwwLDAsMC0yLDIuMjFBMTYsMTYsMCwwLDAsMjAzLjM4LDIyMC42OVptMS41Niw1LjU1VjIzNmgtOS4xOHYtOS43N1oiLz4KCjwvZz4KCjwvc3ZnPg=="

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('/folder.svg') or self.path.endswith('/unknown.svg'):
            # Serve the SVG files from the directory where the Python script is located
            file_path = os.path.join(os.path.dirname(__file__), os.path.basename(self.path))
            # print("==================================================================================================================================")
            # print(os.path.basename(self.path))
            # print("==================================================================================================================================")
            # print(file_path)
            if os.path.exists(file_path):
                # Send SVG file
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
        elif self.path == '/':
            return self.serve_directory_list()
        elif os.path.isdir(self.path.lstrip('/').replace(' ', '%20')):  # Check if path is a directory
            return self.serve_directory(self.path)  # Serve subdirectory
        elif self.path.startswith('/download_zip'):
            query_components = parse_qs(urlparse(self.path).query)
            file_name = query_components.get("file", [None])[0]

            if file_name:
                zip_file = self.create_zip([file_name])
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f"attachment; filename={file_name}.zip")
                self.send_header("Content-Length", str(len(zip_file.getvalue())))
                self.end_headers()
                self.wfile.write(zip_file.getvalue())
            else:
                self.send_error(400, "Bad Request: No file specified")
        else:
            return super().do_GET()

    def create_zip(self, items):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item in items:
                item = unquote(item).strip("/")
                item_path = os.path.join(os.getcwd(), item)
                base_dir = os.path.basename(item)  # Get just the final part (like "c")

                if os.path.isfile(item_path):
                    zipf.write(item_path, arcname=os.path.basename(item_path))
                elif os.path.isdir(item_path):
                    for root, _, files in os.walk(item_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            # Make arcname relative to the base_dir
                            relative_path = os.path.relpath(full_path, start=os.path.dirname(item_path))
                            zipf.write(full_path, arcname=relative_path)
                else:
                    print(f"Warning: {item_path} does not exist or is not a valid file or directory.")
        zip_buffer.seek(0)
        return zip_buffer

    def serve_directory(self, path):
        """Serve the directory content with an index.html if available"""
        dir_path = os.path.join(os.getcwd(), path.lstrip('/'))

        # Check if index.html exists in the subdirectory
        index_file_path = os.path.join(dir_path, "index.html")
        if os.path.exists(index_file_path):
            try:
                with open(index_file_path, "r", encoding="utf-8") as f:
                    html = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            except FileNotFoundError:
                self.send_error(500, "Internal Server Error")
        else:
            # If no index.html, fall back to listing files
            self.serve_directory_list(dir_path)

    def serve_directory_list(self,dir_path=None):

        if dir_path is None:
            dir_path = os.getcwd()

        try:
            file_list = [
                os.path.relpath(os.path.join(dir_path, name), os.getcwd())
                for name in os.listdir(dir_path)
            ]
            file_list.sort()
        except OSError:
            self.send_error(404, "Directory not found")
            return

        try:
            with open(HTML_TEMPLATE, "r", encoding="utf-8") as f:
                html = f.read()
        except Exception as e:
            # print("erorr ", e)
            html = HTML_TEMPLATE

        list_items = ""
        # print("==================================================================================================================================")
        # print(file_list)
        # print(dir_path)
        # print(os.getcwd())
        # print(os.path.isdir((dir_path + file_list[0])))
        # print(os.path.relpath(os.path.join(dir_path, file_list[0]), os.getcwd()))
        # print("==================================================================================================================================")
        list_items += f"""
            <li class="files">
                <a class="file" href=".." id="..">
                    <div class=icon>
                        <img src="{FOLDER_SVG}">
                        <span>..<span>
                    </div>
                </a>
            </li>
            """
        for name in file_list:
            display_name = os.path.basename(name) + "/" if os.path.isdir(name) else os.path.basename(name)
            href = f"/{name}"
            # icon_href = 
            icon_href = FOLDER_SVG if os.path.isdir(name) else UNKNOWN_SVG
            list_items += f"""
            <li class="files">
                <a class="file" href="{href}" id="{display_name}">
                    <div class=icon>
                        <img src="{icon_href}">
                        <div class="fileName">
                            <span>{display_name}</span>
                        </div>
                    </div>
                </a>
            </li>
            """

        html = html.replace("{{file_list}}", list_items)
        html = html.replace("{{myfolder}}", DIRECTORY_TO_SERVE)

        encoded = html.encode("utf-8", "surrogateescape")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        localIp = get_local_ip()
        print("Local IP:", localIp)
        print(f"Serving {DIRECTORY_TO_SERVE} at port {PORT}")
        print(f"Open http://{localIp}:{PORT} in your browser")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            httpd.shutdown()
            httpd.server_close()
