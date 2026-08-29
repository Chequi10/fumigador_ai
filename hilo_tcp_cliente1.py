import threading
import json
import time
import sqlite3
import socket
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion


# Configuración del broker MQTT
MQTT_BROKER = "69.55.60.99"
MQTT_PORT = 1883
MQTT_TOPIC = "tractor/datos"
MQTT_CLIENT_ID = "jetson-fumigador"

semaforo = threading.Semaphore(1)
archivo_db = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/coordenadas_db"
stop_event = threading.Event()
evento_valvula_izquierda = threading.Event()

def tengo_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

def marcar_datos_como_enviados(ids):
    evento_valvula_izquierda.set()
    try:
        with sqlite3.connect(archivo_db) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE coordenadas SET enviado = 1 WHERE id IN ({})".format(','.join('?' * len(ids))), ids)
            conn.commit()
            print(f"{len(ids)} filas marcadas como enviadas.")
    except Exception as e:
        print(f"\033[31mError al marcar datos como enviados: {e}\033[0m")

def obtener_datos_pendientes(limite=100):
    try:
        with sqlite3.connect(archivo_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad,
                       velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta,
                       angulo_relativo_ajustado, velocidad_aparente, presion_barra, bateria, estado
                FROM coordenadas
                WHERE enviado = 0
                LIMIT ?
            """, (limite,))
            return cursor.fetchall()
    except Exception as e:
        print(f"\033[31mError al obtener datos pendientes: {e}\033[0m")
        return []

def server_remote():
    
    cliente_mqtt = mqtt.Client(client_id=MQTT_CLIENT_ID)

    try:
        cliente_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
        cliente_mqtt.loop_start()

        while not stop_event.is_set():
            if not tengo_internet():
                print("\033[33m 🚫📶 Sin conexión a internet. Reintentando más tarde...\033[0m")
                time.sleep(3)
                continue

            datos_pendientes = obtener_datos_pendientes(limite=100)

            if not datos_pendientes:
                print("No hay datos pendientes para enviar.")
                time.sleep(3)
                continue

            ids_confirmados = []

            for i, dato in enumerate(datos_pendientes):
                print(f"Enviando {i+1}/{len(datos_pendientes)}")
                id, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad, velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta, angulo_relativo_ajustado, velocidad_aparente, presion_barra, bateria, estado = dato

                mensaje_json = json.dumps({
                    "id": id,
                    "latitud": latitud,
                    "longitud": longitud,
                    "rumbo": rumbo,
                    "fecha": fecha,
                    "velocidad": velocidad,
                    "temperatura": temperatura,
                    "humedad": humedad,
                    "velocidad_viento": velocidad_viento,
                    "angulo_viento": angulo_viento,
                    "presion": presion,
                    "punto_rocio": punto_rocio,
                    "humedad_absoluta": humedad_absoluta,
                    "angulo_relativo_ajustado": angulo_relativo_ajustado,
                    "velocidad_aparente": velocidad_aparente,
                    "presion_barra": presion_barra,
                    "bateria": bateria,
                    "estado": estado
                })

                try:
                    cliente_mqtt.publish(MQTT_TOPIC, mensaje_json)
                    print(f"📡 Publicado MQTT: {mensaje_json}")
                    ids_confirmados.append(id)
                except Exception as e:
                    print(f"\033[31mError al publicar por MQTT para id {id}: {e}\033[0m")

            if ids_confirmados:
                marcar_datos_como_enviados(ids_confirmados)

            time.sleep(3)

    except Exception as e:
        print(f"\033[31mError general MQTT: {e}\033[0m")
    finally:
        cliente_mqtt.loop_stop()
        cliente_mqtt.disconnect()
