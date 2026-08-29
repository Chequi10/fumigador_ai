import sqlite3
import threading
import os
import time
import queue
from hilo_tcp_cliente1 import obtener_datos_pendientes
from hilo_gps import cola_gps 
from hilo_station import cola_modbus
from solve import all_data


archivo_db = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/coordenadas_db"
semaforo = threading.Semaphore(1)
lock = threading.Lock()

stop_event = threading.Event()
grabacion_activa = threading.Event()   # 🔴 OFF por defecto (no graba)

start_time = time.time()  # Reiniciar el temporizador
bloqueado_time = time.time() - start_time  # Mide el tiempo que estuvo bloqueado
cola_total = queue.Queue()


def server_jetson():
    while not stop_event.is_set():
        contador_ping = 0
        """Crea la base de datos SQLite si no existe, define la tabla y guarda los datos de la cola."""
        # Crear la base de datos y la tabla si no existe
        try:
            with sqlite3.connect(archivo_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS coordenadas (
                        id NUMERIC,
                        latitud REAL,
                        longitud REAL,
                        rumbo REAL,
                        fecha TEXT,
                        velocidad REAL,
                        temperatura REAL,
                        humedad REAL,
                        velocidad_viento REAL,
                        angulo_viento REAL,
                        presion REAL,
                        punto_rocio REAL,
                        humedad_absoluta REAL,
                        angulo_relativo_ajustado REAL,
                        velocidad_aparente REAL,
                        estado REAL,
                        altura_aplicacion REAL,
                        delta_t REAL,
                        caudal_actual REAL,
                        flujometro REAL,
                        taponamiento REAL,
                        deriva REAL,
                        evaporacion REAL,
                        condiciones TEXT,
                        ancho REAL,
                        largo REAL,
                        extra_1 REAL,
                        extra_2 REAL,
                        presion_actual REAL,       
                        estado REAL,
                        bateria REAL,
                        enviado NUMERIC DEFAULT 0
                    )
                ''')
                conn.commit()
                print("Base de datos SQLite iniciada correctamente.")
        except Exception as e:
            print(f"\033[33mError al iniciar la base de datos: {e}\033[0m")
    
        global tot

        while True:
            try:
                datos_modbus = cola_modbus.get_nowait() 
                datos_gps = cola_gps.get_nowait() 
                datos_combinados = datos_gps + datos_modbus  # Combina ambas tuplas o listas
                total=all_data(datos_combinados)
                cola_total.put(total)
                            
                if len(total) == 30:  # Ejemplo, asegúrate de que las longitudes coincidan con lo que esperas
                  
                    print(f"\033[94m Datos pasaron: {total}\033[0m")
                    guardar_datos_en_db([total])  # Recuerda pasar los datos como lista de tuplas
                else:
                    print("\033[31mDatos incompletos o mal formateados.\033[0m")

            except queue.Empty:
                # Si no hay datos en la cola, simplemente esperar
                pass
            except Exception as e:
                print(f"\033[31mError en iniciar_base_datos: {e}\033[0m")

            contador_ping += 1
            if contador_ping >= 250:  # 250 * 20 ms = 5 s
                verificar_estado_db()
                contador_ping = 0
                

            time.sleep(0.020)
        pass

def guardar_datos_en_db(total):
    """Guarda los datos en la base de datos SQLite."""
    #grabacion_activa.set()
    #grabacion_activa.clear() 


    if not grabacion_activa.is_set():
            # GRABAR está OFF: no guardo nada
            return


    try:
        with lock:
            with sqlite3.connect(archivo_db) as conn:
                conn.execute('PRAGMA journal_mode=WAL;')
                cursor = conn.cursor()
                # Crear índice si no existe
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fecha ON coordenadas(fecha);")
                


                cursor.executemany('''
                    INSERT OR IGNORE INTO coordenadas 
                    (id, latitud, longitud, rumbo, fecha, velocidad, temperatura, humedad, velocidad_viento,
                     angulo_viento, presion, punto_rocio, humedad_absoluta, angulo_relativo_ajustado, 
                     velocidad_aparente, altura_aplicacion, delta_t, caudal_actual, flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2, presion_actual, bateria, estado, enviado)
                    VALUES (?, ROUND(?, 7), ROUND(?, 7), ?, ?, ?, ?, ?, ?, ?, ?,  ROUND(?, 2),ROUND(?, 2), ?,ROUND(?, 3), ?, ?,?,?,?,?,?,?,?,?,?,?,? , ?, ?, 0)
                ''', total)

                conn.commit()
                print(f"\033[33mDatos guardados: {len(total)} filas.\033[0m")
                
                cursor.execute("SELECT COUNT(*) FROM coordenadas")
                total_filas = cursor.fetchone()[0]
                print(f"\033[33mTotal de filas: {total_filas} filas.\033[0m")
                if total_filas > 200000:
                    filas_a_borrar = total_filas - 200000
                    cursor.execute('''
                        DELETE FROM coordenadas 
                        WHERE ROWID IN (
                            SELECT ROWID FROM coordenadas 
                            ORDER BY fecha ASC 
                            LIMIT ?
                        )
                    ''', (filas_a_borrar,))
                    conn.commit()
                    print(f"\033[33mSe eliminaron {filas_a_borrar} filas antiguas para mantener solo 200000.\033[0m")

    
    except Exception as e:
        print(f"\033[31m❌Error al guardar en DB: {e}\033[0m")




def verificar_estado_db():
    """Verifica si la base de datos está accesible."""
    try:
        with sqlite3.connect(archivo_db, timeout=2) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            resultado = cursor.fetchone()
            if resultado and resultado[0] == 1:
                print("\033[32mPing a la base de datos exitoso.✅\033[0m")
                return True
    except Exception as e:
        print(f"\033[31mBase de datos no responde: {e}\033[0m")
    return False   