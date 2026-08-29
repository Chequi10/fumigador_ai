import queue
import time
import threading
import math
import pandas as pd
from modulo_temperatura import obtener_temperatura_core0
from modbus_usb import ModbusRTU

cola_modbus = queue.Queue()
semaforo = threading.Semaphore(1)
stop_event = threading.Event()


def task_modbus():
    # Crear una instancia del cliente Modbus una sola vez
    modbus = ModbusRTU(port='/dev/ttyUSB0', baudrate=4800, unit=1)
    
    # Intentar conectar antes de entrar en el bucle
    if not modbus.conectar():
        print("\033[31mError al conectar al dispositivo Modbus. Abortando tarea...\033[0m")
        return  # Si no se puede conectar, abortamos la tarea

    max_intentos = 5  # Número máximo de intentos para reconectar
    intentos = 0  # Contador de intentos

    while not stop_event.is_set():
        try:
            variables = {
                "humedad":           {"direccion": 0x1F8, "escala": 10},
                "temperatura":       {"direccion": 0x1F9, "escala": 10},
                "presion":           {"direccion": 0x1FD, "escala": 1},
                "velocidad_viento":  {"direccion": 0x1F4, "escala": 10},
                "angulo_viento":     {"direccion": 0x1F7, "escala": 1}
            }

            datos = {}

            for nombre, config in variables.items():
                registros = modbus.leer_registros(address=config["direccion"], count=2)
                if registros:
                    valor = registros[0] / config["escala"]
                    datos[nombre] = valor
                else:
                    datos[nombre] = None
                    print(f"⚠ No se pudo leer {nombre} en la dirección {hex(config['direccion'])}")

            humedad = datos["humedad"]
            temperatura = datos["temperatura"]
            presion = datos["presion"]
            velocidad_viento = datos["velocidad_viento"]
            angulo_viento = datos["angulo_viento"]

            
            """
            
                                 Esto lo uso si desde el excel
****************************************************************************************
            redondeado_humedad = math.floor(humedad)
            redondeado_temperatura = math.floor(temperatura)
            redondeado_angulo_viento = math.floor(temperatura)  # Parece que hay un error aquí, debería ser angulo_viento
            redondeado_presion = math.floor(presion)

            # Procesar el archivo de Excel
            archivo_excel = "/home/jetson/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/deltat_eze.xlsx"
            df = pd.read_excel(archivo_excel, sheet_name='DONE')
            CM10 = redondeado_temperatura  # El valor que deseas buscar en la primera columna
            CM11 = redondeado_humedad  # El valor con el que deseas hacer coincidir la fila

            fila = df[df.iloc[:, 0] == CM10]
            columna_idx = df.columns.get_loc(CM11)

            Condiciones = fila.iloc[0, columna_idx]

            # Imprimir el valor encontrado
            print(f'El valor correspondiente es: {Condiciones}').
            
****************************************************************************************     """

            cola_modbus.put((temperatura, humedad, velocidad_viento, angulo_viento, presion))

            # Esperar un poco antes de la próxima lectura
            time.sleep(0.01)

        except Exception as e:
            # Manejo de excepciones
            print(f"\033[31mError: {e}\033[0m")
            intentos += 1

            if intentos >= max_intentos:
                print("Número máximo de intentos alcanzado. Esperando 10 segundos antes de reintentar...")
                time.sleep(10)
                intentos = 0  # Resetear los intentos
            else:
                time.sleep(1)

    # Asegurarse de cerrar la conexión cuando se detenga el proceso
    modbus.cerrar_conexion()
