import os
import json
import threading
import time
import serial


class ESP32Service:

    def __init__(self):
        self.port = os.getenv("ESP32_PORT", "COM5")
        self.baudrate = int(os.getenv("ESP32_BAUDRATE", "115200"))

        self.serial = None

        self.lock = threading.Lock()

        self.latest_status = {
            "connected": False,
            "tracker": False,
            "hm30": False,
            "relay": False,
            "voltage1": 0.0,
            "voltage2": 0.0,
            "current1": 0.0,
            "current2": 0.0,
            "power": 0.0,
            "ac_voltage": None,
            "ac_current": None,
            "ac_power": None,
            "ac_energy": None,
            "uptime": 0,
        }

        self.running = True

        self._connect()

        self.reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True
        )

        self.reader_thread.start()


    # =========================================================
    # CONNECT
    # =========================================================

    def _connect(self):

        try:

            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.2,
            )

            self.latest_status["connected"] = True

            print(
                f"[ESP32] Connected: "
                f"{self.port} @ {self.baudrate}"
            )

        except Exception as e:

            self.serial = None

            self.latest_status["connected"] = False

            print(
                f"[ESP32] Connection failed: {e}"
            )


    # =========================================================
    # RECONNECT
    # =========================================================

    def _ensure_connection(self):

        if self.serial is not None:
            if self.serial.is_open:
                return True

        self._connect()

        return self.serial is not None


    # =========================================================
    # READER
    # =========================================================

    def _reader_loop(self):

        while self.running:

            try:

                if not self._ensure_connection():
                    time.sleep(2)
                    continue


                line = self.serial.readline()


                if not line:
                    continue


                text = line.decode(
                    "utf-8",
                    errors="ignore"
                ).strip()


                if not text:
                    continue


                # ESP32 juga mengirim log seperti:
                # [ESP32] READY
                # [HM30] Power ON
                #
                # Hanya proses JSON.

                if not text.startswith("{"):
                    print(f"[ESP32] {text}")
                    continue


                try:

                    data = json.loads(text)

                except json.JSONDecodeError:

                    print(
                        f"[ESP32] Invalid JSON: {text}"
                    )

                    continue


                if data.get("type") != "status":
                    continue


                with self.lock:

                    self.latest_status.update(data)

                    self.latest_status[
                        "connected"
                    ] = True


            except Exception as e:

                print(
                    f"[ESP32] Reader error: {e}"
                )


                with self.lock:

                    self.latest_status[
                        "connected"
                    ] = False


                try:

                    if self.serial:
                        self.serial.close()

                except Exception:
                    pass


                self.serial = None

                time.sleep(2)


    # =========================================================
    # SEND COMMAND
    # =========================================================

    def send_command(self, command: str):

        if not self._ensure_connection():

            raise RuntimeError(
                "ESP32 tidak terhubung"
            )


        command = command.strip()


        with self.lock:

            self.serial.write(
                (command + "\n").encode("utf-8")
            )

            self.serial.flush()


        return {
            "success": True,
            "command": command
        }


    # =========================================================
    # GET STATUS
    # =========================================================

    def get_status(self):

        with self.lock:

            return dict(
                self.latest_status
            )


    # =========================================================
    # TRACKER
    # =========================================================

    def tracker_on(self):

        return self.send_command(
            "TRACKER_ON"
        )


    def tracker_off(self):

        return self.send_command(
            "TRACKER_OFF"
        )


    # =========================================================
    # HM30
    # =========================================================

    def hm30_on(self):

        return self.send_command(
            "HM30_ON"
        )


    def hm30_off(self):

        return self.send_command(
            "HM30_OFF"
        )


    # =========================================================
    # RELAY
    # =========================================================

    def relay_on(self):

        return self.send_command(
            "RELAY_ON"
        )


    def relay_off(self):

        return self.send_command(
            "RELAY_OFF"
        )


    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):

        self.running = False

        try:

            if self.serial:
                self.serial.close()

        except Exception:
            pass


# =============================================================
# SINGLE ESP32 SERVICE INSTANCE
# =============================================================

esp32_service = ESP32Service()