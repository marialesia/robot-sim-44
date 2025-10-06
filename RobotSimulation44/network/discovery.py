# network/discovery.py
import socket, threading, json, time

BROADCAST_PORT = 5001
DISCOVERY_MESSAGE = {"service": "warehouse-sim", "port": 5000}


class DiscoveryBroadcaster:
    def __init__(self, interval=2):
        # Initialize the broadcaster with a given interval in seconds
        self.interval = interval
        self.running = False

    def start(self):
        # Start broadcasting discovery messages in a background thread
        thread = threading.Thread(target=self._run, daemon=True)
        self.running = True
        thread.start()

    def _run(self):
        # Send discovery messages periodically over UDP broadcast
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(0.2)
            while self.running:
                try:
                    # Build a fresh message each time so we don't mutate the global
                    msg = DISCOVERY_MESSAGE.copy()
                    msg["ip"] = self._get_local_ip()
                    s.sendto(json.dumps(msg).encode("utf-8"), ('<broadcast>', BROADCAST_PORT))
                except Exception as e:
                    print("[DiscoveryBroadcaster] Error:", e)
                time.sleep(self.interval)

    def stop(self):
        # Stop broadcasting messages
        self.running = False

    def _get_local_ip(self):
        # Determine the local IP address of this machine
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"


class DiscoveryListener:
    def __init__(self, on_found):
        # Initialize listener with a callback function `on_found(ip, port)`
        self.on_found = on_found
        self.running = False

    def start(self):
        # Start listening for discovery messages in a background thread
        thread = threading.Thread(target=self._run, daemon=True)
        self.running = True
        thread.start()

    def _run(self):
        # Listen for UDP broadcast messages and call `on_found` for valid services
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", BROADCAST_PORT))
            while self.running:
                try:
                    data, addr = s.recvfrom(1024)
                    msg = json.loads(data.decode("utf-8"))
                    if msg.get("service") == "warehouse-sim":
                        ip, port = msg["ip"], msg["port"]
                        self.on_found(ip, port)
                except Exception:
                    pass

    def stop(self):
        # Stop listening for discovery messages
        self.running = False
