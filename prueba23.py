#!/usr/bin/env python3

import numpy as np
import threading
import time
import pandas as pd
import queue
from text_utils import draw_background
from hilo_valve_left import Threads_valvula_izquierda
from hilo_valve_right import Threads_valvula_derecha
from hilo_station import task_modbus
from hilo_tcp_cliente import publicador_mqtt
from hilo_gps import task_gps
from hilo_data_jetson import server_jetson
from hilo_adc import lector_ads1115
from solve import procesador
import hilo_visioqt1  # Importa la interfaz gráfica
import sys  # Agregar esta importación
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication 


# Crear cola para enviar datos
cola_datos = queue.Queue()
stop_event = threading.Event()
evento_valvula_izquierda = threading.Event()



 
    
# Ejecutar la interfaz gráfica en el hilo principal
app = QApplication(sys.argv)

window = hilo_visioqt1.VisionApp(video_path=0)

window.show()  # Mostrar la ventana

# Ejecutar el bucle de eventos de Qt
sys.exit(app.exec_())



