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
from tkinter import filedialog
import threading, uuid
import time

parser = argparse.ArgumentParser()
parser.add_argument("-port", type=int, help="Port number")
parser.add_argument("-path", type=str, help="Path to directory")

args = parser.parse_args()


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

PORT = args.port or 8700
DIRECTORY_TO_SERVE = args.path or "./"
BASE_DIR = os.path.abspath(DIRECTORY_TO_SERVE)
os.chdir(DIRECTORY_TO_SERVE)
HTML_TEMPLATE = os.path.join(os.path.dirname(__file__), "index.html")



curpath = None
textData = ""
class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):

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
    def do_GET(self):
        global curpath
        if self.path.endswith('endpoints/GET/folder.svg') or self.path.endswith('endpoints/GET/unknown.svg') or self.path.endswith('endpoints/GET/upload.svg') or self.path.endswith('/alert.svg'):
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
            return self.serve_directory_list()
        elif os.path.isdir(self.path.lstrip('/').replace('%20', ' ')):  # Check if path is a directory
            curpath = os.path.join(BASE_DIR, self.path.lstrip('/'))
            return self.serve_directory(self.path + "/")  # Serve subdirectory
        elif self.path.startswith('/endpoints/GET/download_zip'):
            query_components = parse_qs(urlparse(self.path).query)
            if query_components == {}:
                return
            file_name = query_components.get("file", [None])[0]
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

        elif self.path.startswith('/endpoints/GET/zip_progress'):
            query = parse_qs(urlparse(self.path).query)
            job_id = query.get("id", [None])[0]
            progress = zip_progress.get(job_id)
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
        elif self.path== '/endpoints/GET/getText':
            # parsed = urlparse(self.path)
            # query = parse_qs(parsed.query)  # access params like query['key'][0]
            global textData

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {'message': 'GET received', 'data': textData}
            self.wfile.write(json.dumps(response).encode())

        else:
            return super().do_GET()
        
    #FIX test and check for bugs 
    def do_POST(self):
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

        if self.path == '/endpoints/POST/updateText':
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
                item = unquote(item).strip("/")
                item_path = os.path.join(os.getcwd(), item)
                
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
                        <img src="endpoints/GET/folder.svg">
                        <span>..<span>
                    </div>
                </a>
            </li>
            """
        for name in file_list:
            display_name = os.path.basename(name) + "/" if os.path.isdir(name) else os.path.basename(name)
            href = f"/{name}/" if os.path.isdir(name) else f"/{name}"
            # icon_href = 
            icon_href = "endpoints/GET/folder.svg" if os.path.isdir(name) else "endpoints/GET/unknown.svg"
            list_items += f"""
            <li class="files">
                <div class="buffering">
                    <div class="spinner"></div>
                    <img src="alert.svg">
                </div>
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


server_instance = None

if __name__ == '__main__':
    def start_server():
        global server_instance
        try:
            socketserver.TCPServer.allow_reuse_address = True
            server_instance = socketserver.ThreadingTCPServer(("", PORT), CustomHandler)
            server_instance.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            localIp = get_local_ip()
            if localIp == "Error":
                log_output(f"Serving {DIRECTORY_TO_SERVE} at 127.0.0.0 instead with Port {PORT}")
                log_output(f"Open http://127.0.0.0:{PORT} in your browser")
            else:
                log_output(f"Local IP: {localIp}")
                log_output(f"Serving {DIRECTORY_TO_SERVE} at port {PORT}")
                log_output(f"Open http://{localIp}:{PORT} in your browser")
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
    
    def log_output(message):
        message = str(message)
        try: 
            log_text.insert(tk.END, message + "\n")  # Insert message at the end
            log_text.yview(tk.END)  # Auto-scroll to the end
        except Exception:
            print(message)

    def on_click():
        global DIRECTORY_TO_SERVE
        global BASE_DIR
        global PORT
        DIRECTORY_TO_SERVE = pathInput.get()
        BASE_DIR = os.path.abspath(DIRECTORY_TO_SERVE)
        os.chdir(DIRECTORY_TO_SERVE)
        try:
            PORT = int(portInput.get())
        except Exception as e:
            return e
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

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

    root = tk.Tk()
    root.title("File Share HTTP server")
    root.geometry("600x400")

    frame = tk.Frame(root)   # Use a frame to group them horizontally
    frame.pack(padx=10, pady=10)

    label = tk.Label(frame, text="Choose a path")
    label.pack(side=tk.LEFT)

    pathInput = tk.Entry(frame)
    pathInput.insert(tk.END, "../")
    pathInput.pack(side=tk.LEFT, fill=tk.X, expand=True)
    # pathInput.place(x = 30, y = 10)

    button = tk.Button(frame, text="Browse...", command=choose_folder)
    button.pack(side=tk.LEFT, padx=5)
    # button.place(x = 60, y = 10)

    portInput = tk.Entry(root)
    portInput.insert(tk.END, "8701")
    portInput.pack(pady=10)

    button = tk.Button(root, text="Start Server", command=on_click)
    button.pack(pady=10)

    stopButton = tk.Button(root, text="Stop Server", command=stop_server)
    stopButton.pack(pady=10)

    #TODO make a maximum limit
    log_text = tk.Text(root, height=600, width=600, wrap=tk.WORD, state=tk.NORMAL)
    log_text.pack(padx=10, pady=10)




    root.mainloop()
