import http.server
import socketserver
import socket
import os
import zipfile
import io
from urllib.parse import parse_qs, urlparse, unquote
import argparse
import cgi
import json

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
        print("No local network detected")
        return "Error"



# print(f"Port: {args.port}")
# print(f"Path: {args.path}")

PORT = args.port or 8700
DIRECTORY_TO_SERVE = args.path or "./"
BASE_DIR = os.path.abspath(DIRECTORY_TO_SERVE)
os.chdir(DIRECTORY_TO_SERVE)
HTML_TEMPLATE = os.path.join(os.path.dirname(__file__), "index.html")

curpath = None
class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global curpath
        if self.path.endswith('/folder.svg') or self.path.endswith('/unknown.svg') or self.path.endswith('/upload.svg'):
            # Serve the SVG files from the directory where the Python script is located
            file_path = os.path.join(os.path.dirname(__file__), os.path.basename(self.path))
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
            curpath = os.path.join(BASE_DIR, self.path.lstrip('/'))
            print(curpath)
            print("1")
            return self.serve_directory_list()
        elif os.path.isdir(self.path.lstrip('/').replace('%20', ' ')):  # Check if path is a directory
            curpath = os.path.join(BASE_DIR, self.path.lstrip('/'))
            print(curpath)
            print("2")
            return self.serve_directory(self.path + "/")  # Serve subdirectory
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
        elif self.path.startswith('/get-file-size'):
            query_components = parse_qs(urlparse(self.path).query)
            folder = query_components.get("path", [None])[0]
            # print(folder)
            # print(query_components)

            abspath = os.path.abspath(folder)
            basename = os.path.basename(os.path.normpath(folder))
            # print(basename)

            if os.path.isdir(folder):
                size = self.get_folder_size(folder)
                response = {'size_bytes': self.format_size(size), 'abspath': abspath, 'basename': basename}
            elif os.path.isfile(folder):
                size = self.get_file_size(folder)
                response = {'size_bytes': self.format_size(size), 'abspath': abspath, 'basename': basename}
            else:
                response = {'error': 'Path not found'}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            return super().do_GET()
        
    #FIX test and check for bugs 
    def do_POST(self):
        global curpath 
        if self.path == '/upload': 
            print(curpath)
            print("3")

            # return
            content_type = self.headers['Content-Type']
            if 'multipart/form-data' in content_type:
                fs = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD':'POST',
                             'CONTENT_TYPE':self.headers['Content-Type']}
                )

                # 'file' is the field name from the frontend
                if 'file' in fs:
                    uploaded_file = fs['file']
                    filename = uploaded_file.filename
                    data = uploaded_file.file.read()

                    # Save the uploaded file
                    with open(os.path.join(curpath, filename), 'wb') as f:
                        f.write(data)

                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"File uploaded successfully.")
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"No file uploaded.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid Content-Type.")

    def get_folder_size(self, path):
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except FileNotFoundError:
                        # File might disappear between walk and getsize
                        pass
        except Exception as e:
            print(e)
        return total_size
    def get_file_size(self, path):
        total_size = 0
        try:
            try:
                total_size += os.path.getsize(path)
            except FileNotFoundError:
                pass
        except Exception as e:
            print(e)
        return total_size

    def format_size(self, bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} PB"

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
        try:
            dir_path = dir_path.replace("%20", " ")
        except:
            pass
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
                        <img src="folder.svg">
                        <span>..<span>
                    </div>
                </a>
            </li>
            """
        for name in file_list:
            display_name = os.path.basename(name) + "/" if os.path.isdir(name) else os.path.basename(name)
            href = f"/{name}/" if os.path.isdir(name) else f"/{name}"
            # icon_href = 
            icon_href = "folder.svg" if os.path.isdir(name) else "unknown.svg"
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
        if localIp == "Error":
            print(f"Serving {DIRECTORY_TO_SERVE} at 127.0.0.0 instead with Port {PORT}")
            print(f"Open http://127.0.0.0:{PORT} in your browser")
        else:
            print("Local IP:", localIp)
            print(f"Serving {DIRECTORY_TO_SERVE} at port {PORT}")
            print(f"Open http://{localIp}:{PORT} in your browser")
        # print('testttttttttt')
        # print(CustomHandler.format_size(CustomHandler.get_folder_size(DIRECTORY_TO_SERVE)))
        # print('bruh')

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            httpd.shutdown()
            httpd.server_close()
        
