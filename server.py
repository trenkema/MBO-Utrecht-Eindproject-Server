import wifi
import socketpool
import time
import select
import microcontroller
import secrets

class Server:
    def __init__(self, port=1235):
        """
        Initialize the Server instance.
        
        Args:
            port (int): TCP port number to listen on.
        """
        self.port = port          # Port to listen on
        self.pool = None          # SocketPool object for managing sockets
        self.server = None        # The server socket that listens for connections
        self.conn = None          # The client connection socket (once accepted)
        self.buffer = bytearray(1024)  # Buffer for receiving incoming data

    def start_ap(self):
        """
        Start the device as a Wi-Fi Access Point (AP) with given SSID and password.
        
        Args:
            ssid (str): Wi-Fi SSID for the AP.
            password (str): Password for the AP.
        """
        wifi.radio.start_ap(secrets.SSID, secrets.PASSWORD)
        print("AP started. IP address:", wifi.radio.ipv4_address)
        time.sleep(3)  # Pause to allow AP to stabilize before accepting connections

    def start_server(self):
        """
        Create the TCP server socket and listen for incoming connections.
        Accepts a client connection when one arrives.
        """
        if not self.pool:
            # Create a socket pool associated with the Wi-Fi radio
            self.pool = socketpool.SocketPool(wifi.radio)
            # Create a TCP socket for IPv4
            self.server = self.pool.socket(self.pool.AF_INET, self.pool.SOCK_STREAM)
            self.server.settimeout(0)  # Set socket to non-blocking mode

            try:
                # Bind server socket to all interfaces on specified port
                self.server.bind(("0.0.0.0", self.port))
            except OSError as e:
                if e.errno == 112:  # EADDRINUSE - Address already in use
                    print(f"[Server] Port {self.port} is already in use. Restarting...")
                    self.server.close()
                    microcontroller.reset()  # Reset device to try again
                    return
                else:
                    # Other binding error — close and reset device
                    self.server.close()
                    microcontroller.reset()
                    return

            # Start listening for incoming connections (max backlog 1)
            self.server.listen(1)
            print(f"[Server] Listening on 0.0.0.0:{self.port}")

        if not self.conn:
            try:
                # Accept a client connection if available
                self.conn, addr = self.server.accept()
                self.conn.setblocking(False)  # Set client socket to non-blocking
                print("[Server] Client connected from", addr)
            except OSError:
                # No client trying to connect yet; this is normal behavior in non-blocking mode
                pass

    def poll(self):
        """
        Check if any data is available to read from the connected client.
        
        Returns:
            str or None: Received string data if available, otherwise None.
        """
        if not self.conn:
            return None  # No active client connection

        try:
            # Use select to check if the socket is ready for reading (with zero timeout)
            r, _, _ = select.select([self.conn], [], [], 0)
            if self.conn in r:
                # Receive data into buffer
                n = self.conn.recv_into(self.buffer)
                if n == 0:
                    # Client disconnected gracefully
                    print("[Server] Client disconnected")
                    self.close()
                    return None
                # Decode bytes to string, strip whitespace/newlines
                data = self.buffer[:n].decode().strip()
                print(f"[Server] Received: {data}")
                return data
        except Exception as e:
            # Any exception during polling - close connection and report
            print("[Server] Poll error:", e)
            self.close()
        return None

    def send_command(self, cmd: str):
        """
        Send a command string to the connected client.
        
        Args:
            cmd (str): The command string to send.
        """
        if self.conn:
            try:
                print(f"[Server] Sending: {cmd}")
                self.conn.send(cmd.encode())  # Send encoded command bytes
            except Exception as e:
                # On send failure, close connection
                print("[Server] Send error:", e)
                self.close()

    def close(self):
        """
        Close the client connection and server socket safely.
        """
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