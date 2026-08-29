
import subprocess
import re

def obtener_temperatura_core0():
    try:
        # Ejecuta el comando 'sensors' y obtiene la salida
        resultado = subprocess.run(['sensors'], capture_output=True, text=True, check=True)
        
        # Busca la línea que contiene "Core 0"
        for linea in resultado.stdout.split("\n"):
            if "Core 0" in linea:
                # Extrae la temperatura usando expresiones regulares
                match = re.search(r'(\+?\d+\.\d+)°C', linea)
                if match:
                    return float(match.group(1))  # Devuelve la temperatura como número

    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar sensors: {e}")

    return None  # Si no encuentra la temperatura
                