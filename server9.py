                                                                          
import asyncio
import json
import mysql.connector
from mysql.connector import Error
import time
import traceback

# Configuración del servidor TCP
HOST = "0.0.0.0"
PORT = 5000
timeout_segundos = 2  # Tiempo de espera antes de cerrar la conexión

def conectar_mysql():
    while True:
        try:
            conexion = mysql.connector.connect(
                host="localhost",
                user="root",
                password="ezemaria",
                database="coordenadas_db",
                connection_timeout=10
            )
            if conexion.is_connected():
                print("Conexión a MySQL establecida.")
                return conexion
        except Error as e:
            print(f"Error al conectar a MySQL: {e}")
            time.sleep(5)

async def manejar_cliente(reader, writer):
    direccion = writer.get_extra_info('peername')
    print(f"Conexión recibida de {direccion}")

    db = conectar_mysql()
    cursor = db.cursor()

    try:
        while True:
            try:
                datos = await asyncio.wait_for(reader.read(1024), timeout=timeout_segundos)
                if not datos:
                    print(f"Cliente {direccion} cerró la conexión o no envió más datos.")
                    break

                datos = datos.decode("utf-8")
                print(f"Datos recibidos: {datos}")

                try:
                    json_datos = json.loads(datos)
                    campos = [
                        json_datos.get("id_vehiculo"),
                        json_datos.get("latitud"),
                        json_datos.get("longitud"),
                        json_datos.get("rumbo"),
                        json_datos.get("fecha"),
                        json_datos.get("velocidad"),
                        json_datos.get("temperatura"),
                        json_datos.get("humedad"),
                        json_datos.get("velocidad_viento"),
                        json_datos.get("angulo_viento"),
                        json_datos.get("presion"),
                        json_datos.get("punto_rocio"),
                        json_datos.get("humedad_absoluta"),
                        json_datos.get("angulo_relativo_ajustado"),
                        json_datos.get("velocidad_aparente"),
                        json_datos.get("presion_barra"),
                        json_datos.get("bateria"),
                        json_datos.get("estado"),
                    ]

                    if all(v is not None and v != "" for v in campos):
                        try:
                            sql = """
                            INSERT IGNORE INTO coordenadas (
                                id_vehiculo, latitud, longitud, rumbo, fecha, velocidad,
                                temperatura, humedad, velocidad_viento, angulo_viento,
                                presion, punto_rocio, humedad_absoluta, angulo_relativo_ajustado,
                                velocidad_aparente, presion_barra, bateria, estado
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(sql, campos)
                            db.commit()
                            print("Datos guardados en la base de datos.")
                            writer.write("OK".encode("utf-8"))
                        except Error as e:
                            print(f"Error ejecutando INSERT: {e}")
                            traceback.print_exc()
                            db.close()
                            db = conectar_mysql()
                            cursor = db.cursor()
                            writer.write("ERROR DB".encode("utf-8"))
                    else:
                        writer.write("ERROR: Datos incompletos".encode("utf-8"))

                    await writer.drain()

                except json.JSONDecodeError:
                    writer.write("ERROR: JSON inválido".encode("utf-8"))
                    await writer.drain()
                    break

            except asyncio.TimeoutError:
                print(f"Tiempo de espera agotado para {direccion}. Cerrando conexión.")
                break

    except Exception as e:
        print(f"Error inesperado en la conexión con {direccion}: {e}")
        traceback.print_exc()

    finally:
        writer.close()
        await writer.wait_closed()
        print(f"Conexión cerrada con {direccion}")
        if db.is_connected():
            db.close()

# Función para ejecutar el servidor TCP
async def servidor_tcp():
    servidor = await asyncio.start_server(
        manejar_cliente, HOST, PORT
    )
    print(f"Servidor TCP escuchando en {HOST}:{PORT}...")

    async with servidor:
        await servidor.serve_forever()




   # Ejecutar el servidor
asyncio.run(servidor_tcp())     

