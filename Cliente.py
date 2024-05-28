import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import os
import time

class P2PClient:
    def __init__(self, gui, server_ip='192.168.1.34', server_port=8001):
        self.gui = gui
        self.server_ip = server_ip
        self.server_port = server_port
        self.videos = {}
        self.download_dir = 'Descargas'
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

    def start_auto_refresh(self, interval_ms=5000):
        """Inicia la actualización automática de la lista de videos."""
        threading.Thread(target=self.connect_to_server).start()
        self.gui.root.after(interval_ms, self.start_auto_refresh)

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
                    if server_info not in videos[video_name]['servers']:
                        videos[video_name]['servers'].append(server_info)
        return videos

    def request_video_download(self, video_name, selected_servers):
        if video_name in self.videos:
            servers = selected_servers
            num_servers = len(servers)
            total_size = int(self.videos[video_name]['size'])

            sizes = [total_size // num_servers] * num_servers

            remainder = total_size % num_servers
            if remainder > 0:
                sizes[-1] += remainder

            progress_bars, progress_window = self.gui.setup_progress_bars(video_name, num_servers, sizes)

            download_info = {'total': 0, 'per_server': [0] * num_servers}
            start_time = time.time()

            threads = []
            for i, server_info in enumerate(servers):
                host, port = server_info.split(':')
                part_thread = threading.Thread(target=self.download_video_part, args=(video_name, host, int(port), i, num_servers, progress_bars[i], download_info))
                threads.append(part_thread)
                part_thread.start()

            for thread in threads:
                thread.join()

            download_time = time.time() - start_time
            self.reassemble_video(video_name, num_servers, progress_window, download_info, download_time)

    def download_video_part(self, video_name, host, port, part, total_parts, progress_bar, download_info):
        request = f"DOWNLOAD {video_name} PART {part} OF {total_parts}"
        END_OF_DATA_MARKER = "END_OF_DATA"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
                sock.sendall(request.encode())
                video_data = b''
                total_bytes_received = 0
                while True:
                    data = sock.recv(4096)
                    if END_OF_DATA_MARKER.encode() in data:
                        data = data[:data.find(END_OF_DATA_MARKER.encode())]
                        video_data += data
                        break
                    elif data:
                        video_data += data
                        progress_bar['value'] += len(data)
                        total_bytes_received += len(data)
                        download_info['total'] += len(data)
                        download_info['per_server'][part] += len(data)
                        self.gui.root.update_idletasks()
                    else:
                        break
                part_path = f"{self.download_dir}/{video_name}_part_{part}.mp4"
                with open(part_path, 'wb') as video_file:
                    video_file.write(video_data)
        except socket.error as e:
            print(f"Socket error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def reassemble_video(self, video_name, total_parts, progress_window, download_info, download_time):
        final_path = os.path.join(self.download_dir, f"{video_name}")
        if all(os.path.exists(os.path.join(self.download_dir, f"{video_name}_part_{i}.mp4")) for i in range(total_parts)):
            with open(final_path, 'wb') as final_video:
                for i in range(total_parts):
                    part_path = os.path.join(self.download_dir, f"{video_name}_part_{i}.mp4")
                    with open(part_path, 'rb') as part_file:
                        final_video.write(part_file.read())
                    os.remove(part_path)
            
            progress_window.destroy()

            download_info_text = (f"Nombre del Video: {video_name}\n"
                                  f"Ruta: {final_path}\n"
                                  f"Tiempo de Descarga: {download_time:.2f} segundos\n"
                                  f"Tamaño Total: {download_info['total']} bytes\n"
                                  f"Descarga por Servidor:\n" +
                                  "\n".join([f"  Parte {i + 1}: {size} bytes" for i, size in enumerate(download_info['per_server'])]))

            messagebox.showinfo("Download Complete", f"Video {video_name} reconstruido y guardado en {final_path}.\n\n{download_info_text}")
        else:
            progress_window.destroy()
            messagebox.showerror("Download Error", "Algunas partes del video faltan, no se puede reensamblar el video.")

class VideoDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Video Downloader")
        self.treeview = ttk.Treeview(root, columns=('Size', 'Servers'))
        self.treeview.heading('#0', text='Video Name')
        self.treeview.heading('Size', text='Size')
        self.treeview.heading('Servers', text='Available on Servers')
        self.treeview.pack(fill=tk.BOTH, expand=True)

        ttk.Button(self.root, text="Download Selected Video", command=self.show_server_selection).pack(expand=True)

    def display_videos(self, videos):
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        for video, info in videos.items():
            servers_info = ", ".join(info['servers'])
            self.treeview.insert('', 'end', iid=video, text=video, values=(info['size'], servers_info))

    def show_server_selection(self):
        selected_item = self.treeview.selection()
        if selected_item:
            video_name = self.treeview.item(selected_item[0])['text']
            servers = self.client.videos[video_name]['servers']
            self.server_selection_popup(video_name, servers)
        else:
            messagebox.showwarning("Warning", "Please select a video to download.")

    def server_selection_popup(self, video_name, servers):
        popup = tk.Toplevel(self.root)
        popup.title(f"Select Servers for {video_name}")

        # Calcular la posición para centrar la ventana emergente
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()

        popup_width = 300
        popup_height = 200

        pos_x = (screen_width // 2) - (popup_width // 2)
        pos_y = (screen_height // 2) - (popup_height // 2)

        popup.geometry(f"{popup_width}x{popup_height}+{pos_x}+{pos_y}")

        server_vars = []
        for server in servers:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(popup, text=server, variable=var)
            chk.pack(anchor='w')
            server_vars.append(var)

        def start_download():
            selected_servers = [server for server, var in zip(servers, server_vars) if var.get()]
            if selected_servers:
                threading.Thread(target=lambda: self.client.request_video_download(video_name, selected_servers)).start()
                popup.destroy()
            else:
                messagebox.showwarning("Warning", "Please select at least one server.")

        ttk.Button(popup, text="Download", command=start_download).pack()

    def setup_progress_bars(self, video_name, num_parts, sizes):
        progress_bars = []
        top = tk.Toplevel(self.root)
        top.title(f"Downloading {video_name}")

        screen_width = top.winfo_screenwidth()
        screen_height = top.winfo_screenheight()

        estimated_width = 300  
        estimated_height = 30 * num_parts + 50 

        pos_x = (screen_width // 2) - (estimated_width // 2)
        pos_y = (screen_height // 2) - (estimated_height // 2)

        top.geometry(f"{estimated_width}x{estimated_height}+{pos_x}+{pos_y}")

        for i in range(num_parts):
            label = tk.Label(top, text=f"Parte {i + 1}/{num_parts}")
            label.pack()
            progress = ttk.Progressbar(top, length=200, mode='determinate', maximum=sizes[i])
            progress.pack()
            progress_bars.append(progress)

        return progress_bars, top

def main():
    root = tk.Tk()
    gui = VideoDownloaderGUI(root)
    client = P2PClient(gui)
    gui.client = client

    # Inicia la actualización automática cada 5 segundos
    client.start_auto_refresh(interval_ms=5000)

    root.mainloop()

if __name__ == "__main__":
    main()
