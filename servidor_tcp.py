import json
import queue
import threading
import time

import mysql.connector
from mysql.connector import errors as mysql_errors
import paho.mqtt.client as mqtt

# -------------------------
# Configuración DB (MariaDB)
# -------------------------
DB_CFG = dict(
    host="localhost",
    user="root",
    password="ezemaria",
    database="coordenadas_db",
    autocommit=False,
    connection_timeout=5,
)

_db = None
_cursor = None
_db_lock = threading.Lock()


def get_db():
    """Devuelve conexión/cursor vivos. Reconecta si hace falta."""
    global _db, _cursor
    with _db_lock:
        try:
            if _db is not None and _db.is_connected():
                return _db, _cursor
        except Exception:
            pass

        # Cerrar si quedó algo a medias
        try:
            if _cursor:
                _cursor.close()
        except Exception:
            pass
        try:
            if _db:
                _db.close()
        except Exception:
            pass

        _db = mysql.connector.connect(**DB_CFG)
        _cursor = _db.cursor()
        return _db, _cursor


def force_reconnect():
    """Fuerza reconexión en próximo get_db()."""
    global _db, _cursor
    with _db_lock:
        try:
            if _cursor:
                _cursor.close()
        except Exception:
            pass
        try:
            if _db:
                _db.close()
        except Exception:
            pass
        _db = None
        _cursor = None


def exec_with_retry(sql, params, max_tries=3):
    """Ejecuta con reintentos ante 2013/2006 y reconecta."""
    last = None
    for intento in range(1, max_tries + 1):
        try:
            db, cursor = get_db()
            cursor.execute(sql, params)
            return True
        except mysql_errors.OperationalError as e:
            if getattr(e, "errno", None) in (2006, 2013):
                last = e
                force_reconnect()
                time.sleep(0.5 * intento)  # backoff corto
                continue
            raise
        except Exception as e:
            last = e
            time.sleep(0.2)
    print(f"❌ MySQL: no se pudo ejecutar tras {max_tries} intentos: {last}")
    return False


# -------------------------
# Configuración MQTT
# -------------------------
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "tractor/datos"
MQTT_ACK_TOPIC = "tractor/ack"

# Cola para almacenar los datos a procesar
cola_datos = queue.Queue(maxsize=200)

# Cliente MQTT global (para publicar ACK desde otro hilo)
mqtt_client = None

# SQL (igual que tuyo)
SQL_INSERT = """
INSERT IGNORE INTO coordenadas (
    id_vehiculo, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad,
    velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta,
    angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual,
    flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo,
    extra_1, extra_2, presion_actual, bateria, estado
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def publicar_ack(ids_ok):
    """Publica ACK SOLO si DB guardó OK."""
    global mqtt_client
    if not mqtt_client:
        return
    try:
        ack_msg = {"status": "stored", "ids": ids_ok}
        mqtt_client.publish(MQTT_ACK_TOPIC, json.dumps(ack_msg), qos=1)
    except Exception as e:
        print(f"⚠️ No pude publicar ACK: {e}")


def procesar_datos():
    while True:
        paquete = cola_datos.get()

        guardados = 0
        descartados = 0
        ids_ok = []

        try:
            # Asegura conexión viva (reconecta si hace falta)
            db, _ = get_db()

            for item in paquete:
                campos = [
                    item.get("id"), item.get("latitud"), item.get("longitud"), item.get("rumbo"), item.get("fecha"),
                    item.get("velocidad"), item.get("temperatura"), item.get("humedad"),
                    item.get("velocidad_viento"), item.get("angulo_viento"), item.get("presion"),
                    item.get("punto_rocio"), item.get("humedad_absoluta"), item.get("angulo_relativo_ajustado"),
                    item.get("velocidad_aparente"), item.get("altura_aplicacion"), item.get("delta_t"),
                    item.get("caudal_actual"), item.get("flujometro"), item.get("taponamiento"), item.get("deriva"),
                    item.get("evaporacion"), item.get("condiciones"), item.get("ancho"), item.get("largo"),
                    item.get("extra_1"), item.get("extra_2"), item.get("presion_actual"),
                    item.get("bateria"), item.get("estado")
                ]

                if not all(v is not None and v != "" for v in campos):
                    descartados += 1
                    continue

                ok = exec_with_retry(SQL_INSERT, campos, max_tries=3)
                if ok:
                    guardados += 1
                    if "indice" in item:
                        ids_ok.append(item["indice"])

            # Commit una sola vez por lote
            try:
                db, _ = get_db()
                db.commit()
            except mysql_errors.OperationalError as e:
                if getattr(e, "errno", None) in (2006, 2013):
                    print(f"❌ Commit falló (MySQL {e.errno}). No mando ACK. Se reintentará desde el cliente.")
                    # rollback y no ACK
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    ids_ok = []
                else:
                    raise

            print(f"✅ Guardados: {guardados} | ⚠️ Incompletos: {descartados}")

        except Exception as e:
            # rollback por seguridad
            try:
                db, _ = get_db()
                db.rollback()
            except Exception:
                pass
            print(f"❌ Error en el hilo de procesamiento: {e}")
            ids_ok = []

        finally:
            # ACK real (solo si DB guardó OK)
            if ids_ok:
                publicar_ack(ids_ok)

            cola_datos.task_done()
            time.sleep(0.01)


def on_message(client, userdata, msg):
    """Solo encola. NO manda ACK acá."""
    try:
        data = json.loads(msg.payload.decode("utf-8"))

        if isinstance(data, list):
            cola_datos.put_nowait(data)
            print(f"🧾 Recibido paquete con {len(data)} registros")
        elif isinstance(data, dict):
            cola_datos.put_nowait([data])
            print("🧾 Recibido 1 registro individual")
        else:
            print("⚠️ Tipo de dato no soportado")

    except queue.Full:
        print("⚠️ Cola llena. Paquete descartado.")
    except Exception as e:
        print(f"⚠️ Error en on_message: {e}")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("🔌 Conectado al broker MQTT")
        client.subscribe(MQTT_TOPIC, qos=1)
    else:
        print(f"❌ Error de conexión MQTT: {rc}")


def main():
    global mqtt_client

    # Iniciar hilo de DB
    thread = threading.Thread(target=procesar_datos, daemon=True)
    thread.start()

    # MQTT
    client = mqtt.Client()
    mqtt_client = client
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
