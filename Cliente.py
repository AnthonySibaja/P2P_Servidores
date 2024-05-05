import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import os
import time

class P2PClient:
    def __init__(self, gui, server_ip='192.168.1.34', server_port=8000):
        self.gui = gui
        self.server_ip = server_ip
        self.server_port = server_port
        self.videos = {}
        self.download_dir = 'video_Descargado'
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def connect_to_server(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.server_ip, self.server_port))
                sock.sendall("QUERY".encode())
                data = sock.recv(4096).decode()
                self.videos = self.parse_videos(data)
            self.gui.display_videos(self.videos)
        except socket.error as e:
            messagebox.showerror("Connection Error", f"Error al conectar al servidor: {e}")

    def parse_videos(self, data):
        videos = {}
        lines = data.split('\n')
        for line in lines:
            if line.strip():
                parts = line.split(' bytes available at ')
                if len(parts) > 1:
                    video_details = parts[0].split()
                    video_name = video_details[0]
                    video_size = video_details[1]
                    server_info = parts[1]
                    if video_name not in videos:
                        videos[video_name] = {'size': video_size, 'servers': []}
                    videos[video_name]['servers'].append(server_info)
        return videos

    def request_video_download(self, video_name):
        if video_name in self.videos:
            servers = self.videos[video_name]['servers']
            num_servers = len(servers)
            progress_bars = self.gui.setup_progress_bars(video_name, num_servers)
            threads = []
            for i, server_info in enumerate(servers):
                host, port = server_info.split(':')
                part_thread = threading.Thread(target=self.download_video_part, args=(video_name, host, int(port), i, num_servers, progress_bars[i]))
                threads.append(part_thread)
                part_thread.start()
            for thread in threads:
                thread.join()
            self.reassemble_video(video_name, num_servers)

    def download_video_part(self, video_name, host, port, part, total_parts, progress_bar):
        request = f"DOWNLOAD {video_name} PART {part} OF {total_parts}"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
                sock.settimeout(10)
                sock.sendall(request.encode())
                video_data = b''
                while True:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            break
                        video_data += data
                        progress_bar['value'] += len(data)
                        self.gui.root.update_idletasks()
                        
                    except socket.timeout:
                        print("Socket timed out while receiving data.")
                        break
                part_path = f"{self.download_dir}/{video_name}_part_{part}.mp4"
                with open(part_path, 'wb') as video_file:
                    video_file.write(video_data)
        except socket.error as e:
            print(f"Socket error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def reassemble_video(self, video_name, total_parts):
        
        final_path = os.path.join(self.download_dir, f"{video_name}.mp4")
        if all(os.path.exists(os.path.join(self.download_dir, f"{video_name}_part_{i}.mp4")) for i in range(total_parts)):
            with open(final_path, 'wb') as final_video:
                for i in range(total_parts):
                    part_path = os.path.join(self.download_dir, f"{video_name}_part_{i}.mp4")
                    with open(part_path, 'rb') as part_file:
                        final_video.write(part_file.read())
                    os.remove(part_path)
            messagebox.showinfo("Download Complete", f"Video {video_name} reconstructed and saved in {final_path}.")
            
        else:
            messagebox.showerror("Download Error", "Some parts of the video are missing, cannot reassemble the video.")

class VideoDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Video Downloader")
        self.treeview = ttk.Treeview(root, columns=('Size', 'Servers'))
        self.treeview.heading('#0', text='Video Name')
        self.treeview.heading('Size', text='Size')
        self.treeview.heading('Servers', text='Available on Servers')
        self.treeview.pack(fill=tk.BOTH, expand=True)
        ttk.Button(self.root, text="Download Selected Video", command=self.download_selected).pack(expand=True)

    def display_videos(self, videos):
        for video, info in videos.items():
            self.treeview.insert('', 'end', iid=video, text=video, values=(info['size'], f"{len(info['servers'])} server(s)"))

    def download_selected(self):
        selected_item = self.treeview.selection()
        if selected_item:
            video_name = self.treeview.item(selected_item[0])['text']
            threading.Thread(target=lambda: self.client.request_video_download(video_name)).start()
        else:
            messagebox.showwarning("Warning", "Please select a video to download.")

    def setup_progress_bars(self, video_name, num_parts):
        progress_bars = []
        top = tk.Toplevel(self.root)
        top.title(f"Downloading {video_name}")
        for i in range(num_parts):
            label = tk.Label(top, text=f"Part {i + 1}/{num_parts}")
            label.pack()
            progress = ttk.Progressbar(top, length  = 200, mode='determinate', maximum=1000)
            progress.pack()
            progress_bars.append(progress)
        return progress_bars

def main():
    root = tk.Tk()
    gui = VideoDownloaderGUI(root)
    client = P2PClient(gui)
    gui.client = client
    threading.Thread(target=client.connect_to_server).start()
    root.mainloop()

if __name__ == "__main__":
    main()
