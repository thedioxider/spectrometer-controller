import uasyncio as asyncio
import network
import ujson as json
from machine import Pin, ADC
from SpectrometerMotor import SpectrometerMotor
from SpectrometerOpticalPair import SpectrometerOpticalPair
from SpectrometerGrating import SpectrometerGrating
from Spectrometer import Spectrometer

# Network Configuration
WIFI_SSID = "YOUR_SSID"
WIFI_PASS = "YOUR_PASSWORD"

# Pin Configuration (ESP32)
MOTOR_EN = 12
MOTOR_DIR = 13
MOTOR_PUL = 14
LIGHT_SENSOR_PIN = 4
PHOTODIODE_ADC_PIN = 36

# Hardware Initialization
light_sensor = Pin(LIGHT_SENSOR_PIN, Pin.IN, Pin.PULL_DOWN)
photodiode = ADC(Pin(PHOTODIODE_ADC_PIN))
photodiode.width(ADC.WIDTH_12BIT)
photodiode.atten(ADC.ATTN_11DB)

def is_light():
    return light_sensor.value() == 1

def default_degree(current_grating=0):
    motor.disable()
    motor._current_steps = 0
    motor.enable()

def get_intensity():
    return photodiode.read()

# Patch necessary_functions module to use real hardware
import necessary_functions
necessary_functions.is_light = is_light
necessary_functions.default_degree = default_degree
necessary_functions.get_intensity = get_intensity

motor = SpectrometerMotor(en_pin=MOTOR_EN, dir_pin=MOTOR_DIR, pul_pin=MOTOR_PUL, revolution_steps=500)
optical = SpectrometerOpticalPair()
optical.is_receiving = is_light

grating = SpectrometerGrating(motor=motor, optical_pair=optical, center_offset=60, motor_ratio=144)
spec = Spectrometer(rotate_step=0.01, trust_quantity=2)

# Grating State Management
GRATING_STATE = {
    "current_grating": 1,
    "installed_gratings": [
        {"id": 1, "groove_density_mm": 1200, "blaze_nm": 500, "is_active": True},
        {"id": 2, "groove_density_mm": 600, "blaze_nm": 400, "is_active": False},
        {"id": 3, "groove_density_mm": 300, "blaze_nm": 350, "is_active": False}
    ]
}

def process_command(cmd: str):
    cmd = cmd.strip().upper()
    try:
        if "GOTO" in cmd:
            val = float(cmd.replace("GOTO", "").strip())
            spec.rotate_by_wavelength(val)
            return f"{val:.3f} nm", "200 OK"
        elif cmd == "?NM":
            wl = spec.get_current_wavelength()
            return f"{wl:.2f} nm", "200 OK"
        elif "NM/MIN" in cmd and "?" not in cmd:
            val = float(cmd.replace("NM/MIN", "").strip())
            motor.set_rate(int(val * 16))
            return f"{val:.2f} nm/min", "200 OK"
        elif cmd == "?NM/MIN":
            return "100.00 nm/min", "200 OK"
        elif "GRATING" in cmd and "?" not in cmd:
            val = int(cmd.replace("GRATING", "").strip())
            spec.current_grating = val
            grating.align_to_grating(val)
            GRATING_STATE["current_grating"] = val
            for g in GRATING_STATE["installed_gratings"]:
                g["is_active"] = (g["id"] == val)
            return str(val), "200 OK"
        elif cmd == "?GRATING":
            return str(GRATING_STATE["current_grating"]), "200 OK"
        elif cmd == "?GRATINGS":
            return json.dumps(GRATING_STATE), "200 OK"
        elif cmd.startswith("SET-GRATINGS"):
            payload_str = cmd[len("SET-GRATINGS"):].strip()
            data = json.loads(payload_str)
            if "gratings" in data and isinstance(data["gratings"], list):
                GRATING_STATE["installed_gratings"] = [
                    {**g, "is_active": g.get("id") == GRATING_STATE["current_grating"]}
                    for g in data["gratings"]
                ]
                return "Gratings updated", "200 OK"
            return "Invalid format", "400 Bad Request"
        elif "SCAN-FROM" in cmd:
            val = float(cmd.replace("SCAN-FROM", "").strip())
            spec.set_scan_from(val)
            return f"{val:.2f} nm", "200 OK"
        elif "SCAN-TO" in cmd:
            val = float(cmd.replace("SCAN-TO", "").strip())
            spec.set_scan_to(val)
            return f"{val:.2f} nm", "200 OK"
        elif cmd == "START-SCANS":
            asyncio.create_task(_run_scan_async())
            return "Scan started", "200 OK"
        else:
            return f"Unknown: {cmd}", "400 Bad Request"
    except ValueError:
        return "Invalid parameter", "400 Bad Request"
    except Exception as e:
        return str(e), "500 Internal Error"

async def _run_scan_async():
    data = spec.start_scan()
    print(f"Scan finished. {len(data)} points collected.")

async def handle_client(reader, writer):
    try:
        request_line = await reader.readline()
        if not request_line:
            return
        headers = {}
        while True:
            line = await reader.readline()
            if line == b'\r\n' or line == b'':
                break
            if b':' in line:
                k, v = line.split(b':', 1)
                headers[k.decode().strip().lower()] = v.decode().strip()
        content_length = int(headers.get('content-length', 0))
        body = b''
        if content_length > 0:
            body = await reader.readexactly(content_length)
        cmd = ""
        try:
            data = json.loads(body)
            cmd = data.get("command", "")
        except:
            cmd = body.decode("utf-8", errors="ignore")
        response_text, status = process_command(cmd)
        content_type = "application/json" if response_text.startswith("{") or response_text.startswith("[") else "text/plain"
        resp = f"HTTP/1.1 {status}\r\nContent-Type: {content_type}\r\nContent-Length: {len(response_text)}\r\n\r\n{response_text}"
        await writer.awrite(resp.encode())
    except Exception as e:
        await writer.awrite(f"HTTP/1.1 500\r\n\r\n{str(e)}".encode())
    finally:
        await writer.aclose()

async def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            await asyncio.sleep(0.5)
    print(f"IP: {wlan.ifconfig()[0]}")

async def main():
    await connect_wifi()
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
    print("Server listening on port 80")
    while True:
        await asyncio.sleep(1)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Stopped")