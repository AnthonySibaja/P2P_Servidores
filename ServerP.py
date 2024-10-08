import socket
import threading
import time

class MainServer:
    def __init__(self, host='192.168.100.125', port=8001):
        self.host = host
        self.port = port
        self.active_video_servers = {}

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.log(f"Main Server listening on {self.host}:{self.port}")
        threading.Thread(target=self.verificar_servidores_activos).start()

        try:
            while True:
                client_socket, address = self.socket.accept()
                self.log(f"Connection from {address}", header="New Connection")
                threading.Thread(target=self.handle_connection, args=(client_socket, address)).start()
        except KeyboardInterrupt:
            self.log("Shutting down the server.")
            self.socket.close()

    def handle_connection(self, client_socket, address):
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            action = "REGISTER" if "REGISTER" in data else "UPDATE" if "UPDATE" in data else "QUERY"
            if action in ["REGISTER", "UPDATE"]:
                self.register_video_server(data, address)
            elif action == "QUERY":
                self.respond_to_query(client_socket)
            self.log(f"Received data: {data}", header=f"{action} Request")
        client_socket.close()

    def register_video_server(self, data, address):
        _, server_info, *videos_info = data.split()
        host, port = server_info.split(':')
        videos = {video.split(':')[0]: {'size': int(video.split(':')[1])} for video in videos_info}
        for video_name, info in videos.items():
            if video_name in self.active_video_servers:
                self.active_video_servers[video_name].append({'host': host, 'port': int(port), 'details': info})
            else:
                self.active_video_servers[video_name] = [{'host': host, 'port': int(port), 'details': info}]
        
        self.log(f"Video server {server_info} registered with videos:\n" + "\n".join(f"{k}: {v['size']} bytes" for k, v in videos.items()), header="Server Registration")

    def respond_to_query(self, client_socket):
        video_info = "\n".join(
            f"{video} {server['details']['size']} bytes available at {server['host']}:{server['port']}"
            for video, servers in self.active_video_servers.items()
            for server in servers
        )
        client_socket.sendall(video_info.encode())

    def verificar_servidores_activos(self):
        while True:
            time.sleep(10)
            for video, servers in list(self.active_video_servers.items()):
                for server in list(servers):
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(10)
                    try:
                        s.connect((server['host'], server['port']))
                        s.sendall(b'ping')
                        response = s.recv(1024)
                        if response != b'pong':
                            raise Exception("Respuesta incorrecta o ninguna respuesta recibida")
                    except Exception as e:
                        server['intentos_fallidos'] = server.get('intentos_fallidos', 0) + 1
                        if server['intentos_fallidos'] >= 3:
                            servers.remove(server)
                            self.log(f"Servidor {server['host']}:{server['port']} removido por inactividad.", header="Server Check")
                        else:
                            self.log(f"Error en servidor {server['host']}:{server['port']}: {e}, intentos fallidos: {server['intentos_fallidos']}", header="Server Error")
                    else:
                        server['intentos_fallidos'] = 0  # Reset on successful response
                    finally:
                        s.close()
                if not servers:
                    del self.active_video_servers[video]

    def log(self, message, header="Log"):
        print(f"--- {header} ---")
        print(message)
        print("--- End ---\n")

if __name__ == "__main__":
    port = 8001
    main_server = MainServer(port=port)
    main_server.start()
