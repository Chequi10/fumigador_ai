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
        try:
            print(f"Conectando a {self.port} con baudios {self.baudrate} y unit {self.unit}")
            # Inicializar el cliente Modbus y la conexión
            self.client = ModbusSerialClient(port=self.port, baudrate=self.baudrate, 
                                             timeout=3, stopbits=1, bytesize=8, parity='N')
            if not self.client.connect():
                print("No se pudo conectar al dispositivo Modbus.")
                return False
            return True
        except Exception as e:
            print(f"Error al conectar: {e}")
            return False

    def leer_registros(self, address, count):
        max_intentos = 3
        for intento in range(1, max_intentos + 1):
            try:
                print(f"Intentando leer registros... (Intento {intento}/{max_intentos})")
                response = self.client.read_holding_registers(address=address, count=count)
                if response.isError():
                    print(f"Error al leer los registros en el intento {intento}. Respuesta con error.")
                else:
                    humedad = response.registers[0] / 10  # Convierte a %
                    temperatura = response.registers[1] / 10      # Convierte a grados
                    
                    print(f"\nHumedad: {humedad}%, Temperatura: {temperatura}°C\n")

                    return response.registers
            except ModbusIOException as e:
                print(f"No response received after {intento} retries. Error: {e}")
                if intento == max_intentos:
                    print("Desconectando el cliente Modbus debido a fallos repetidos.")
                    self.client.close()
                    return None
            time.sleep(1)  # Esperar entre intentos
            
           

    
    def cerrar_conexion(self):
            if self.client:
                print("Cerrando conexión Modbus...")
                self.client.close()
                self.client = None