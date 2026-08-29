import queue
import time
import threading
import math
import pandas as pd  # opcional si usás Excel
from modulo_temperatura import obtener_temperatura_core0  # opcional
from modbus_usb import ModbusRTU

# Recursos compartidos
cola_modbus = queue.Queue()
semaforo = threading.Semaphore(1)
stop_event = threading.Event()

def task_modbus():
    puerto_alias = '/dev/ttyUSB_modbus'  # crear con udev
    baudrate = 4800
    unit = 1

    # Reintentos y tiempos
    max_intentos_conexion = 5
    espera_reintento_conexion = 2  # s
    espera_reconexion_por_error = 5  # s
    periodo_lectura = 1.0  # s, 1 Hz es razonable para 4800 bps

    # Puertos candidatos por si el alias no existe aún
    candidatos = [puerto_alias, '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2']

    modbus = None

    def conectar_modbus():
        """Intenta abrir el puerto con varios intentos y puertos candidatos."""
        nonlocal modbus
        intento = 0
        while intento < max_intentos_conexion and not stop_event.is_set():
            for puerto in candidatos:
                try:
                    modbus = ModbusRTU(port=puerto, baudrate=baudrate, unit=unit)
                    if modbus.conectar():
                        print(f"\033[32mConexión Modbus establecida en {puerto}\033[0m")
                        return True
                except Exception as e:
                    print(f"\033[31mError al conectar en {puerto}: {e}\033[0m")
            intento += 1
            print(f"Reintento de conexión {intento}/{max_intentos_conexion} en {espera_reintento_conexion}s...")
            time.sleep(espera_reintento_conexion)
        return False

    if not conectar_modbus():
        print("\033[31mNo fue posible establecer la conexión Modbus. Tarea abortada.\033[0m")
        return

    variables = {
        "humedad":           {"direccion": 0x1F8, "escala": 10},
        "temperatura":       {"direccion": 0x1F9, "escala": 10},
        "presion":           {"direccion": 0x1FD, "escala": 10},
        "velocidad_viento":  {"direccion": 0x1F4, "escala": 10},
        "angulo_viento":     {"direccion": 0x1F7, "escala": 10},
    }

    while not stop_event.is_set():
        try:
            datos = {}
            for nombre, cfg in variables.items():
                registros = modbus.leer_registros(address=cfg["direccion"], count=2)
                if registros:
                    # Si el equipo usa 1 registro, el valor está en registros[0]
                    # Si usa 2 registros (32 bits), ajustar según tu ModbusRTU
                    valor = registros[0] / cfg["escala"]
                    datos[nombre] = valor
                else:
                    datos[nombre] = None
                    print(f"⚠ No se pudo leer {nombre} en {hex(cfg['direccion'])}")

            cola_modbus.put((
                datos["temperatura"],
                datos["humedad"],
                datos["velocidad_viento"],
                datos["angulo_viento"],
                datos["presion"],
            ))

            time.sleep(periodo_lectura)

        except Exception as e:
            print(f"\033[31mError en lectura Modbus: {e}\033[0m")
            try:
                if modbus:
                    modbus.cerrar_conexion()
            except Exception:
                pass
            print(f"Intento de reconexión en {espera_reconexion_por_error}s...")
            time.sleep(espera_reconexion_por_error)
            if not conectar_modbus():
                print("\033[31mReconexión fallida. Se continúa intentando...\033[0m")

    # Cierre ordenado
    try:
        if modbus:
            modbus.cerrar_conexion()
    except Exception:
        pass
