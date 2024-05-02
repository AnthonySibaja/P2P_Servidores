import socket
import os

class P2PClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

    def connect_to_server(self):
        """Conecta al servidor principal y obtiene la lista de vídeos disponibles."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_ip, self.server_port))
            sock.sendall("QUERY".encode())
            data = sock.recv(4096).decode()
            print("Vídeos disponibles:")
            self.videos = self.parse_videos(data)
        self.choose_video()

    def parse_videos(self, data):
        """Parsea la información de los vídeos recibidos del servidor."""
        videos = {}
        lines = data.split('\n')
        for line in lines:
            if line.strip():
                parts = line.split(' from ')
                if len(parts) > 1:
                    video_name, servers = parts[0], parts[1]
                    videos[video_name] = servers.split(', ')
        return videos

    def choose_video(self):
        """Permite al usuario seleccionar un vídeo para descargar."""
        print("\nIngrese el nombre del vídeo que desea descargar:")
        for video in self.videos:
            print(video)
        video_choice = input()
        self.request_video_download(video_choice)

    def request_video_download(self, video_name):
        """Solicita la descarga de un vídeo específico y maneja la descarga de partes."""
        if video_name in self.videos:
            servers = self.videos[video_name]
            print(f"Descargando {video_name} de {len(servers)} servidores...")
            self.download_video_parts(video_name, servers)
        else:
            print("Vídeo no encontrado.")

    def download_video_parts(self, video_name, servers):
        """Descarga partes del vídeo de diferentes servidores y muestra el progreso."""
        video_data = []
        for index, server in enumerate(servers):
            host, port = server.split(':')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, int(port)))
                request = f"DOWNLOAD {video_name} {index + 1}"
                sock.sendall(request.encode())
                part_data = sock.recv(4096)
                video_data.append(part_data)
                print(f"Parte {index + 1} descargada de {host}. Tamaño: {len(part_data)} bytes.")
        self.reassemble_video(video_name, video_data)

    def reassemble_video(self, video_name, video_data_parts):
        """Reensambla y guarda el vídeo completo en la carpeta 'video_Descargado'."""
        directory = "video_Descargado"
        if not os.path.exists(directory):
            os.makedirs(directory)
        video_path = os.path.join(directory, f"{video_name}_complete.mp4")
        with open(video_path, 'wb') as video_file:
            for part_data in video_data_parts:
                video_file.write(part_data)
        print(f"Vídeo {video_name} descargado y reensamblado correctamente en {video_path}.")

if __name__ == "__main__":
    server_ip = input("Enter the main server IP: ")
    server_port = int(input("Enter the main server port: "))
    client = P2PClient(server_ip, server_port)
    client.connect_to_server()
