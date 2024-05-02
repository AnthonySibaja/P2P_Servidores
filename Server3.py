import socket
import threading
import os
import time

class VideoServer:
    def __init__(self, server_ip, server_port, video_directory, host='127.0.0.1', port=9000):
        self.host = host
        self.port = port
        self.server_ip = server_ip
        self.server_port = server_port
        self.video_directory = video_directory
        self.videos = self.load_videos()
        self.server_active = True

    def load_videos(self):
        """Carga los vídeos y devuelve una lista de tuplas con el nombre y tamaño de cada vídeo."""
        return [(f, os.path.getsize(os.path.join(self.video_directory, f)))
                for f in os.listdir(self.video_directory) if os.path.isfile(os.path.join(self.video_directory, f))]

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen()
        print(f"Video Server listening on {self.host}:{self.port}")
        self.register_with_main_server()
        threading.Thread(target=self.monitor_video_directory).start()

        try:
            while self.server_active:
                client_socket, address = self.socket.accept()
                print(f"Connection from {address}")
                threading.Thread(target=self.handle_client, args=(client_socket, address)).start()
        except KeyboardInterrupt:
            print("Shutting down the server.")
            self.socket.close()

    def register_with_main_server(self):
        """Registers or updates the video list on the main server."""
        videos_info = " ".join(f"{name}:{size}" for name, size in self.videos)
        message = f"REGISTER {self.host}:{self.port} {videos_info}"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.server_ip, self.server_port))
                sock.sendall(message.encode())
        except Exception as e:
            print(f"Failed to connect to main server: {e}")

    def handle_client(self, client_socket, address):
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            if data == 'ping':
                client_socket.sendall(b'pong')
            else:
                print(f"Received data: {data} from {address}")
        client_socket.close()

    def monitor_video_directory(self):
        """Monitors the video directory and updates the main server with any changes."""
        last_known_videos = set(self.videos)
        while True:
            current_videos = set(self.load_videos())
            if current_videos != last_known_videos:
                self.update_main_server_with_videos(current_videos)
                last_known_videos = current_videos
            time.sleep(10)

    def update_main_server_with_videos(self, videos):
        """Sends updates to the main server about the list of available videos."""
        videos_info = " ".join(f"{name}:{size}" for name, size in videos)
        message = f"UPDATE {self.host}:{self.port} {videos_info}"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.server_ip, self.server_port))
                sock.sendall(message.encode())
                print(f"Updated main server with new video list: {videos}")
        except Exception as e:
            print(f"Failed to connect to main server for update: {e}")

if __name__ == "__main__":
    main_server_ip = '192.168.100.125'  
    main_server_port = 8000  
    video_dir = input("Enter the path to the video directory: ")
    port = 9000
    video_server = VideoServer(main_server_ip, main_server_port, video_dir, port=port)
    video_server.start()
