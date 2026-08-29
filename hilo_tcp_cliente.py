import threading
import time
import sqlite3
import json
import socket
import paho.mqtt.client as mqtt

MQTT_BROKER = "69.55.60.99"
MQTT_PORT = 1883
MQTT_TOPIC = "tractor/datos"
MQTT_CLIENT_ID = "jetson-fumigador"

archivo_db = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/coordenadas_db"
stop_event = threading.Event()
grabacion_activa = threading.Event()   # 🔴 OFF por defecto (no graba)


# Variables internas de suavizado
_fallas_consecutivas = 0
_estado_actual = True   # asumimos que arranca con internet




def recuperar_registros_pendientes():
    """Recupera registros que quedaron marcados como 'en proceso' (enviado=2)"""
    try:
        with sqlite3.connect(archivo_db) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE coordenadas SET enviado = 0 WHERE enviado = 2")
            conn.commit()
            print("✅ Registros en proceso restablecidos a pendientes")
    except Exception as e:
        print(f"❌ Error recuperando registros pendientes: {e}")


def marcar_datos_como_enviados(ids, exito=True):
    """Marca los datos como enviados (1) o los devuelve a pendientes (0)"""
    if not ids:
        return
    try:
        with sqlite3.connect(archivo_db) as conn:
            cur = conn.cursor()
            if exito:
                cur.executemany("UPDATE coordenadas SET enviado = 1 WHERE indice = ?", [(i,) for i in ids])
                print(f"✅✅✅✅✅✅✅✅✅ {len(ids)} datos marcados como enviados.")
            else:
                cur.executemany("UPDATE coordenadas SET enviado = 0 WHERE indice = ?", [(i,) for i in ids])
                print(f"✅✅✅ {len(ids)} datos devueltos a pendientes.")
            conn.commit()
    except Exception as e:
        print(f"❌ Error actualizando base: {e}")


def normalizar_set(ids):
    out = set()
    for x in ids:
        try:
            out.add(int(x))
        except Exception:
            out.add(x)
    return out


def tomar_lote_y_marcar(limite):
    """
    Toma un lote de enviados=0, los marca enviado=2, y devuelve:
    - ids (lista de indice)
    - filas (tuplas con todos los campos)
    """
    with sqlite3.connect(archivo_db) as conn:
        cur = conn.cursor()

        # 1) tomar ids pendientes
        cur.execute("""
            SELECT indice
            FROM coordenadas
            WHERE enviado = 0
            ORDER BY datetime(fecha) ASC
            LIMIT ?
        """, (limite,))
        ids = [r[0] for r in cur.fetchall()]
        if not ids:
            return [], []

        # 2) marcarlos como en proceso
        cur.executemany("UPDATE coordenadas SET enviado = 2 WHERE indice = ?", [(i,) for i in ids])
        conn.commit()

        # 3) traer SOLO esas filas
        qmarks = ",".join(["?"] * len(ids))
        cur.execute(f"""
            SELECT indice, id, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad,
                   velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta,
                   angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual,
                   flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2,
                   presion_actual, bateria, estado
            FROM coordenadas
            WHERE indice IN ({qmarks})
            ORDER BY datetime(fecha) ASC
        """, ids)

        filas = cur.fetchall()
        return ids, filas


def publicador_mqtt():
    LIMITE = 100
    MAX_BYTES = 120000
    ACK_TIMEOUT = 10
    REINTENTOS = 3
    ultimo_barrido = 0

    cliente_mqtt = mqtt.Client(client_id=MQTT_CLIENT_ID)

    # ✅ Auto-reconnect manejado por paho (no loops propios)
    cliente_mqtt.reconnect_delay_set(min_delay=1, max_delay=30)

    connected_event = threading.Event()
    ack_event = threading.Event()
    vuelo_lock = threading.Lock()
    ultimo_ids_confirmar = []

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅ Conectado a MQTT")
            connected_event.set()
            client.subscribe("tractor/ack", qos=0)
        else:
            connected_event.clear()
            print(f"❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌ Error conectando MQTT: {rc}")

    def on_disconnect(client, userdata, rc):
        connected_event.clear()
        print(f"⚠️⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️  MQTT desconectado (rc={rc})")

    def on_message(client, userdata, msg):
        nonlocal ultimo_ids_confirmar
        try:
            payload = json.loads(msg.payload.decode())
            if msg.topic == "tractor/ack":
                ids_recibidos = normalizar_set(payload.get("ids", []))
                ids_esperados = normalizar_set(ultimo_ids_confirmar)

                if ids_esperados and ids_esperados.issubset(ids_recibidos):
                    ack_event.set()
                else:
                    faltan = list(ids_esperados - ids_recibidos)[:10]
                    print(f"⚠️ ACK no coincide. Faltan (muestra): {faltan}")
        except Exception as e:
            print(f"❌ Error procesando ACK: {e}")

    cliente_mqtt.on_connect = on_connect
    cliente_mqtt.on_disconnect = on_disconnect
    cliente_mqtt.on_message = on_message

    try:
        recuperar_registros_pendientes()

        # ✅ Conexión async + loop de red siempre corriendo
        cliente_mqtt.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=120)
        cliente_mqtt.loop_start()

        while not stop_event.is_set():
            ahora = time.time()
            if ahora - ultimo_barrido > 120:
                recuperar_registros_pendientes()
                ultimo_barrido = ahora

            

            # ✅ si no está conectado, NO intentes conectar vos: paho lo hace solo
            if not connected_event.is_set():
                # (paho va a reintentar solo por reconnect_delay_set)
                time.sleep(1)
                continue

            ids_confirmados, filas = tomar_lote_y_marcar(LIMITE)

            # ✅ si no hay nada para mandar, dormí más (evita girar al pedo)
            if not filas:
                time.sleep(1.0)
                continue

            paquete = []
            for dato in filas:
                (indice, id, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad,
                 velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta,
                 angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual,
                 flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2,
                 presion_actual, bateria, estado) = dato

                paquete.append({
                    "indice": indice,
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
                    "altura_aplicacion": altura_aplicacion,
                    "delta_t": delta_t,
                    "caudal_actual": caudal_actual,
                    "flujometro": flujometro,
                    "taponamiento": taponamiento,
                    "deriva": deriva,
                    "evaporacion": evaporacion,
                    "condiciones": condiciones,
                    "ancho": ancho,
                    "largo": largo,
                    "extra_1": extra_1,
                    "extra_2": extra_2,
                    "presion_actual": presion_actual,
                    "bateria": bateria,
                    "estado": estado
                })

            mensaje_json = json.dumps(paquete)
            if len(mensaje_json) > MAX_BYTES:
                print(f"⚠️ Paquete demasiado grande ({len(mensaje_json)} bytes). Bajá LIMITE.")
                marcar_datos_como_enviados(ids_confirmados, exito=False)
                continue

            with vuelo_lock:
                reintentos = 0
                exito = False

                while reintentos < REINTENTOS and not exito and not stop_event.is_set():
                    try:
                        # si se cayó mientras tanto, dejá que paho reconecte solo
                        if not connected_event.is_set():
                            time.sleep(1)
                            continue

                        ack_event.clear()
                        ultimo_ids_confirmar = ids_confirmados.copy()

                        info = cliente_mqtt.publish(MQTT_TOPIC, mensaje_json, qos=1)
                        info.wait_for_publish(timeout=5)

                        print(f"📤 Publicado {len(ids_confirmados)} filas, esperando ACK (intento {reintentos+1})...")

                        if ack_event.wait(timeout=ACK_TIMEOUT):
                            marcar_datos_como_enviados(ids_confirmados, exito=True)
                            exito = True
                        else:
                            print("⚠️ No llegó ACK. Reintento...")
                            reintentos += 1
                            time.sleep(1)

                    except Exception as e:
                        print(f"❌ Error publicando: {e}")
                        reintentos += 1
                        time.sleep(1)

                if not exito:
                    print(f"❌ No se pudo enviar lote tras {reintentos} intentos. Devuelvo a 0.")
                    marcar_datos_como_enviados(ids_confirmados, exito=False)

            time.sleep(0.02)

    except Exception as e:
        print(f"❌ Error general MQTT: {e}")
    finally:
        try:
            cliente_mqtt.loop_stop()
            cliente_mqtt.disconnect()
        except Exception:
            pass
