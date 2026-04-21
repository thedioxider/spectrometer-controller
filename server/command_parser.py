import uasyncio as asyncio
from GratingParameters import GratingParameters

class CommandParser:
    def __init__(self, spec, motor, grating):
        self.spec = spec
        self.motor = motor
        self.grating = grating
        self.grating_params = GratingParameters()

    def execute(self, cmd):
        cmd = cmd.strip().upper()
        try:
            if "GOTO" in cmd:
                val = float(cmd.replace("GOTO", "").strip())
                self.spec.rotate_by_wavelength(val)
                return f"{val:.3f} nm", "200 OK"
            elif cmd == "?NM":
                return f"{self.spec.get_current_wavelength():.2f} nm", "200 OK"
            elif "NM/MIN" in cmd and "?" not in cmd:
                val = float(cmd.replace("NM/MIN", "").strip())
                self.motor.set_rate(int(val * 16))
                return f"{val:.2f} nm/min", "200 OK"
            elif cmd == "?NM/MIN":
                return "100.00 nm/min", "200 OK"
            elif "GRATING" in cmd and "?" not in cmd:
                val = int(cmd.replace("GRATING", "").strip())
                self.grating_params.set_active(val)
                self.spec.current_grating = val
                self.grating.align_to_grating(val)
                return str(val), "200 OK"
            elif cmd == "?GRATING":
                return str(self.grating_params.get_active_id()), "200 OK"
            elif cmd == "?GRATINGS":
                return self.grating_params.to_json(), "200 OK"
            elif cmd.startswith("SET-GRATINGS"):
                payload = cmd[len("SET-GRATINGS"):].strip()
                self.grating_params.update(payload)
                return "Gratings updated", "200 OK"
            elif "SCAN-FROM" in cmd:
                val = float(cmd.replace("SCAN-FROM", "").strip())
                self.spec.set_scan_from(val)
                return f"{val:.2f} nm", "200 OK"
            elif "SCAN-TO" in cmd:
                val = float(cmd.replace("SCAN-TO", "").strip())
                self.spec.set_scan_to(val)
                return f"{val:.2f} nm", "200 OK"
            elif cmd == "START-SCANS":
                asyncio.create_task(self._run_scan())
                return "Scan started", "200 OK"
            else:
                return f"Unknown: {cmd}", "400 Bad Request"
        except ValueError as e:
            return str(e), "400 Bad Request"
        except Exception as e:
            return str(e), "500 Internal Error"

    async def _run_scan(self):
        data = self.spec.start_scan()
        print(f"Scan done: {len(data)} points")