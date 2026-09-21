import os
import serial.tools.list_ports

def main():
    # 1. Cari port ESP
    esp_port = "/dev/ttyUSB0" # Default jika tidak ketemu
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        desc = port.description.upper()
        if "CH340" in desc or "CP210" in desc or "USB SERIAL" in desc:
            esp_port = port.device
            break
            
    print(f"[*] ESP32 terdeteksi di port: {esp_port}")

    # 2. Update file .env
    env_file = "/home/panelkopasus/apipanelkps/.env"
    
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.readlines()
    else:
        lines = []

    new_lines = []
    found = False
    for line in lines:
        if line.startswith("ESP32_PORT="):
            new_lines.append(f"ESP32_PORT={esp_port}\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        new_lines.append(f"ESP32_PORT={esp_port}\n")

    with open(env_file, "w") as f:
        f.writelines(new_lines)
        
    print("[*] File .env berhasil diperbarui!")

if __name__ == "__main__":
    main()
