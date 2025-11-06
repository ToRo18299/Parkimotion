import serial
import threading
import time
import re
import numpy as np
from scipy.signal import butter, filtfilt

puerto_lectura = "COM6"
puerto_escritura = "COM11"
baudrate = 115200

ser_lectura = None
ser_escritura = None

ser_lock = threading.Lock()
serial_listo = threading.Event()
hilo_inicializado = False
buffer_size = 300
data_buffer = []

# Regex actualizado para aceptar "Hz"
patron = re.compile(
    r"ACC_X:\s*(-?\d+\.\d+),\s*ACC_Y:\s*(-?\d+\.\d+),\s*ACC_Z:\s*(-?\d+\.\d+)\s*\|\s*F_Z\(filt\):\s*(-?\d+\.\d+)\s*\|\s*Freq:\s*(-?\d+\.\d+)(?:\s*Hz)?\s*\|\s*Ref:\s*(-?\d+\.\d+)\s*\|\s*Motor:\s*(-?\d+\.\d+)"
)

def leer_serial():
    global ser_lectura
    with ser_lock:
        try:
            ser_lectura = serial.Serial(puerto_lectura, baudrate, timeout=1)
            serial_listo.set()
        except Exception as e:
            print(f"❌ Error al abrir {puerto_lectura}: {e}")
            serial_listo.clear()
            return

    while True:
        try:
            linea = ser_lectura.readline().decode(errors='ignore').strip()
            print(f"🔄 Línea recibida: {linea}")

            match = patron.match(linea)
            if match:
                acc_x = float(match.group(1))
                acc_y = float(match.group(2))
                acc_z = float(match.group(3))
                freq_est = float(match.group(5))
                timestamp = time.time()

                data_buffer.append((timestamp, acc_x, acc_y, acc_z, freq_est))
                if len(data_buffer) > buffer_size:
                    data_buffer.pop(0)
                print(f" Datos guardados. Tamaño buffer: {len(data_buffer)}")
        except Exception as e:
            print(f"Error en lectura serial: {e}")

def iniciar_hilo_serial():
    global hilo_inicializado
    if not hilo_inicializado:
        hilo = threading.Thread(target=leer_serial, daemon=True)
        hilo.start()
        hilo_inicializado = True

ultima_frecuencia_enviada = None

def enviar_frecuencia(f):
    global ser_escritura, ultima_frecuencia_enviada

    try:
        # Validar entrada
        if f is None:
            print("⚠️ Frecuencia no válida (None).")
            return

        # Evitar reenvíos innecesarios
        if ultima_frecuencia_enviada is not None and round(f, 2) == round(ultima_frecuencia_enviada, 2):
            return

        ultima_frecuencia_enviada = f
        comando = f"{f:.2f}\n"

        # Abrir puerto si es necesario
        if ser_escritura is None or not ser_escritura.is_open:
            try:
                ser_escritura = serial.Serial(puerto_escritura, baudrate, timeout=1)
                print(f"🔌 Puerto {puerto_escritura} abierto.")
            except Exception as e:
                print(f"❌ No se pudo abrir {puerto_escritura}: {e}")
                return

        # Enviar comando protegido
        with ser_lock:
            if ser_escritura and ser_escritura.is_open:
                ser_escritura.write(comando.encode())
                print(f"📤 Enviada frecuencia por COM11 → {comando.strip()}")

    except Exception as e:
        print(f"❌ Error inesperado en enviar_frecuencia(): {e}")

def obtener_datos_filtrados(eje="Z", ventana_segundos=5):
    if not data_buffer or len(data_buffer) < 50:
        return [], []

    idx = {"X": 1, "Y": 2, "Z": 3}[eje.upper()]
    t0 = data_buffer[0][0]
    tiempos = [row[0] - t0 for row in data_buffer]

    tiempo_actual = tiempos[-1]
    datos_filtrados = [
        (t, row[idx]) for t, row in zip(tiempos, data_buffer)
        if (tiempo_actual - t) <= ventana_segundos
    ]

    if len(datos_filtrados) < 50:
        return [], []

    t_filtrado, acc_filtrado = zip(*datos_filtrados)
    acc = np.array(acc_filtrado)

    fs = 40
    b, a = butter(4, [3, 7], btype='bandpass', fs=fs)
    acc_filtrado = filtfilt(b, a, acc)

    return list(t_filtrado), acc_filtrado

def obtener_fft(eje="Z"):
    if not data_buffer or len(data_buffer) < 50:
        return [], []

    idx = {"X": 1, "Y": 2, "Z": 3}[eje.upper()]
    acc = np.array([row[idx] for row in data_buffer])
    fs = 40
    b, a = butter(4, [3, 7], btype='bandpass', fs=fs)
    acc_filt = filtfilt(b, a, acc)
    ventana = np.hanning(len(acc_filt))
    senal = acc_filt * ventana
    fft_vals = np.fft.fft(senal)
    N = len(fft_vals)
    freqs = np.fft.fftfreq(N, d=1/fs)
    magnitudes = np.abs(fft_vals[:N//2])
    freqs = freqs[:N//2]
    magnitudes /= np.max(magnitudes) if np.max(magnitudes) != 0 else 1
    return freqs, magnitudes

from scipy.fft import fft, fftfreq

def obtener_frecuencia_dominante(eje="Z", ref_freq=None, ancho=1.0):
    if not data_buffer or len(data_buffer) < 50:
        return 0.0

    idx = {"X": 1, "Y": 2, "Z": 3}[eje.upper()]
    acc = np.array([row[idx] for row in data_buffer])
    fs = 40  # Frecuencia de muestreo

    # Aplicar filtrado pasa banda y ventana Hann
    b, a = butter(4, [3, 7], btype='bandpass', fs=fs)
    acc_filt = filtfilt(b, a, acc)
    ventana = np.hanning(len(acc_filt))
    señal = acc_filt * ventana

    # FFT real
    N = len(señal)
    freqs = fftfreq(N, d=1/fs)[:N//2]
    mags = np.abs(fft(señal))[:N//2]

    if ref_freq is not None:
        mask = (freqs >= ref_freq - ancho/2) & (freqs <= ref_freq + ancho/2)
        if not np.any(mask):
            return ref_freq
        freqs_filtrados = freqs[mask]
        mags_filtrados = mags[mask]
        return freqs_filtrados[np.argmax(mags_filtrados)]
    else:
        return freqs[np.argmax(mags)]


def limpiar_buffer():
    global data_buffer
    data_buffer.clear()
def obtener_amplitud_pico(eje="Z"):
    if not data_buffer or len(data_buffer) < 50:
        return 0.0

    idx = {"X": 1, "Y": 2, "Z": 3}[eje.upper()]
    acc = np.array([row[idx] for row in data_buffer])
    fs = 40
    b, a = butter(4, [3, 7], btype='bandpass', fs=fs)
    acc_filt = filtfilt(b, a, acc)

    return np.max(np.abs(acc_filt))  # en unidades de g

def estimar_amplitud_cm(amplitud_g, frecuencia_hz):
    if frecuencia_hz is None or frecuencia_hz <= 0:
        return 0.0
    # a = A*(2πf)^2  =>  A = a / (4π²f²)
    a_m_s2 = amplitud_g * 9.81
    A_m = a_m_s2 / ((2 * np.pi * frecuencia_hz) ** 2)
    A_cm = A_m * 100
    return A_cm
