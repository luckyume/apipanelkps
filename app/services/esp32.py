import os
import json
import threading
import time
from typing import Optional

import serial
from serial import SerialException


class ESP32Service:

    def __init__(self):
        # =====================================================
        # CONFIG
        # =====================================================

        self.port = os.getenv(
            "ESP32_PORT",
            "COM28"
        )

        self.baudrate = int(
            os.getenv(
                "ESP32_BAUDRATE",
                "115200"
            )
        )

        self.timeout = float(
            os.getenv(
                "ESP32_TIMEOUT",
                "0.2"
            )
        )

        self.status_timeout = float(
            os.getenv(
                "ESP32_STATUS_TIMEOUT",
                "2.0"
            )
        )

        # =====================================================
        # SERIAL
        # =====================================================

        self.serial: Optional[serial.Serial] = None

        self.serial_lock = threading.Lock()

        self.status_condition = threading.Condition()

        self.running = True

        # Waktu terakhir menerima JSON status
        self.last_status_time = 0.0

        # Counter status
        self.status_counter = 0

        # =====================================================
        # STATUS DEFAULT
        # =====================================================

        self.latest_status = {
            "ok": False,
            "type": "status",

            "connected": False,

            "tracker": {
                "enabled": False,
                "voltage": 0.0,
                "current": 0.0,
                "power": 0.0,
            },

            "hm30": {
                "enabled": False,
                "voltage": 0.0,
                "current": 0.0,
                "power": 0.0,
            },

            "total_power": 0.0,

            "energy_kwh": 0.0,

            "ac": {
                "valid": False,
                "voltage": 0.0,
                "current": 0.0,
                "power": 0.0,
                "energy": 0.0,
            },

            "relay_protection": False,

            "alarm": None,

            "last_update": None,
        }

        # =====================================================
        # CONNECT
        # =====================================================

        self._connect()

        # =====================================================
        # READER THREAD
        # =====================================================

        self.reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name="ESP32-Serial-Reader"
        )

        self.reader_thread.start()

    # =========================================================
    # CONNECT
    # =========================================================

    def _connect(self):

        try:

            # Tutup koneksi lama jika ada
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

            # Bersihkan buffer
            try:
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()

            except Exception:
                pass

            with self.status_condition:

                self.latest_status["connected"] = True

                self.status_condition.notify_all()

            print(
                f"[ESP32] Connected: "
                f"{self.port} @ {self.baudrate}"
            )

            return True

        except Exception as exc:

            self.serial = None

            with self.status_condition:

                self.latest_status["connected"] = False

                self.status_condition.notify_all()

            print(
                f"[ESP32] Connection failed: {exc}"
            )

            return False

    # =========================================================
    # ENSURE CONNECTION
    # =========================================================

    def _ensure_connection(self):

        if self.serial is not None:

            try:

                if self.serial.is_open:

                    return True

            except Exception:
                pass

        return self._connect()

    # =========================================================
    # CLOSE SERIAL
    # =========================================================

    def _close_serial(self):

        try:

            if self.serial is not None:

                self.serial.close()

        except Exception:
            pass

        finally:

            self.serial = None

    # =========================================================
    # READER LOOP
    # =========================================================

    def _reader_loop(self):

        while self.running:

            try:

                if not self._ensure_connection():

                    time.sleep(2)

                    continue

                # =============================================
                # BACA 1 BARIS
                # =============================================

                line = self.serial.readline()

                if not line:

                    continue

                text = line.decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                if not text:

                    continue

                # =============================================
                # LOG BIASA
                # =============================================

                if not text.startswith("{"):

                    print(
                        f"[ESP32] {text}"
                    )

                    continue

                # =============================================
                # JSON
                # =============================================

                try:

                    data = json.loads(text)

                except json.JSONDecodeError:

                    print(
                        f"[ESP32] Invalid JSON: {text}"
                    )

                    continue

                # =============================================
                # STATUS
                # =============================================

                if data.get("type") == "status":

                    self._update_status(
                        data
                    )

                    continue

                # =============================================
                # RESPONSE COMMAND
                # =============================================

                if data.get("ok") is not None:

                    print(
                        f"[ESP32] Response: {data}"
                    )

                    continue

            except (
                SerialException,
                OSError,
                UnicodeDecodeError
            ) as exc:

                print(
                    f"[ESP32] Serial error: {exc}"
                )

                with self.status_condition:

                    self.latest_status[
                        "connected"
                    ] = False

                    self.status_condition.notify_all()

                self._close_serial()

                time.sleep(2)

            except Exception as exc:

                print(
                    f"[ESP32] Reader error: {exc}"
                )

                with self.status_condition:

                    self.latest_status[
                        "connected"
                    ] = False

                    self.status_condition.notify_all()

                time.sleep(1)

    # =========================================================
    # UPDATE STATUS
    # =========================================================

    def _update_status(
        self,
        data: dict
    ):

        with self.status_condition:

            # -----------------------------------------------
            # Jangan replace seluruh object secara buta.
            # Kita normalisasi supaya API selalu punya struktur
            # yang konsisten.
            # -----------------------------------------------

            tracker = data.get(
                "tracker",
                {}
            )

            hm30 = data.get(
                "hm30",
                {}
            )

            ac = data.get(
                "ac",
                {}
            )

            self.latest_status = {

                "ok": bool(
                    data.get(
                        "ok",
                        True
                    )
                ),

                "type": "status",

                "connected": True,

                "tracker": {
                    "enabled": bool(
                        tracker.get(
                            "enabled",
                            False
                        )
                    ),

                    "voltage": float(
                        tracker.get(
                            "voltage",
                            0.0
                        ) or 0.0
                    ),

                    "current": float(
                        tracker.get(
                            "current",
                            0.0
                        ) or 0.0
                    ),

                    "power": float(
                        tracker.get(
                            "power",
                            0.0
                        ) or 0.0
                    ),
                },

                "hm30": {
                    "enabled": bool(
                        hm30.get(
                            "enabled",
                            False
                        )
                    ),

                    "voltage": float(
                        hm30.get(
                            "voltage",
                            0.0
                        ) or 0.0
                    ),

                    "current": float(
                        hm30.get(
                            "current",
                            0.0
                        ) or 0.0
                    ),

                    "power": float(
                        hm30.get(
                            "power",
                            0.0
                        ) or 0.0
                    ),
                },

                "total_power": float(
                    data.get(
                        "total_power",
                        0.0
                    ) or 0.0
                ),

                "energy_kwh": float(
                    data.get(
                        "energy_kwh",
                        0.0
                    ) or 0.0
                ),

                "ac": {
                    "valid": bool(
                        ac.get(
                            "valid",
                            False
                        )
                    ),

                    "voltage": float(
                        ac.get(
                            "voltage",
                            0.0
                        ) or 0.0
                    ),

                    "current": float(
                        ac.get(
                            "current",
                            0.0
                        ) or 0.0
                    ),

                    "power": float(
                        ac.get(
                            "power",
                            0.0
                        ) or 0.0
                    ),

                    "energy": float(
                        ac.get(
                            "energy",
                            0.0
                        ) or 0.0
                    ),
                },

                "relay_protection": bool(
                    data.get(
                        "relay_protection",
                        False
                    )
                ),

                "alarm": data.get(
                    "alarm",
                    None
                ),

                "last_update": time.time(),
            }

            self.last_status_time = time.time()

            self.status_counter += 1

            self.status_condition.notify_all()

    # =========================================================
    # SEND COMMAND
    # =========================================================

    def send_command(
        self,
        command: str
    ):

        command = command.strip()

        if not command:

            raise RuntimeError(
                "Command ESP32 kosong"
            )

        if not self._ensure_connection():

            raise RuntimeError(
                "ESP32 tidak terhubung"
            )

        with self.serial_lock:

            try:

                # -------------------------------------------
                # Bersihkan input buffer.
                #
                # Jangan hapus terlalu agresif karena reader
                # thread bisa sedang membaca status.
                # -------------------------------------------

                payload = (
                    command + "\n"
                ).encode(
                    "utf-8"
                )

                self.serial.write(
                    payload
                )

                self.serial.flush()

            except Exception as exc:

                self._close_serial()

                with self.status_condition:

                    self.latest_status[
                        "connected"
                    ] = False

                    self.status_condition.notify_all()

                raise RuntimeError(
                    f"Gagal mengirim command ke ESP32: {exc}"
                ) from exc

        return {
            "success": True,
            "command": command,
        }

    # =========================================================
    # REQUEST STATUS
    # =========================================================

    def request_status(self):

        if not self._ensure_connection():

            raise RuntimeError(
                "ESP32 tidak terhubung"
            )

        # Ambil counter sebelum request.
        with self.status_condition:

            old_counter = (
                self.status_counter
            )

        # =============================================
        # KIRIM STATUS
        # =============================================

        self.send_command(
            "STATUS"
        )

        # =============================================
        # TUNGGU ESP32 MEMBALAS
        # =============================================

        deadline = (
            time.monotonic()
            + self.status_timeout
        )

        with self.status_condition:

            while (
                self.status_counter
                <= old_counter
            ):

                remaining = (
                    deadline
                    - time.monotonic()
                )

                if remaining <= 0:

                    break

                self.status_condition.wait(
                    timeout=remaining
                )

            # =========================================
            # Cek apakah mendapat status baru
            # =========================================

            if (
                self.status_counter
                > old_counter
            ):

                return dict(
                    self.latest_status
                )

            # =========================================
            # Timeout
            # =========================================

            # Kalau sebelumnya pernah punya status,
            # tetap kembalikan status terakhir tetapi tandai
            # bahwa request terbaru timeout.
            status = dict(
                self.latest_status
            )

            status[
                "status_request_timeout"
            ] = True

            return status

    # =========================================================
    # GET STATUS
    # =========================================================

    def get_status(self):

        return self.request_status()

    # =========================================================
    # TRACKER
    # =========================================================

    def tracker_on(self):

        return self.send_command(
            "TRACKER ON"
        )

    def tracker_off(self):

        return self.send_command(
            "TRACKER OFF"
        )

    def set_tracker(
        self,
        state: bool
    ):

        if state:

            result = self.tracker_on()

        else:

            result = self.tracker_off()

        # Ambil status terbaru setelah command.
        try:

            status = self.request_status()

            result["status"] = status

        except Exception as exc:

            result["status_error"] = str(
                exc
            )

        return result

    # =========================================================
    # HM30
    # =========================================================

    def hm30_on(self):

        return self.send_command(
            "HM30 ON"
        )

    def hm30_off(self):

        return self.send_command(
            "HM30 OFF"
        )

    def set_hm30(
        self,
        state: bool
    ):

        if state:

            result = self.hm30_on()

        else:

            result = self.hm30_off()

        # Ambil status terbaru setelah command.
        try:

            status = self.request_status()

            result["status"] = status

        except Exception as exc:

            result["status_error"] = str(
                exc
            )

        return result

    # =========================================================
    # RELAY
    #
    # ESP32 yang Anda kirim saat ini BELUM mempunyai command:
    # RELAY ON / RELAY OFF.
    #
    # Fungsi ini dipertahankan untuk kompatibilitas API,
    # tetapi jangan digunakan sebelum command tersebut
    # ditambahkan di ESP32.
    # =========================================================

    def relay_on(self):

        return self.send_command(
            "RELAY ON"
        )

    def relay_off(self):

        return self.send_command(
            "RELAY OFF"
        )

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):

        self.running = False

        self._close_serial()

        with self.status_condition:

            self.latest_status[
                "connected"
            ] = False

            self.status_condition.notify_all()


# =============================================================
# SINGLE ESP32 SERVICE INSTANCE
# =============================================================

esp32_service = ESP32Service()