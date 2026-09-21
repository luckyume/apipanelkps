import os
import json
import threading
import time
from typing import Optional

import serial
from serial import SerialException

# --- TAMBAHAN WAJIB AGAR PYTHON MEMBACA FILE .ENV TERBARU ---
from dotenv import load_dotenv
load_dotenv("/home/panelkopasus/apipanelkps/.env")
# ------------------------------------------------------------

class ESP32Service:
    def __init__(self):
        # =====================================================
        # CONFIG
        # =====================================================
        self.port = os.getenv("ESP32_PORT", "/dev/ttyUSB0")
        self.baudrate = int(os.getenv("ESP32_BAUDRATE", "115200"))
        
        self.timeout = float(os.getenv("ESP32_TIMEOUT", "0.2"))
        self.status_timeout = float(os.getenv("ESP32_STATUS_TIMEOUT", "2.0"))
        # ------------------------------------------------------

        # =====================================================
        # SERIAL
        # =====================================================
        self.serial: Optional[serial.Serial] = None
        self.serial_lock = threading.Lock()
        self.status_condition = threading.Condition()
        self.running = True

        self.last_status_time = 0.0
        self.status_counter = 0
        # =====================================================
        # STATUS DEFAULT
        # =====================================================
        self.latest_status = {
            "ok": False,
            "type": "status",
            "connected": False,
            "tracker": {"enabled": False, "voltage": 0.0, "current": 0.0, "power": 0.0},
            "hm30": {"enabled": False, "voltage": 0.0, "current": 0.0, "power": 0.0},
            "total_power": 0.0,
            "energy_kwh": 0.0,
            "ac": {"valid": False, "voltage": 0.0, "current": 0.0, "power": 0.0, "energy": 0.0},
            "ssr1": {"enabled": False},
            "ssr2": {"enabled": False},
            "relay": {"enabled": False},
            "relay_protection": False,
            "alarm": None,
            "last_update": None,
        }

        self._connect()

        self.reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name="ESP32-Serial-Reader"
        )
        self.reader_thread.start()

        # =====================================================
        # AUTO START SSR1 & SSR2 KETIKA BOOT
        # =====================================================
        self.startup_thread = threading.Thread(
            target=self._startup_sequence,
            daemon=True,
            name="ESP32-Startup-Sequence"
        )
        self.startup_thread.start()

    def _startup_sequence(self):
        """
        Fungsi ini berjalan saat inisialisasi API.
        Memberikan jeda agar ESP32 selesai boot setelah koneksi serial, 
        lalu menembak SSR1, jeda 1 detik, lalu menembak SSR2.
        """
        print("[ESP32] Menunggu ESP32 siap untuk auto-start SSR...")
        # Jeda 3 detik karena saat serial connect, ESP32 hardware akan auto-reset
        time.sleep(10)
        
        try:
            print("[ESP32] Mengirim perintah True untuk SSR1 (BOOT1)...")
            self.set_ssr1(True)
            
            # Beri jeda 1 detik agar serial tidak bertabrakan
            time.sleep(1)
            print("[ESP32] Mengirim perintah True untuk SSR1 (BOOT2)...")
            self.set_ssr1(True)
            
            # Beri jeda 1 detik agar serial tidak bertabrakan
            time.sleep(1)
            print("[ESP32] Mengirim perintah True untuk SSR2 (BOOT)...")
            self.set_ssr2(True)
            
            print("[ESP32] Auto-start SSR1 dan SSR2 berhasil dikirim.")
        except Exception as e:
            print(f"[ESP32] Gagal mengirim auto-start SSR saat boot: {e}")

    def _connect(self):
        try:
            if self.serial is not None:
                try:
                    self.serial.close()
                except Exception:
                    pass
                self.serial = None

            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=1.0
            )

            try:
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
            except Exception:
                pass

            with self.status_condition:
                self.latest_status["connected"] = True
                self.status_condition.notify_all()

            print(f"[ESP32] Connected: {self.port} @ {self.baudrate}")
            return True

        except Exception as exc:
            self.serial = None
            with self.status_condition:
                self.latest_status["connected"] = False
                self.status_condition.notify_all()
            print(f"[ESP32] Connection failed: {exc}")
            return False

    def _ensure_connection(self):
        if self.serial is not None:
            try:
                if self.serial.is_open:
                    return True
            except Exception:
                pass
        return self._connect()

    def _close_serial(self):
        try:
            if self.serial is not None:
                self.serial.close()
        except Exception:
            pass
        finally:
            self.serial = None

    def _reader_loop(self):
        while self.running:
            try:
                if not self._ensure_connection():
                    time.sleep(2)
                    continue

                line = self.serial.readline()
                if not line:
                    continue

                text = line.decode("utf-8", errors="ignore").strip()
                if not text:
                    continue

                if not text.startswith("{"):
                    print(f"[ESP32] {text}")
                    continue

                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    print(f"[ESP32] Invalid JSON: {text}")
                    continue

                if data.get("type") == "status":
                    self._update_status(data)
                    continue

                if data.get("ok") is not None:
                    print(f"[ESP32] Response: {data}")
                    continue

            except (SerialException, OSError, UnicodeDecodeError) as exc:
                print(f"[ESP32] Serial error: {exc}")
                with self.status_condition:
                    self.latest_status["connected"] = False
                    self.status_condition.notify_all()
                self._close_serial()
                time.sleep(2)

            except Exception as exc:
                print(f"[ESP32] Reader error: {exc}")
                with self.status_condition:
                    self.latest_status["connected"] = False
                    self.status_condition.notify_all()
                time.sleep(1)

    def _update_status(self, data: dict):
        with self.status_condition:
            tracker = data.get("tracker", {})
            hm30 = data.get("hm30", {})
            ac = data.get("ac", {})

            self.latest_status = {
                "ok": bool(data.get("ok", True)),
                "type": "status",
                "connected": True,
                "tracker": {
                    "enabled": bool(tracker.get("enabled", False)),
                    "voltage": float(tracker.get("voltage", 0.0) or 0.0),
                    "current": float(tracker.get("current", 0.0) or 0.0),
                    "power": float(tracker.get("power", 0.0) or 0.0),
                },
                "hm30": {
                    "enabled": bool(hm30.get("enabled", False)),
                    "voltage": float(hm30.get("voltage", 0.0) or 0.0),
                    "current": float(hm30.get("current", 0.0) or 0.0),
                    "power": float(hm30.get("power", 0.0) or 0.0),
                },
                "total_power": float(data.get("total_power", 0.0) or 0.0),
                "energy_kwh": float(data.get("energy_kwh", 0.0) or 0.0),
                "ac": {
                    "valid": bool(ac.get("valid", False)),
                    "voltage": float(ac.get("voltage", 0.0) or 0.0),
                    "current": float(ac.get("current", 0.0) or 0.0),
                    "power": float(ac.get("power", 0.0) or 0.0),
                    "energy": float(ac.get("energy", 0.0) or 0.0),
                },
                "ssr1": {"enabled": bool(data.get("ssr1", False))},
                "ssr2": {"enabled": bool(data.get("ssr2", False))},
                # Relay Active-Low: jika ESP32 kirim false (LOW), berarti relay nyala (True)
                "relay": {"enabled": not bool(data.get("relay", False))},
                "relay_protection": bool(data.get("relay_protection", False)),
                "alarm": data.get("alarm", None),
                "last_update": time.time(),
            }
            self.last_status_time = time.time()
            self.status_counter += 1
            self.status_condition.notify_all()

    def send_command(self, command: str):
        command = command.strip()
        if not command:
            raise RuntimeError("Command ESP32 kosong")
        if not self._ensure_connection():
            raise RuntimeError("ESP32 tidak terhubung")

        with self.serial_lock:
            try:
                payload = (command + "\n").encode("utf-8")
                self.serial.write(payload)
                self.serial.flush()
            except Exception as exc:
                self._close_serial()
                with self.status_condition:
                    self.latest_status["connected"] = False
                    self.status_condition.notify_all()
                raise RuntimeError(f"Gagal mengirim command ke ESP32: {exc}") from exc

        return {"success": True, "command": command}

    def request_status(self):
        if not self._ensure_connection():
            raise RuntimeError("ESP32 tidak terhubung")

        with self.status_condition:
            old_counter = self.status_counter

        self.send_command("STATUS")

        deadline = time.monotonic() + self.status_timeout
        with self.status_condition:
            while self.status_counter <= old_counter:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self.status_condition.wait(timeout=remaining)

            if self.status_counter > old_counter:
                return dict(self.latest_status)

            status = dict(self.latest_status)
            status["status_request_timeout"] = True
            return status

    def get_status(self):
        return self.request_status()

    # =========================================================
    # TRACKER
    # =========================================================
    def set_tracker(self, state: bool):
        command = "TRACKER ON" if state else "TRACKER OFF"
        result = self.send_command(command)
        try:
            result["status"] = self.request_status()
        except Exception as exc:
            result["status_error"] = str(exc)
        return result

    # =========================================================
    # HM30
    # =========================================================
    def set_hm30(self, state: bool):
        command = "HM30 ON" if state else "HM30 OFF"
        result = self.send_command(command)
        try:
            result["status"] = self.request_status()
        except Exception as exc:
            result["status_error"] = str(exc)
        return result

    # =========================================================
    # SSR1
    # =========================================================
    def set_ssr1(self, state: bool):
        command = json.dumps({"device": "ssr1", "state": state}, separators=(',', ':'))
        result = self.send_command(command)
        try:
            result["status"] = self.request_status()
        except Exception as exc:
            result["status_error"] = str(exc)
        return result

    # =========================================================
    # SSR2
    # =========================================================
    def set_ssr2(self, state: bool):
        command = json.dumps({"device": "ssr2", "state": state}, separators=(',', ':'))
        result = self.send_command(command)
        try:
            result["status"] = self.request_status()
        except Exception as exc:
            result["status_error"] = str(exc)
        return result

    # =========================================================
    # RELAY
    # =========================================================
    def set_relay(self, state: bool):
        # Relay active-low: API TRUE (ingin nyala) -> kirim FALSE; API FALSE (ingin mati) -> kirim TRUE
        command = json.dumps({"device": "relay", "state": not state}, separators=(',', ':'))
        result = self.send_command(command)
        try:
            result["status"] = self.request_status()
        except Exception as exc:
            result["status_error"] = str(exc)
        return result

# =============================================================
# SINGLE ESP32 SERVICE INSTANCE
# =============================================================
esp32_service = ESP32Service()