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
                self.spec.change_grating(val)
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
                return f"{val:.2f} nm", "200 OK"

            elif cmd.endswith("SCAN-TO"):
                val = float(cmd.replace("SCAN-TO", "").strip())
                self.spec.set_scan_to(val)
                return f"{val:.2f} nm", "200 OK"

            elif cmd == "START-SCANS":
                ans = self.spec.start_scan()
                return str(ans), "200 OK"

            elif cmd.startswith("CALIBRATE"):
                wl = float(cmd.replace("CALIBRATE", "").strip())
                self.spec.calibrate(wl)
                return f"Calibrating to {wl:.1f} nm", "200 OK"

            elif cmd == "NEXT-GRATING":
                self.spec.next_grating()
                return "Switching to next grating", "200 OK"

            elif cmd == "PREV-GRATING":
                self.spec.prev_grating()
                return "Switching to previous grating", "200 OK"
            
            # elif cmd == "?SCAN-STATUS":
            #     return self.state.get_status_summary(), "200 OK"
            #
            # elif cmd == "?SCAN-DATA":
            #     if self.state.scan_status == "completed":
            #         data = self.state.get_scan_data()
            #         return json.dumps(data), "200 OK"
            #     return "Scan not completed", "206 Partial Content"

            else:
                return f"Unknown: {cmd}", "400 Bad Request"

        except ValueError as e:
            return str(e), "400 Bad Request"
        except Exception as e:
            return str(e), "500 Internal Error"
