import socket
import threading
import json

class Server:
    def __init__(self, host="0.0.0.0", port=5000, on_message=None):
        self.host = host
        self.port = port
        self.on_message = on_message
        self.client_conn = None
        self.client_addr = None
        self.running = False
        self._send_buffer = []  # queue for messages until client connects

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        self.running = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(1)
            print(f"[Server] Listening on {self.host}:{self.port}")
            self.client_conn, self.client_addr = s.accept()
            print(f"[Server] Client connected from {self.client_addr}")

            # Flush any queued messages
            for msg in self._send_buffer:
                self._send_raw(msg)
            self._send_buffer.clear()

            with self.client_conn:
                while self.running:
                    try:
                        data = self.client_conn.recv(4096)
                        if not data:
                            break
                        try:
                            msg = json.loads(data.decode("utf-8"))
                            if self.on_message:
                                self.on_message(msg)
                        except json.JSONDecodeError:
                            print("[Server] Invalid JSON received")
                    except ConnectionResetError:
                        break

    def _send_raw(self, msg):
        if self.client_conn:
            try:
                self.client_conn.sendall(json.dumps(msg).encode("utf-8"))
            except Exception as e:
                print("[Server] Send failed:", e)
                self.client_conn = None  # mark as closed

    def send(self, msg):
        if self.client_conn:
            self._send_raw(msg)
        else:
            print("[Server] No client connected; queuing")
            self._send_buffer.append(msg)
