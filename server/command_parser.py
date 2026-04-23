import uasyncio as asyncio
import ujson as json
from GratingParameters import GratingParameters
from Hardware_state import HardwareState
from Spectrometer import Spectrometer

class CommandParser:
    def __init__(self, spectrometer: Spectrometer, state: HardwareState):
        self.spec = spectrometer
        self.state = state
        self.grating_params = GratingParameters()
        self.scan_task = None

    def execute(self, cmd: str) -> tuple:
        cmd = cmd.strip().upper()
        try:
            if cmd.endswith("GOTO"):
                val = float(cmd.replace("GOTO", "").strip())
                self.spec.rotate_by_wavelength(val)
                return f"{val:.3f} nm", "200 OK"

            elif cmd == "?NM":
                return f"{self.spec.get_current_wavelength():.2f} nm", "200 OK"

            elif cmd.endswith("NM/MIN") and "?" not in cmd:
                val = float(cmd.replace("NM/MIN", "").strip())
                self.state.scan_speed_nm_per_min = val
                # Примечание: установка скорости мотора требует доступа к necessary_functions.
                # В текущей архитектуре это делается через адаптер при старте сканирования.
                return f"{val:.2f} nm/min", "200 OK"

            elif cmd == "?NM/MIN":
                return f"{self.state.scan_speed_nm_per_min:.2f} nm/min", "200 OK"

            elif cmd.endswith("GRATING") and "?" not in cmd:
                val = int(cmd.replace("GRATING", "").strip())
                from necessary_functions import default_degree
                default_degree(val)
                self.state.current_grating_id = val
                return str(val), "200 OK"

            elif cmd == "?GRATING":
                return str(self.spec.get_current_grating()), "200 OK"

            elif cmd == "?GRATINGS":
                return self.grating_params.to_json(), "200 OK"

            elif cmd.startswith("SET-GRATING"):
                val = int(cmd.replace("SET-GRATING", "").strip())
                self.grating_params.update_grating(val)
                return "Gratings updated", "200 OK"

            elif cmd.endswith("SCAN-FROM"):
                val = float(cmd.replace("SCAN-FROM", "").strip())
                self.spec.set_scan_from(val)
                self.state.scan_from = val
                return f"{val:.2f} nm", "200 OK"

            elif cmd.endswith("SCAN-TO"):
                val = float(cmd.replace("SCAN-TO", "").strip())
                self.spec.set_scan_to(val)
                self.state.scan_to = val
                return f"{val:.2f} nm", "200 OK"

            elif cmd == "START-SCANS":
                if self.scan_task and not self.scan_task.done():
                    return "Scan already in progress", "400 Bad Request"
                self.scan_task = asyncio.create_task(self._run_scan())
                return "Scan started", "200 OK"

            elif cmd == "?SCAN-STATUS":
                return self.state.get_status_summary(), "200 OK"

            elif cmd == "?SCAN-DATA":
                if self.state.scan_status == "completed":
                    data = self.state.get_scan_data()
                    return json.dumps(data), "200 OK"
                return "Scan not completed", "206 Partial Content"

            else:
                return f"Unknown: {cmd}", "400 Bad Request"

        except ValueError as e:
            return str(e), "400 Bad Request"
        except Exception as e:
            return str(e), "500 Internal Error"

    async def _run_scan(self):
        self.state.update_scan_status("running", 0.0)
        self.state.clear_scan_buffer()
        try:
            from necessary_functions import rotate_by_degree, rotate_by_step, get_intensity, current_degree
            import uasyncio as asyncio

            start_deg = self.state.scan_from
            stop_deg = self.state.scan_to

            rotate_by_degree(start_deg - current_degree())
            await asyncio.sleep(0.1)

            step_deg = 0.01
            current = current_degree()

            while current < stop_deg:
                rotate_by_degree(step_deg)
                await asyncio.sleep(0.05)
                intensity = get_intensity()
                current = current_degree()
                self.state.append_scan_point(current, intensity)
                progress = (current - start_deg) / (stop_deg - start_deg) * 100
                self.state.update_scan_status("running", min(progress, 100.0))

            self.state.update_scan_status("completed", 100.0)

        except Exception as e:
            self.state.update_scan_status("error", 0.0)
            self.state.error_message = str(e)