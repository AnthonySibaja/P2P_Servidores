import socket
import os

class P2PClient:
    def __init__(self):
        # IP y puerto del servidor principal configurados directamente en el código
        self.server_ip = '192.168.1.34'
        self.server_port = 8000

    def connect_to_server(self):
        """Conecta al servidor principal y obtiene la lista de vídeos disponibles."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.server_ip, self.server_port))
            sock.sendall("QUERY".encode())
            data = sock.recv(4096).decode()
            print("Vídeos disponibles:")
            self.videos = self.parse_videos(data)
        self.display_videos()

    def parse_videos(self, data):
        """Parsea la información de los vídeos recibidos del servidor."""
        videos = {}
        lines = data.split('\n')
        for line in lines:
            if line.strip():  # Ensure the line is not empty
                video_details = line.split(' available at ')
                video_name = video_details[0].split(' bytes')[0]
                servers = video_details[1:]
                videos[video_name] = {'servers': servers}
        return videos

    def display_videos(self):
        """Muestra los vídeos disponibles y el número de servidores en los que están disponibles."""
        for video, info in self.videos.items():
            print(f"{video}: Disponible en {len(info['servers'])} servidor(es)")
        video_choice = "ibai.mp4"
        self.request_video_download(video_choice)

    def request_video_download(self, video_name):
        """Solicita la descarga de un vídeo específico."""
        if video_name in self.videos:
            print(f"Opciones de descarga para {video_name}:")
            for index, server_info in enumerate(self.videos[video_name]['servers'], 1):
                print(f"{index}. {server_info}")
            server_choice = int(input("Seleccione el servidor desde el que desea descargar: "))
            server_info = self.videos[video_name]['servers'][server_choice - 1]
            print(f"Descargando {video_name} desde {server_info}...")
        else:
            print("Vídeo no encontrado.")
    def download_video(self, video_name, server_info):
        """Descarga un vídeo del servidor especificado."""
        host, port = server_info.split(':')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, int(port)))
            request = f"DOWNLOAD {video_name}"
            sock.sendall(request.encode())
            video_data = b''
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                video_data += data
            self.save_video(video_name, video_data)

    def save_video(self, video_name, video_data):
        """Guarda el vídeo descargado en un archivo en el disco."""
        directory = "video_Descargado"
        if not os.path.exists(directory):
            os.makedirs(directory)
        video_path = os.path.join(directory, f"{video_name}.mp4")
        with open(video_path, 'wb') as video_file:
            video_file.write(video_data)
        print(f"Vídeo {video_name} descargado y guardado correctamente en {video_path}.")

if __name__ == "__main__":
    client = P2PClient()
    client.connect_to_server()
