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
            elif data.startswith("DOWNLOAD"):
                self.send_video_part(data, client_socket)
            else:
                print(f"Received data: {data} from {address}")
        client_socket.close()


    def send_video_part(self, data, client_socket):
        parts = data.split()
        video_name = parts[1]
        part_index = int(parts[-3])
        total_parts = int(parts[-1])

        video_path = os.path.join(self.video_directory, video_name)
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            part_size = file_size // total_parts
            start_byte = part_index * part_size
            end_byte = start_byte + part_size if part_index < total_parts - 1 else file_size

            with open(video_path, 'rb') as file:
                file.seek(start_byte)
                while start_byte < end_byte:
                    bytes_to_read = min(4096, end_byte - start_byte)
                    data = file.read(bytes_to_read)
                    if data:
                        client_socket.sendall(data)
                        start_byte += len(data)
                    print(f"Sent {len(data)} bytes from part {part_index} of {video_name}")  # Debugging
        else:
            print(f"Video file {video_name} not found.")

    def monitor_video_directory(self):
        last_known_videos = set(self.videos)
        while True:
            current_videos = set(self.load_videos())
            if current_videos != last_known_videos:
                self.update_main_server_with_videos(current_videos)
                last_known_videos = current_videos
            time.sleep(10)

    def update_main_server_with_videos(self, videos):
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
