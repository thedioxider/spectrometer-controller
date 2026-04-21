# server.py
import socket
import ujson as json
import network


def connect_wifi(ssid: str, password: str):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            pass
    print("IP:", wlan.ifconfig()[0])


def parse_request(raw: bytes):
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    method, path, _ = lines[0].decode().split(" ", 2)
    headers = {}
    for line in lines[1:]:
        k, _, v = line.decode().partition(":")
        headers[k.strip().lower()] = v.strip()
    return method, path, headers, body


def read_full_body(client, body, headers):
    length = int(headers.get("content-length", 0))
    while len(body) < length:
        body += client.recv(min(1024, length - len(body)))
    return body


def respond(client, status: str, payload):
    body = json.dumps(payload).encode()
    client.send(b"HTTP/1.0 " + status.encode() + b"\r\n")
    client.send(b"Content-Type: application/json\r\n")
    client.send(b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n")
    client.send(body)


def handle_request(client, process_command):
    raw = client.recv(2048)
    if not raw:
        return
    method, path, headers, body = parse_request(raw)

    if method == "GET" and path == "/":
        return respond(client, "200 OK", {"ok": True, "service": "spectrometer"})

    if method == "POST" and path == "/api/spectrometer":
        body = read_full_body(client, body, headers)
        cmd = ""
        try:
            data = json.loads(body)
            cmd = data.get("command", "")
        except:
            cmd = body.decode("utf-8", errors="ignore")

        try:
            response_text, status = process_command(cmd)
            is_json = response_text.startswith("{") or response_text.startswith("[")
            if is_json:
                respond(client, status, json.loads(response_text))
            else:
                respond(client, status, {"response": response_text})
        except Exception as e:
            respond(client, "500 Internal Error", {"error": str(e)})
        return

    respond(client, "404 Not Found", {"error": "not found"})


def start_server(process_command, port: int = 80):
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(2)
    print("Server listening on port", port)
    while True:
        client, _ = s.accept()
        try:
            handle_request(client, process_command)
        except Exception as e:
            print("Error:", e)
        finally:
            client.close()