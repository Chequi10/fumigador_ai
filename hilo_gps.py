import serial
import queue
import time
import threading
from datetime import datetime

semaforo = threading.Semaphore(1)
lock = threading.Lock()
idconta = 1
stop_event = threading.Event()

# Cola para almacenar los datos que deben enviarse por TCP
cola_gps = queue.Queue()

def conectar_puerto(puerto="/dev/ttyACM0", baudrate=9600, timeout=1):
    """Establece conexión con el GPS y devuelve el objeto serial."""
    try:
        ser = serial.Serial(puerto, baudrate, timeout=timeout)
        print(f"🟢 Conectado al GPS en {puerto} a {baudrate} baudios")
        return ser
    except serial.SerialException as e:
        print(f"\033[31mError al abrir el puerto serie: {e}\033[0m")
        return None

def convertir_grados_nmea(valor, direccion):
    """Convierte coordenadas NMEA a grados decimales."""
    if not valor:
        return None

    if direccion in ['N', 'S']:  # Latitud
        grados = int(valor[:2])
        minutos = float(valor[2:])
    elif direccion in ['E', 'W']:  # Longitud
        grados = int(valor[:3])
        minutos = float(valor[3:])
    else:
        return None

    resultado = grados + (minutos / 60)
    if direccion in ['S', 'W']:
        resultado *= -1
    return resultado

def task_gps():
    global velocidad, latitud, longitud, fecha, idconta, id, rumbo

    puerto_gps = "/dev/ttyACM0"  # Ajustar según corresponda
    gps_serial = conectar_puerto(puerto_gps)

    if not gps_serial:
        return  # No pudo conectar

    try:
        while not stop_event.is_set():
            try:
                linea = gps_serial.readline().decode(errors='ignore').strip()
                if linea.startswith("$GPRMC") or linea.startswith("$GNRMC"):
                    datos = linea.split(",")
                    if len(datos) >= 10:
                        # --- 1) Validación RMC (A=válido, V=inválido) ---
                        status = datos[2] if len(datos) > 2 else ""
                        if status != "A":
                            # imprimí "inválido" cada 2s para no spamear
                            ahora = time.time()
                            if not hasattr(task_gps, "_t_inv"):
                                task_gps._t_inv = 0
                            if ahora - task_gps._t_inv > 2:
                                print("\033[33m[GPS] Datos inválidos (sin fix)\033[0m")
                                task_gps._t_inv = ahora
                            continue

                        # --- 2) Convertir coordenadas ---
                        lat = convertir_grados_nmea(datos[3], datos[4])
                        lon = convertir_grados_nmea(datos[5], datos[6])

                        if lat is None or lon is None:
                            ahora = time.time()
                            if not hasattr(task_gps, "_t_inv2"):
                                task_gps._t_inv2 = 0
                            if ahora - task_gps._t_inv2 > 2:
                                print("\033[33m[GPS] Datos inválidos (lat/lon vacíos)\033[0m")
                                task_gps._t_inv2 = ahora
                            continue

                        # --- 3) YA ES VÁLIDO: recién acá redondeo (evita NoneType) ---
                        latitud = round(lat, 6)
                        longitud = round(lon, 6)

                        rumbo = float(datos[8]) if datos[8] else 0.0

                        # Manejo robusto de la hora
                        hora_raw = datos[1]
                        fecha_raw = datos[9]
                        if not hora_raw or not fecha_raw:
                            ahora = time.time()
                            if not hasattr(task_gps, "_t_inv3"):
                                task_gps._t_inv3 = 0
                            if ahora - task_gps._t_inv3 > 2:
                                print("\033[33m[GPS] Datos inválidos (fecha/hora vacías)\033[0m")
                                task_gps._t_inv3 = ahora
                            continue

                        if "." in hora_raw:
                            hora = datetime.strptime(hora_raw, "%H%M%S.%f").strftime("%H:%M:%S")
                        else:
                            hora = datetime.strptime(hora_raw, "%H%M%S").strftime("%H:%M:%S")

                        fecha = f"{datetime.strptime(fecha_raw, '%d%m%y').strftime('%Y-%m-%d')} {hora}"
                        velocidad = round(float(datos[7]) * 1.852, 2) if datos[7] else 0.0

                        idconta = (idconta % 6) + 1
                        id = 2

                        # --- 4) Cola EXACTAMENTE igual que antes (mismo tuple) ---
                        cola_gps.put((id, latitud, longitud, rumbo, fecha, velocidad))

                        # imprimir válido cada 2s para no spamear
                        ahora = time.time()
                        if not hasattr(task_gps, "_t_ok"):
                            task_gps._t_ok = 0
                        if ahora - task_gps._t_ok > 2:
                            print(f"\033[32m[GPS] OK lat={latitud} lon={longitud} rumbo={rumbo}\033[0m")
                            task_gps._t_ok = ahora

                        #print(f"\033[36m\nID:{id}    Latitud: {latitud}   Longitud:{longitud}   Fecha: {fecha}   Velocidad: {velocidad} km/h  Rumbo: {rumbo}\n\033[0m")
            except Exception as e:
                print(f"\033[31mError leyendo GPS: {e}\033[0m")

    finally:
        gps_serial.close()