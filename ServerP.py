import socket
import threading
import time

class MainServer:
    def __init__(self, host='192.168.100.125', port=8000):
        self.host = host
        self.port = port
        self.active_video_servers = {}

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        print(f"Main Server listening on {self.host}:{self.port}")
        threading.Thread(target=self.verificar_servidores_activos).start()

        try:
            while True:
                client_socket, address = self.socket.accept()
                print(f"Connection from {address}")
                threading.Thread(target=self.handle_connection, args=(client_socket, address)).start()
        except KeyboardInterrupt:
            print("Shutting down the server.")
            self.socket.close()

    def handle_connection(self, client_socket, address):
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            if data.startswith("REGISTER") or data.startswith("UPDATE"):
                self.register_video_server(data, address)
            elif data.startswith("QUERY"):
                self.respond_to_query(client_socket)
            print(f"Received data: {data} from {address}")
        client_socket.close()

    def register_video_server(self, data, address):
        _, server_info, *videos_info = data.split()
        host, port = server_info.split(':')
        videos = {video.split(':')[0]: {'size': int(video.split(':')[1])} for video in videos_info}
        self.active_video_servers[host] = {'details': videos, 'port': int(port), 'intentos_fallidos': 0}
        print(f"Video server {server_info} registered with videos: {videos}")

    def respond_to_query(self, client_socket):
        """Envía la información de todos los vídeos disponibles a los clientes, incluyendo servidor y puerto."""
        video_info = "\n".join(
            f"{video} {info['size']} bytes available at {server}:{details['port']}"
            for server, details in self.active_video_servers.items()
            for video, info in details['details'].items()
        )
        client_socket.sendall(video_info.encode())
    def verificar_servidores_activos(self):
        while True:
            time.sleep(10)
            for ip_servidor, detalles in list(self.active_video_servers.items()):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)  # Increased timeout
                try:
                    s.connect((ip_servidor, detalles['port']))
                    s.sendall(b'ping')
                    response = s.recv(1024)
                    if response != b'pong':
                        raise Exception("Respuesta incorrecta o ninguna respuesta recibida")
                except Exception as e:
                    detalles['intentos_fallidos'] += 1
                    if detalles['intentos_fallidos'] >= 3:
                        print(f"Servidor {ip_servidor} removido por inactividad.")
                        del self.active_video_servers[ip_servidor]
                    else:
                        print(f"Error en servidor {ip_servidor}: {e}, intentos fallidos: {detalles['intentos_fallidos']}")
                else:
                    detalles['intentos_fallidos'] = 0  # Reset on successful response
                finally:
                    s.close()

if __name__ == "__main__":
    port = int(input("Enter the port number to listen on: "))
    main_server = MainServer(port=port)
    main_server.start()
