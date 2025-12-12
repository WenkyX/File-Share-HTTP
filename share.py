import http.server
# from http.server import SimpleHTTPRequestHandler
import socketserver
import socket
import os
import zipfile
import io
from urllib.parse import parse_qs, urlparse, unquote
import argparse
import cgi
import json
import tkinter as tk
from tkinter import filedialog, ttk
import threading, uuid
import time
import sys
# import base64
from http.cookies import SimpleCookie
# import ssl
import re
import mimetypes
from PIL import Image

# context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# context.load_cert_chain(certfile='cert/cert.pem', keyfile='cert/key.pem')



zip_progress = {}

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

PORT = 8700
DIRECTORY_TO_SERVE = "./"
BASE_DIR = os.path.abspath(DIRECTORY_TO_SERVE)
os.chdir(DIRECTORY_TO_SERVE)
HTML_TEMPLATE = os.path.join(os.path.dirname(__file__), "index.html")
HTML_LOGIN_TEMPLATE = os.path.join(os.path.dirname(__file__), "login.html")


USERS_DEFAULT = {
    "admin": "super",
    }
USERS = {
    "admin": "super",
    }
SESSIONS = {}
# AUTH_STRING = b"Basic " + base64.b64encode(USERNAME + b":" + PASSWORD)

curpath = None
textData = ""
class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        try:
            now = time.time()
            year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
            s = "%02d:%02d:%02d" % (
            hh, mm, ss)

            message = format % args
            message1 = ("%s - [%s] %s" %
                            (self.address_string(),
                            s,
                            message.translate(self._control_char_table)))

            log_output(message1)
        except Exception as e:
            # print(f"Error logging message: {e}")
            print(f"Original message: {format % args}")

    # def is_authenticated(self):
    #     header = self.headers.get('Authorization')
    #     return header and header.encode() == AUTH_STRING
    
    def get_session(self):
        cookie = self.headers.get("Cookie")
        if not cookie:
            return None
        c = SimpleCookie(cookie)
        sid = c.get("session")
        if sid and sid.value in SESSIONS:
            return SESSIONS[sid.value]
        return None

    def respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        requested_path = os.path.abspath(self.path[1:] if self.path.startswith('/') else self.path)
        if not requested_path.startswith(BASE_DIR):
            self.send_error(403, "Forbidden: Access outside the base directory is not allowed.")
            return
        session = self.get_session()
        if not session and is_authenticate.get():
            with open(HTML_LOGIN_TEMPLATE, "r", encoding="utf-8") as f:
                html = f.read()
            self.respond(200, html)
            return
        
        global curpath
        static_files = ['/endpoints/GET/folder.svg', 
                        '/endpoints/GET/unknown.svg', 
                        '/endpoints/GET/upload.svg', 
                        '/alert.svg', 
                        '/endpoints/GET/video.svg',
                        '/endpoints/GET/zip.svg',
                        '/endpoints/GET/pdf.svg',
                        '/endpoints/GET/word.svg',
                        '/endpoints/GET/excel.svg',
                        '/endpoints/GET/ppt.svg',
                        '/endpoints/GET/audio.svg',
                        '/endpoints/GET/text.svg',
                        '/endpoints/GET/exe.svg',
                        '/endpoints/GET/code.svg'
                        ]
        if any(self.path.endswith(file) for file in static_files):
            # Serve the SVG files from the directory where the Python script is located
            file_path = os.path.join(os.path.dirname(__file__), 'static', os.path.basename(self.path))
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
            return self.serve_directory_list()
        # elif '/._thumbcache/' in self.path:
        #     self.send_error(404, "File not found")
        elif os.path.isdir(self.path.lstrip('/').replace('%20', ' ')):  # Check if path is a directory
            curpath = os.path.join(BASE_DIR, self.path.lstrip('/'))
            return self.serve_directory(self.path + "/")  # Serve subdirectory
        elif self.path.startswith('/endpoints/GET/download_zip'):
            query_components = parse_qs(urlparse(self.path).query)
            print(query_components)
            print(self.path)
            if query_components == {}:
                return
            file_name = query_components.get("file", [None])[0]
            
            # Ensure file_name is prefixed with BASE_DIR when it's a relative path
            file_name1 = None
            if file_name:
                file_name1 = unquote(file_name)
                # normalize and remove any leading slashes/backslashes
                file_name1 = os.path.normpath(file_name1.lstrip("/\\"))
                if not os.path.isabs(file_name1):
                    file_name1 = os.path.join(BASE_DIR, file_name1)
                else:
                    file_name1 = os.path.normpath(file_name1)
                # update original variable for downstream code
                file_name = file_name1
            print(file_name1)

            print(os.path.abspath(file_name), "vs", BASE_DIR)
            print(file_name, "vs", BASE_DIR)
            if not (os.path.abspath(file_name)).startswith(BASE_DIR):
                self.send_error(403, "Forbidden: Access outside the base directory is not allowed.")
                return
            # print(file_name)

            if file_name:

                job_id = str(uuid.uuid4())
                zip_progress[job_id] = 0
                threading.Thread(target=self.create_zip_async, args=(job_id, [file_name])).start()

                self.send_response(200)
                self.end_headers()
                self.wfile.write(job_id.encode())
            else:
                self.send_error(400, "Bad Request: No file specified")

        elif os.path.isfile(self.path.lstrip('/').replace('%20', ' ')):
            filepath = os.path.join(BASE_DIR, self.path.lstrip('/').replace('%20', ' '))
            try:
                ctype, _ = mimetypes.guess_type(filepath)
                if ctype is None:
                    ctype = "application/octet-stream"

                with open(filepath, 'rb') as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Disposition", "inline")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self.send_error(500, "Internal server error")

        elif self.path.startswith('/endpoints/GET/zip_progress'):
            query = parse_qs(urlparse(self.path).query)
            job_id = query.get("id", [None])[0]
            progress = zip_progress.get(job_id)
            client_ip = self.client_address[0]
            log_output(f"ZIP progress from {client_ip} : {progress}%", 2)
            if progress is None:
                self.send_error(404)
            elif isinstance(progress, tuple) and progress[0] == "done":
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", "attachment; filename=download.zip")
                self.send_header("Content-Length", str(len(progress[1].getvalue())))
                self.end_headers()
                self.wfile.write(progress[1].getvalue())
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(str(progress).encode())
        elif self.path.startswith('/endpoints/GET/get-file-size'):
            query_components = parse_qs(urlparse(self.path).query)
            folder = query_components.get("path", [None])[0]
            abspath = os.path.abspath(folder)
            if not abspath.startswith(BASE_DIR):
                self.send_error(403, "Forbidden: Access outside the base directory is not allowed.")
                return
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
        elif self.path == '/endpoints/GET/getText':
            # parsed = urlparse(self.path)
            # query = parse_qs(parsed.query)  # access params like query['key'][0]
            global textData

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'message': 'GET received', 'data': textData}
            self.wfile.write(json.dumps(response).encode())

        else:
            self.send_response(404)
        
    def is_valid_username(self, username):
        return bool(re.fullmatch(r"[A-Za-z0-9_.-]{3,20}", username))

    def is_valid_password(self, password):
        return 1 <= len(password) <= 64
    def do_POST(self):
        # if not self.is_authenticated():
        #     self.request_auth()
        if self.path == "/login":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            data = json.loads(body)
            user = data.get("username", "")
            pwd = data.get("password", "")

            if not self.is_valid_username(user) or not self.is_valid_password(pwd):
                self.send_response(401)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Invalid input format")
                return
            client_ip = self.client_address[0]
            if USERS.get(user) == pwd:
                sid = str(uuid.uuid4())
                SESSIONS[sid] = user
                self.send_response(302)
                self.send_header("Set-Cookie", f"session={sid}; HttpOnly")
                self.send_header("Location", "/")
                self.end_headers()  
                self.wfile.write(b"Login Success")
                print(f"{client_ip} Successfully logged in as {user}")
                log_output(f"{client_ip} Successfully logged in as {user}",index=2, color='green')
                log_output(f"{client_ip} Successfully logged in as {user}",index=1, color='green')
            else:
                self.send_response(401)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Invalid credentials")
                return

        session = self.get_session()
        if not session and is_authenticate.get():
            self.send_response(401, "Unauthorized")
            return

        global curpath 
        global textData
        if self.path == '/endpoints/POST/upload':

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
                    # Sanitize filename to prevent directory traversal
                    filename = os.path.basename(uploaded_file.filename)
                    # Optionally, remove dangerous characters
                    filename = filename.replace("..", "").replace("/", "").replace("\\", "")
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
        elif self.path == '/endpoints/POST/upload_progress':
            content_type = self.headers['Content-Type']
            if 'application/json' in content_type:
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                data = json.loads(body)
                client_ip = self.client_address[0]

                log_output(f"Upload progress from {client_ip} : {data['progress']}%", 2)
                # print(data['progress'])

            self.send_response(200)
            self.end_headers()

        elif self.path == '/endpoints/POST/updateText':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            textData = data['data']
            print(textData)
            # process data here

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'status': 'received'}
            self.wfile.write(json.dumps(response).encode())
        
        else:
            self.send_response(404)
            self.end_headers()

        
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

    def create_zip_async(self, job_id, items):
        # total_steps = len(items)
        total_count = 0
        i = 0
        # print(total_steps, "total_stepstotal_stepstotal_stepstotal_stepstotal_stepstotal_stepstotal_stepstotal_steps")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for i, item in enumerate(items):
                item = unquote(item)
                item_path = item
                
                base_dir = os.path.basename(item)  # Get just the final part (like "c")

                if os.path.isfile(item_path):
                    zipf.write(item_path, arcname=os.path.basename(item_path))
                elif os.path.isdir(item_path):
                    for root, _, files in os.walk(item_path):
                        total_count += len(files)
                        # print(total_count, "total_counttotal_counttotal_counttotal_counttotal_counttotal_counttotal_count")
                    for root, _, files in os.walk(item_path):
                        for file in files:
                            i += 1
                            zip_progress[job_id] = int((i + 1) / total_count * 100)
                            full_path = os.path.join(root, file)
                            # Make arcname relative to the base_dir
                            relative_path = os.path.relpath(full_path, start=os.path.dirname(item_path))
                            zipf.write(full_path, arcname=relative_path)
                else:
                    print(f"Warning: {item_path} does not exist or is not a valid file or directory.")
        zip_buffer.seek(0)
        zip_progress[job_id] = "done", zip_buffer
        # return zip_buffer
    
    # def create_zip_async(job_id, files):
    #     total_steps = len(files)
    #     zip_buffer = io.BytesIO()
    #     with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
    #         for i, file in enumerate(files):
    #             zipf.writestr(file, f"Contents of {file}")
    #             zip_progress[job_id] = int((i + 1) / total_steps * 100)
    #     zip_buffer.seek(0)
    #     zip_progress[job_id] = "done", zip_buffer

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
        list_items += f"""
            <li class="files" data-type="navigation">
                <a class="file" href=".." id="..">
                    <div class=icon>
                        <img src="endpoints/GET/folder.svg">
                        <span>..<span>
                    </div>
                </a>
            </li>
            """
        for name in file_list:
            isdir = os.path.isdir(name)
            basename = os.path.basename(name)
            display_name = basename + "/" if isdir else basename
            href = f"/{name}/" if isdir else f"/{name}"

            kind = ''
            if isdir:
                icon_href = "endpoints/GET/folder.svg"
            else:
                import magic
                import mimetypes
                kind = magic.from_file(name, mime=True)
                ext = mimetypes.guess_extension(kind)

            # if name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico', '.avif', '.apng')):
            if not kind:
                icon_href = "endpoints/GET/unknown.svg"
            elif kind.startswith('image/') and not kind == 'image/svg+xml':
                if not os.path.exists("._thumbcache"):
                    os.makedirs("._thumbcache")
                
                # Preserve original extension
                original_ext = os.path.splitext(basename)[1]
                thumb_path = f"._thumbcache/{os.path.splitext(basename)[0]}{original_ext}"
                
                if not os.path.exists(thumb_path):
                    try:
                        img = Image.open(name)
                        if img.mode == 'CMYK':
                            img = img.convert('RGB')
                        elif img.mode == 'RGBA':
                            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                            rgb_img.paste(img, mask=img.split()[3])
                            img = rgb_img
                        img.thumbnail((200, 200))
                        img.save(thumb_path)
                        icon_href = thumb_path
                    except Exception as e:
                        print(f"Error generating thumbnail for {name}: {e}")
                        icon_href = "endpoints/GET/unknown.svg"
                else:
                    icon_href = thumb_path
            # elif name.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg')):
            elif kind.startswith('video/'):
                if not os.path.exists("._thumbcache"):
                    os.makedirs("._thumbcache")
                
                thumb_path = f"._thumbcache/{os.path.splitext(basename)[0]}.jpg"
                
                if not os.path.exists(thumb_path):
                    try:
                        from moviepy import VideoFileClip  # Changed import for moviepy 2.x
                        clip = VideoFileClip(name)
                        # Get frame at 1 second or 10% into video
                        frame_time = min(1.0, clip.duration * 0.1)
                        frame = clip.get_frame(frame_time)
                        img = Image.fromarray(frame)
                        img.thumbnail((200, 200))
                        img.save(thumb_path)
                        clip.close()
                        icon_href = thumb_path
                    except Exception as e:
                        print(f"Error generating video thumbnail: {e}")
                        icon_href = "endpoints/GET/video.svg"
                else:
                    icon_href = thumb_path
            # elif name.lower().endswith('.pdf'):
            elif ext in ['.pdf'] or kind == 'application/pdf':
                icon_href = "endpoints/GET/pdf.svg"
            # elif name.lower().endswith(('.doc', '.docx', '.odt', '.rtf')):
            elif ext in ['.doc', '.docx', '.odt', '.rtf'] :
                icon_href = "endpoints/GET/word.svg"
            # elif name.lower().endswith(('.xls', '.xlsx', '.ods', '.csv')):
            elif ext in ['.xls', '.xlsx', '.ods', '.csv']:
                icon_href = "endpoints/GET/excel.svg"
            # elif name.lower().endswith(('.ppt', '.pptx', '.odp')):
            elif ext in ['.ppt', '.pptx', '.odp']:
                icon_href = "endpoints/GET/ppt.svg"
            # elif name.lower().endswith(('.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a')):
            elif kind.startswith('audio/'):
                icon_href = "endpoints/GET/audio.svg"
            # elif name.lower().endswith(('.txt', '.md', '.log', '.ini', '.cfg', '.json', '.xml', '.yaml', '.yml', '.csv')):
            elif ext in ['.txt', '.md', '.log', '.ini', '.cfg', '.json', '.xml', '.yaml', '.yml', '.csv'] or kind in ['text/plain', 'application/json', 'application/xml', 'text/x-yaml']:
                icon_href = "endpoints/GET/text.svg"
            # elif name.lower().endswith(('.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm')):
            elif ext in ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm'] or kind in ['application/x-msdownload', 'application/x-mach-binary', 'application/x-debian-package']:
                icon_href = "endpoints/GET/exe.svg"
            # elif name.lower().endswith(('.html', '.htm', '.css', '.js')):
            elif ext in ['.html', '.htm', '.css', '.js'] or kind in ['text/html', 'text/css', 'application/javascript']:
                icon_href = "endpoints/GET/code.svg"
            # elif name.lower().endswith(('.svg',)):
            elif ext in ['.svg'] or kind == 'image/svg+xml':
                icon_href = name
            # elif name.lower().endswith(('.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz')):
            elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'] or kind in ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed', 'application/x-tar']:
                icon_href = "endpoints/GET/zip.svg"
            else:
                icon_href = "endpoints/GET/unknown.svg"
            
            file_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(name)))
            list_items += f"""
            <li class="files" data-date="{file_date}" data-type="{'directory' if isdir else 'file'}">
                <div class="buffering">
                    <div class="spinner"></div>
                    <img src="alert.svg">
                </div>
                <a class="file" href="{href}" id="{display_name}" {"onclick='previewImage(event, this)'" if not isdir and (icon_href.startswith("._thumbcache/") or name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.ico', '.avif', '.apng'))) else ''}>
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


server_instance = None

if __name__ == '__main__':
    def log_output(message, index=None, end=None, color=None):
        message = str(message)

        if end is None:
            endl = "\n"
        elif end == '':
            endl = ''
        try: 
            index = int(index) if index else 1
            if color:
                try:
                    log_texts[index].insert('end', message + endl, color)
                    log_texts[index].yview('end')
                except:
                    log_texts[index].insert(tk.END, message + endl)  # Insert message at the end
                    log_texts[index].yview(tk.END)  # Auto-scroll to the end
            else:
                log_texts[index].insert(tk.END, message + endl)  # Insert message at the end
                log_texts[index].yview(tk.END)  # Auto-scroll to the end
        except Exception as e:
            # print(f"Error logging output: {e}")
            print(message)

    #idk, this is from gipity
    class DualLogger:
        def __init__(self, minimal_logger, original_stderr):
            self.minimal_logger = minimal_logger
            self.original_stderr = original_stderr

        def write(self, message):
            stripped = message.strip()
            if stripped:
                minimal_message = self.filter_message(message)
                if minimal_message:
                    self.minimal_logger(minimal_message, 1)
            self.original_stderr.write(message)  # write full original message, including newlines

        def flush(self):
            self.original_stderr.flush()

        def filter_message(self, msg):
            # Customize minimal output here, e.g. remove tracebacks
            if "Traceback" in msg or msg.startswith("  File"):
                return ""  # suppress detailed traceback lines
            return msg.strip()

    sys.stderr = DualLogger(log_output, sys.__stderr__)

    log_texts = {}
    def start_server():
        global server_instance
        try:
            socketserver.TCPServer.allow_reuse_address = True
            # print(get_local_ip())
            server_instance = socketserver.ThreadingTCPServer(("", PORT), CustomHandler)
            print("server_instance")
            server_instance.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # server_instance.socket = context.wrap_socket(server_instance.socket, server_side=True)
            localIp = get_local_ip()
            if localIp == "Error":
                log_output(f"No local network detected", color='red')
                log_output(f"Serving {DIRECTORY_TO_SERVE} at 127.0.0.0 instead with Port {PORT}")
                log_output(f"Open http://127.0.0.0:{PORT} in your browser", color='green')
            else:
                log_output(f"Local IP: {localIp}")
                log_output(f"Serving {DIRECTORY_TO_SERVE} at port {PORT}")
                log_output(f"Open http://{localIp}:{PORT} in your browser", color='green')
                # label.config(text=f"Server started on port {PORT}")

            # print('testttttttttt')
            # print(CustomHandler.format_size(CustomHandler.get_folder_size(DIRECTORY_TO_SERVE)))
            # print('bruh')

            try:
                server_instance.serve_forever()
            except KeyboardInterrupt:
                log_output("\nShutting down...")
                server_instance.shutdown()
                server_instance.server_close()
        except Exception as e:
            log_output(e)
            return e
    

    def on_click():
        global DIRECTORY_TO_SERVE
        global BASE_DIR
        global PORT
        global USERS

        DIRECTORY_TO_SERVE = pathInput.get()
        BASE_DIR = os.path.abspath(DIRECTORY_TO_SERVE)
        os.chdir(DIRECTORY_TO_SERVE)
        try:
            PORT = int(portInput.get())
        except Exception as e:
            return e
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        credentials = users_credentials.get("1.0", "end-1c")
        if is_authenticate.get():
            try:
                USERS = json.loads(credentials)
                log_output(f"Using authentication with {len(USERS)} users", color='blue')
            except:
                log_output("Invalid credentials format. Please use JSON format like: {\"username\": \"password\"}", color='red')
                print("Invalid credentials format. Please use JSON format like: {\"username\": \"password\"}")
                log_output("defaulting to {\"admin\": \"super\"}")
                USERS = USERS_DEFAULT

    def stop_server():
        global server_instance
        if server_instance:
            server_instance.shutdown()
            server_instance.server_close()
            log_output("Server stopped.")
            server_instance = None
    
    def choose_folder():
        folder = filedialog.askdirectory()
        if folder:
            pathInput.delete(0, tk.END)      # Clear current content
            pathInput.insert(0, folder)  



    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-port", type=int, help="Port number")
        parser.add_argument("-path", type=str, help="Path to directory")
        parser.add_argument("-no-gui", action="store_true", help="Run without GUI")

        args = parser.parse_args()

        if args.no_gui:
            PORT = args.port or 8700
            DIRECTORY_TO_SERVE = args.path or "./"
            BASE_DIR = os.path.abspath(DIRECTORY_TO_SERVE)
            os.chdir(DIRECTORY_TO_SERVE)

            print(f"Port: {PORT}")
            print(f"Path: {DIRECTORY_TO_SERVE}")

            is_authenticate = type('', (), {'get': lambda self: True})()
            start_server()
            sys.exit(0)

        root = tk.Tk()
        is_authenticate = tk.BooleanVar(value = True)
        root.title("File Share HTTP server")
        root.geometry("600x400")

        notebook = ttk.Notebook(root)
        notebook.pack(expand=True, fill='both')

        tab1 = tk.Frame(notebook)
        tab2 = tk.Frame(notebook)
        tab3 = tk.Frame(notebook)

        notebook.add(tab1, text='Control')
        notebook.add(tab2, text='Monitoring')
        notebook.add(tab3, text='Credentials')


        #=======================================================================================
        # region Tab 1 content
        frame = tk.Frame(tab1)   # Use a frame to group them horizontally
        frame.pack(padx=10, pady=10)

        frame2 = tk.Frame(tab1)   # Use a frame to group them horizontally
        frame2.pack(padx=10, pady=10)

        label = tk.Label(frame, text="Choose a path")
        label.pack(side=tk.LEFT)

        pathInput = tk.Entry(frame)
        pathInput.insert(tk.END, "../")
        pathInput.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if args.path is not None:
            pathInput.delete(0, tk.END)
            pathInput.insert(tk.END, args.path)
        # pathInput.place(x = 30, y = 10)

        button = tk.Button(frame, text="Browse...", command=choose_folder)
        button.pack(side=tk.LEFT, padx=5)
        # button.place(x = 60, y = 10)

        _kinter_labelPort = tk.Label(frame2, text="port")
        _kinter_labelPort.pack(side=tk.LEFT, padx=5)

        portInput = tk.Entry(frame2)
        portInput.insert(tk.END, "8701")
        portInput.pack(pady=10)
        if args.port is not None:
            portInput.delete(0, tk.END)
            portInput.insert(tk.END, str(args.port))

        checkbox = tk.Checkbutton(tab1, text="Use Authentication", variable=is_authenticate)
        checkbox.pack()

        button = tk.Button(tab1, text="Start Server", command=on_click)
        button.pack(pady=10)

        stopButton = tk.Button(tab1, text="Stop Server", command=stop_server)
        stopButton.pack()

        #TODO make a maximum limit
        log_texts[1] = tk.Text(tab1, height=600, width=600, wrap=tk.WORD, state=tk.NORMAL)
        log_texts[1].pack(padx=10, pady=10)

        log_texts[1].tag_config('red', foreground='red')
        log_texts[1].tag_config('blue', foreground='blue')
        log_texts[1].tag_config('green', foreground='green')
        log_texts[1].tag_config('blue_bg', background='blue')
        # endregion

        #=======================================================================================
        # region Tab 2 content

        log_texts[2] = tk.Text(tab2, height=600, width=600, wrap=tk.WORD, state=tk.NORMAL)
        log_texts[2].pack(padx=10, pady=10)

        log_texts[2].tag_config('red', foreground='red')
        log_texts[2].tag_config('blue', foreground='blue')
        log_texts[2].tag_config('green', foreground='green')
        #endregion

        #=======================================================================================
        # region Tab 3 content

        tk.Label(tab3, text="Enter users credentials in a JSON format, to be used when logging in").pack(padx=10, pady=10)

        users_credentials = tk.Text(tab3, height=600, width=600, wrap=tk.WORD, state=tk.NORMAL)
        users_credentials.pack(padx=10, pady=10)

        users_credentials.insert(tk.END, json.dumps(USERS_DEFAULT, indent=4))
        #endregion
        
        
        
        
        
        
        
        root.mainloop()

    except Exception as e:
        print("Error Trying to use display:", e)

        PORT = args.port or 8700
        DIRECTORY_TO_SERVE = args.path or "./"
        BASE_DIR = os.path.abspath(DIRECTORY_TO_SERVE)
        os.chdir(DIRECTORY_TO_SERVE)

        print(f"Port: {PORT}")
        print(f"Path: {DIRECTORY_TO_SERVE}")

        # server_thread = threading.Thread(target=start_server, daemon=True)
        # server_thread.start()
        is_authenticate = type('', (), {'get': lambda self: True})()
        start_server()