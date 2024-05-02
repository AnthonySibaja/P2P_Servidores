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
            if line.strip():  # Ensure the line is not empty
                video_name, rest = line.split(' available at ')
                size_info, server_info = rest.split(' bytes ')
                videos[video_name] = {'size': size_info, 'server': server_info}
        return videos

    def choose_video(self):
        """Permite al usuario seleccionar un vídeo para descargar."""
        for video, info in self.videos.items():
            print(f"{video} {info['size']} bytes available at {info['server']}")
        video_choice = input("\nIngrese el nombre del vídeo que desea descargar: ")
        self.request_video_download(video_choice)

    def request_video_download(self, video_name):
        """Solicita la descarga de un vídeo específico y maneja la descarga de partes."""
        if video_name in self.videos:
            server_info = self.videos[video_name]['server']
            print(f"Descargando {video_name} desde {server_info}...")
            self.download_video_parts(video_name, server_info)
        else:
            print("Vídeo no encontrado.")

    def download_video_parts(self, video_name, server_info):
        """Descarga partes del vídeo de diferentes servidores y muestra el progreso."""
        host, port = server_info.split(':')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, int(port)))
            request = f"DOWNLOAD {video_name}"
            sock.sendall(request.encode())
            video_data = sock.recv(4096)
            self.reassemble_video(video_name, video_data)

    def reassemble_video(self, video_name, video_data):
        """Reensambla y guarda el vídeo completo en la carpeta 'video_Descargado'."""
        directory = "video_Descargado"
        if not os.path.exists(directory):
            os.makedirs(directory)
        video_path = os.path.join(directory, f"{video_name}_complete.mp4")
        with open(video_path, 'wb') as video_file:
            video_file.write(video_data)
        print(f"Vídeo {video_name} descargado y reensamblado correctamente en {video_path}.")

if __name__ == "__main__":
    server_ip = input("Enter the main server IP: ")
    server_port = int(input("Enter the main server port: "))
    client = P2PClient(server_ip, server_port)
    client.connect_to_server()
