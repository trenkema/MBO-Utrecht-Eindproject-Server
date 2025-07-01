import wifi
import socketpool
import time
import select
import microcontroller

class Server:
    def __init__(self, port=1235):
        self.port = port
        self.pool = None
        self.server = None
        self.conn = None
        self.buffer = bytearray(1024)

    def start_ap(self, ssid="myAP", password="password123"):
        wifi.radio.start_ap(ssid=ssid, password=password)
        print("AP started. IP address:", wifi.radio.ipv4_address)
        time.sleep(3)  # Let AP stabilize

    def start_server(self):
        if not self.pool:
            self.pool = socketpool.SocketPool(wifi.radio)
            self.server = self.pool.socket(self.pool.AF_INET, self.pool.SOCK_STREAM)
            self.server.settimeout(0)  # Non-blocking
            try:
                self.server.bind(("0.0.0.0", self.port))
            except OSError as e:
                if e.errno == 112:  # EADDRINUSE
                    print(f"[Server] Port {self.port} is already in use. Restarting...")
                    self.server.close()
                    microcontroller.reset()
                    return
                else:
                    self.server.close()
                    microcontroller.reset()
                    return

            self.server.listen(1)
            print(f"[Server] Listening on 0.0.0.0:{self.port}")

        if not self.conn:
            try:
                self.conn, addr = self.server.accept()
                self.conn.setblocking(False)
                print("[Server] Client connected from", addr)
            except OSError:
                # No incoming connection yet — this is okay
                pass

    def poll(self):
        if not self.conn:
            return None

        try:
            r, _, _ = select.select([self.conn], [], [], 0)
            if self.conn in r:
                n = self.conn.recv_into(self.buffer)
                if n == 0:
                    print("[Server] Client disconnected")
                    self.close()
                    return None
                data = self.buffer[:n].decode().strip()
                print(f"[Server] Received: {data}")
                return data
        except Exception as e:
            print("[Server] Poll error:", e)
            self.close()
        return None

    def send_command(self, cmd: str):
        if self.conn:
            try:
                print(f"[Server] Sending: {cmd}")
                self.conn.send(cmd.encode())
            except Exception as e:
                print("[Server] Send error:", e)
                self.close()

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass
            self.server = None
