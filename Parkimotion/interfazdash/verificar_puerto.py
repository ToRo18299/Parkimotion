import serial

try:
    ser = serial.Serial("COM6", 115200, timeout=1)
    print("✅ COM6 abierto correctamente.")
    ser.close()
except Exception as e:
    print(f"❌ Error accediendo a COM6: {e}")
