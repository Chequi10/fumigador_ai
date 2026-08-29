import json
import mysql.connector
import paho.mqtt.client as mqtt
import queue
import threading
import time

# Configuración de la base de datos
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="ezemaria",
    database="coordenadas_db"
)
cursor = db.cursor()

# Configuración del broker MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "tractor/datos"

# Cola para almacenar los datos a procesar
cola_datos = queue.Queue(maxsize=10)

# Función para insertar en la base de datos
def insertar_en_db(data):
    try:
        id = data.get("id")
        latitud = data.get("latitud")
        longitud = data.get("longitud")
        rumbo = data.get("rumbo")
        fecha = data.get("fecha")
        velocidad = data.get("velocidad")
        temperatura = data.get("temperatura")
        humedad = data.get("humedad")
        velocidad_viento = data.get("velocidad_viento")
        angulo_viento = data.get("angulo_viento")
        presion = data.get("presion")
        punto_rocio = data.get("punto_rocio")
        humedad_absoluta = data.get("humedad_absoluta")
        angulo_relativo_ajustado = data.get("angulo_relativo_ajustado")
        velocidad_aparente = data.get("velocidad_aparente")
        altura_aplicacion = data.get("altura_aplicacion")
        delta_t = data.get("delta_t")
        caudal_actual = data.get("caudal_actual")
        flujometro = data.get("flujometro")
        taponamiento = data.get("taponamiento")
        deriva = data.get("deriva")
        evaporacion = data.get("evaporacion")
        condiciones = data.get("condiciones")
        ancho = data.get("ancho")
        largo = data.get("largo")
        extra_1 = data.get("extra_1")
        extra_2 = data.get("extra_2")
        presion_actual = data.get("presion_actual")
        bateria = data.get("bateria")
        estado = data.get("estado")

        if all(v is not None and v != "" for v in [id, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad, velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta, angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual, flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2, presion_actual, bateria, estado]):
            sql = """
            INSERT IGNORE INTO coordenadas (id_vehiculo, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad,
                           velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta,
                           angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual,
                           flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2, presion_actual, bateria, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s )
            """
            cursor.execute(sql, (id, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad, velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta, angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual, flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2, presion_actual, bateria, estado))
            db.commit()
        else:
            print("⚠️ Datos incompletos")
    except Exception as e:
        print(f"❌ Error al insertar en la base de datos: {e}")

# Función para procesar los datos en un hilo separado
def procesar_datos():
    while True:
        try:
            paquete = cola_datos.get()
            guardados = 0
            descartados = 0

            for item in paquete:
                campos = [
                    item.get("id"), item.get("latitud"), item.get("longitud"), item.get("rumbo"), item.get("fecha"),
                    item.get("velocidad"), item.get("temperatura"), item.get("humedad"),
                    item.get("velocidad_viento"), item.get("angulo_viento"), item.get("presion"),
                    item.get("punto_rocio"), item.get("humedad_absoluta"), item.get("angulo_relativo_ajustado"),
                    item.get("velocidad_aparente"), item.get("altura_aplicacion"), item.get("delta_t"), item.get("caudal_actual"), item.get("flujometro"),
                    item.get("taponamiento"), item.get("deriva"), item.get("evaporacion"),
                    item.get("condiciones"), item.get("ancho"), item.get("largo"),
                    item.get("extra_1"), item.get("extra_2"), item.get("presion_actual"),        
                      item.get("bateria"), item.get("estado")
                ]

                if all(v is not None and v != "" for v in campos):
                    try:
                        sql = """
                        INSERT IGNORE INTO coordenadas (
                            id_vehiculo, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad,
                           velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta,
                           angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual,
                           flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2, presion_actual, bateria, estado
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(sql, campos)
                        db.commit()
                        guardados += 1
                    except Exception as e:
                        print(f"❌ Error al insertar un registro: {e}")
                else:
                    descartados += 1

            print(f"✅ Guardados: {guardados} | ⚠️ Incompletos: {descartados}")
            cola_datos.task_done()

        except Exception as e:
            print(f"❌ Error en el hilo de procesamiento: {e}")
        time.sleep(0.01)

# NUEVO: Función liviana para manejar mensajes
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)

        if isinstance(data, list):
            try:
                cola_datos.put_nowait(data)
                print(f"🧾 Recibido paquete con {len(data)} registros  {data}")

                # Enviar ACK después de procesar el paquete
                ack_msg = {"status": "received", "ids": [dato["indice"] for dato in data]}  # Obtiene los IDs de los registros recibidos
                client.publish("tractor/ack", json.dumps(ack_msg), qos=1)  # Publica el ACK

            except queue.Full:
                print("⚠️ Cola llena. Paquete descartado.")
        elif isinstance(data, dict):
            try:
                cola_datos.put_nowait([data])
                print(f"🧾 Recibido 1 registro individual")

                # Enviar ACK después de procesar el registro
                ack_msg = {"status": "received", "ids": [data["indice"]]}  # Obtiene el ID del registro recibido
                client.publish("tractor/ack", json.dumps(ack_msg), qos=1)  # Publica el ACK

            except queue.Full:
                print("⚠️ Cola llena. Registro descartado.")
        else:
            print("⚠️ Tipo de dato no soportado")
    except Exception as e:
        print(f"⚠️ Error en on_message: {e}")


# Función de callback para cuando el cliente MQTT se conecta
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("🔌 Conectado al broker MQTT")
        client.subscribe(MQTT_TOPIC, qos=1)
    else:
        print(f"❌ Error de conexión: {rc}")

# Configuración del cliente MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Iniciar el hilo para procesar los datos
thread = threading.Thread(target=procesar_datos, daemon=True)
thread.start()

# Conectar al broker MQTT
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()


