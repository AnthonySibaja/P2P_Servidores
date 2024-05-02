import socket
import threading
import os

class P2PClient:
    def __init__(self, server_ip='192.168.100.125', server_port=8000):
        self.server_ip = server_ip
        self.server_port = server_port

    def connect_to_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_ip, self.server_port))
            sock.sendall("QUERY".encode())
            data = sock.recv(4096).decode()
            print("Vídeos disponibles:")
            self.videos = self.parse_videos(data)
        self.display_videos()

    def parse_videos(self, data):
        videos = {}
        lines = data.split('\n')
        for line in lines:
            if line.strip():
                video_details = line.split(' available at ')
                video_name, details = video_details[0].split(' bytes')[0], video_details[1]
                if video_name not in videos:
                    videos[video_name] = {'servers': []}
                videos[video_name]['servers'].append(details)
        return videos

    def display_videos(self):
        for video, info in self.videos.items():
            print(f"{video}: Disponible en {len(info['servers'])} servidor(es)")
        self.select_video()

    def select_video(self):
        print("Elija el video que desea descargar:")
        video_choice = input("")
        self.request_video_download(video_choice)

    def request_video_download(self, video_name):
        if video_name in self.videos:
            servers = self.videos[video_name]['servers']
            num_servers = len(servers)
            print(f"Descargando {video_name} desde {num_servers} servidor(es)...")

            threads = []
            for i, server_info in enumerate(servers):
                host, port = server_info.split(':')
                part_thread = threading.Thread(target=self.download_video_part, args=(video_name, host, int(port), i, num_servers))
                threads.append(part_thread)
                part_thread.start()

            for thread in threads:
                thread.join()

            self.reassemble_video(video_name, num_servers)

            print("Vídeo no encontrado.")

    def download_video_part(self, video_name, host, port, part, total_parts):
        request = f"DOWNLOAD {video_name} PART {part} OF {total_parts}"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            sock.sendall(request.encode())
            video_data = b''
            print("entra")
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                video_data += data
            part_path = f"video_Descargado/{video_name}_part_{part}.mp4"
            print(f"Received {len(video_data)} bytes for part {part}.")  # Debugging
            with open(part_path, 'wb') as video_file:
                video_file.write(video_data)


    def reassemble_video(self, video_name, total_parts):
        final_path = f"video_Descargado/{video_name}.mp4"
        with open(final_path, 'wb') as final_video:
            for i in range(total_parts):
                part_path = f"video_Descargado/{video_name}_part_{i}.mp4"
                with open(part_path, 'rb') as part_file:
                    final_video.write(part_file.read())
                os.remove(part_path)
        print(f"Vídeo {video_name} reconstruido y guardado en {final_path}.")


if __name__ == "__main__":
    client = P2PClient()
    client.connect_to_server()
