import uasyncio as asyncio
import ujson as json
import network
from command_parser import CommandParser
from Hardware_state import HardwareState
from Spectrometer import Spectrometer


def parse_request(raw: bytes):
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    method, path, _ = lines[0].decode().split(" ", 2)
    headers = {}
    for line in lines[1:]:
        k, _, v = line.decode().partition(":")
        headers[k.strip().lower()] = v.strip()
    return method, path, headers, body


async def read_full_body(reader, body, headers):
    length = int(headers.get("content-length", 0))
    while len(body) < length:
        chunk = await reader.read(min(1024, length - len(body)))
        if not chunk:
            break
        body += chunk
    return body


async def respond(writer, status: str, payload):
    body = json.dumps(payload).encode()
    writer.write(b"HTTP/1.1 " + status.encode() + b"\r\n")
    writer.write(b"Content-Type: application/json\r\n")
    writer.write(b"Content-Length: " + str(len(body)).encode() + b"\r\n")
    writer.write(b"\r\n")
    writer.write(body)
    await writer.drain()


async def handle_request(reader, writer, parser: CommandParser):
    try:
        raw = await reader.read(2048)
        if not raw:
            writer.close()
            return
        method, path, headers, body = parse_request(raw)

        if method == "GET" and path == "/":
            await respond(writer, "200 OK", {"ok": True, "service": "spectrometer"})
        elif method == "POST" and path == "/api/spectrometer":
            body = await read_full_body(reader, body, headers)
            cmd = ""
            try:
                data = json.loads(body)
                cmd = data.get("command", "")
            except:
                cmd = body.decode("utf-8", errors="ignore")

            try:
                response_text, status = parser.execute(cmd)
                if isinstance(response_text, str) and (response_text.startswith("{") or response_text.startswith("[")):
                    await respond(writer, status, json.loads(response_text))
                else:
                    await respond(writer, status, {"response": response_text})
            except Exception as e:
                await respond(writer, "500 Internal Error", {"error": str(e)})
        else:
            await respond(writer, "404 Not Found", {"error": "not found"})
    except Exception as e:
        print("Request error:", e)
    finally:
        writer.close()


async def start_server_async(parser: CommandParser, port: int = 80):
    server = await asyncio.start_server(
        lambda reader, writer: handle_request(reader, writer, parser),
        "0.0.0.0",
        port
    )
    print(f"Server listening on port {port}")
    while True:
        await asyncio.sleep(1)

