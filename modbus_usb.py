from pymodbus.client import ModbusSerialClient
import time
from pymodbus.exceptions import ModbusIOException
import threading

class ModbusRTU:
    def __init__(self, port, baudrate, unit):
        self.port = port
        self.baudrate = baudrate
        self.unit = unit
        self.client = None  # Aquí se agregará el cliente de Modbus cuando se inicialice

    def conectar(self):
        """Abre la conexión Modbus una sola vez."""
        try:
            if self.client:
                print("Ya hay una conexión abierta.")
                return True  # Ya está conectado

            print(f"Conectando la estación Meteorológica {self.port} con baudios {self.baudrate} y unit {self.unit}")
            # Inicializar el cliente Modbus y la conexión
            self.client = ModbusSerialClient(port=self.port, baudrate=self.baudrate, 
                                             timeout=3, stopbits=1, bytesize=8, parity='N')
            if not self.client.connect():
                print("\033[31mNo se pudo conectar al dispositivo Modbus.\033[0m")
                return False
            return True
        except Exception as e:
            print(f"\033[31mError al conectar: {e}\033[0m")
            return False

    def leer_registros(self, address, count):
        max_intentos = 3
        for intento in range(1, max_intentos + 1):
            try:
                
                response = self.client.read_holding_registers(address=address, count=count)
                if response.isError():
                    print(f"Intentando leer registros... (Intento {intento}/{max_intentos})")
                   
                else:
                   
                    return response.registers
            except ModbusIOException as e:
                print(f"\033[31mNo response received after {intento} retries. Error: {e}\033[0m")
                if intento == max_intentos:
                    print("Desconectando el cliente Modbus debido a fallos repetidos.")
                    self.client.close()
                    return None
            time.sleep(0.001)  # Esperar entre intentos
            
           

    
    def cerrar_conexion(self):
            if self.client:
                print("Cerrando la conexión de la Estacion metereologica ")
                self.client.close()
                self.client = None