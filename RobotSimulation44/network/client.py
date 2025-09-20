# network/client.py
import socket
import threading
import json
import time

class Client:
    def __init__(self, host="127.0.0.1", port=5000, on_message=None, reconnect_interval=2):
        self.host = host
        self.port = port
        self.on_message = on_message
        self.conn = None
        self.running = False
        self._send_buffer = []  # queue until connected
        self.reconnect_interval = reconnect_interval

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        self.running = True
        while self.running:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    print(f"[Client] Connecting to {self.host}:{self.port}...")
                    s.connect((self.host, self.port))
                    self.conn = s
                    print("[Client] Connected!")

                    # Flush any queued messages
                    for msg in self._send_buffer:
                        self._send_raw(msg)
                    self._send_buffer.clear()

                    while self.running:
                        data = s.recv(4096)
                        if not data:
                            break
                        try:
                            msg = json.loads(data.decode("utf-8"))
                            if self.on_message:
                                self.on_message(msg)
                        except json.JSONDecodeError:
                            print("[Client] Invalid JSON received")
            except ConnectionRefusedError:
                print("[Client] Connection refused, retrying...")
                time.sleep(self.reconnect_interval)
            except OSError:
                break  # socket closed

    def _send_raw(self, msg):
        if self.conn:
            try:
                self.conn.sendall(json.dumps(msg).encode("utf-8"))
            except Exception as e:
                print("[Client] Send failed:", e)

    def send(self, msg):
        if self.conn:
            self._send_raw(msg)
        else:
            # Queue until connection established
            self._send_buffer.append(msg)
