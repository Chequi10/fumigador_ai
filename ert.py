import os
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = '/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms'
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.*=false'
import queue
import sys
import cv2
import numpy as np
import warnings
import sqlite3
import cv2
import numpy as np
import pycuda.autoinit
import pycuda.driver as cuda
import tensorrt as trt
from PyQt5.QtCore import QThread, pyqtSignal
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from hilo_data_jetson import cola_total
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import QGridLayout ,QTableWidget, QTableWidgetItem, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import QSize
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QSizePolicy, QStackedWidget
from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QMessageBox
from mostrar_lotes import Ventana_Lotes
from mostrar_especificaciones import Ventana_Especificaciones
from mostrar_mapa import Ventana_mapa
from PyQt5.QtGui import QColor
from text_utils import draw_background
from hilo_valve_left import Threads_valvula_izquierda
from hilo_valve_right import Threads_valvula_derecha
from hilo_station import task_modbus
from hilo_tcp_cliente import publicador_mqtt
from hilo_tcp_cliente import lector_base
from hilo_gps import task_gps
from hilo_data_jetson import server_jetson
from hilo_adc import lector_ads1115
from solve import procesador
from seteo import modificar_parametros
from update import update_labels, update_value, update_video
import threading
import torch
from hilo_tcp_cliente import tengo_internet
from eventos_globales import evento_valvula_izquierda, evento_valvula_derecha
import estado_global

# Establecer fuente global
stop_event = threading.Event()
archivo_db = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/coordenadas_db"



class VideoThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)

    def __init__(self, video_path):
        super().__init__()
        self.estado_internet = "Verificando"
        self.video_path = video_path
        self.running = True

        # Ruta del engine generado
        self.engine_path = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/best_int8.engine"



        # Cargar modelo TensorRT
        self.load_engine()

    def set_estado_internet(self, estado):
        self.estado_internet = estado

    def load_engine(self):
        """Carga el modelo TensorRT optimizado (API moderna v10.3)"""
        try:
            import os

            if not os.path.exists(self.engine_path):
                raise FileNotFoundError(f"No se encontró el engine en: {self.engine_path}")

            self.trt_logger = trt.Logger(trt.Logger.INFO)
            runtime = trt.Runtime(self.trt_logger)

            with open(self.engine_path, "rb") as f:
                engine_data = f.read()

            self.engine = runtime.deserialize_cuda_engine(engine_data)
            if self.engine is None:
                raise RuntimeError("No se pudo deserializar el engine TensorRT")

            self.context = self.engine.create_execution_context()
            if self.context is None:
                raise RuntimeError("No se pudo crear el contexto de ejecución")

            # NUEVO: API moderna TensorRT 10.x
            bindings = [self.engine.get_tensor_name(i) for i in range(self.engine.num_io_tensors)]
            print(f"[INFO] Bindings encontrados: {bindings}")

            # Detectar nombres de entrada y salida automáticamente
            self.input_binding = [n for n in bindings if self.engine.get_tensor_mode(n) == trt.TensorIOMode.INPUT][0]
            self.output_binding = [n for n in bindings if self.engine.get_tensor_mode(n) == trt.TensorIOMode.OUTPUT][0]

            self.input_shape = self.engine.get_tensor_shape(self.input_binding)
            self.output_shape = self.engine.get_tensor_shape(self.output_binding)

            print(f"[INFO] Input tensor: {self.input_binding} -> shape {self.input_shape}")
            print(f"[INFO] Output tensor: {self.output_binding} -> shape {self.output_shape}")

            # Reservar memoria GPU
            input_size = trt.volume(self.input_shape) * np.dtype(np.float32).itemsize
            output_size = trt.volume(self.output_shape) * np.dtype(np.float32).itemsize

            self.d_input = cuda.mem_alloc(input_size)
            self.d_output = cuda.mem_alloc(output_size)

            self.bindings = [int(self.d_input), int(self.d_output)]

            print("[INFO] Engine TensorRT cargado correctamente ✅")

        except Exception as e:
            print(f"[ERROR] Falló la carga del engine TensorRT: {e}")
            self.engine = None
            self.context = None


    def preprocess(self, img):
        """Prepara el frame para la red."""
        img_resized = cv2.resize(img, (640, 640))
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_transposed = np.transpose(img_rgb, (2, 0, 1))
        img_normalized = img_transposed.astype(np.float32) / 255.0
        img_expanded = np.expand_dims(img_normalized, axis=0)
        return img_expanded.copy()

    def postprocess(self, output, img):
        """Dibuja las detecciones (demo simplificada)."""
        detections = output.reshape(-1, 7)
        num_detecciones = 0
        for det in detections:
            conf = det[2]
            if conf > 0.25:  # Umbral confianza
                num_detecciones += 1
                x1, y1, x2, y2 = map(int, det[3:7])
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        return img, num_detecciones

    def run(self):
        """Ejecuta el bucle de detección."""
        if self.engine is None or self.context is None:
            print("[ERROR] No hay engine cargado. Abortando hilo de detección.")
            return


    def stop(self):
        self.running = False
        self.wait()


class VentanaWeb(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.resize(1000, 700)

        self.web_view = QWebEngineView()
        self.web_view.load(QUrl(url))
        self.setCentralWidget(self.web_view)

class TecladoNumerico(QWidget):
    def __init__(self, line_edit, on_ok=None, parent=None):
        super().__init__(parent)
        self.line_edit = line_edit
        self.on_ok = on_ok  # Nuevo parámetro para callback
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        botones = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['0', '.', 'Borrar'],
            ['OK']
        ]

        for fila in botones:
            fila_layout = QHBoxLayout()
            for texto in fila:
                boton = QPushButton(texto)
                boton.clicked.connect(lambda _, t=texto: self.boton_presionado(t))
                fila_layout.addWidget(boton)
            layout.addLayout(fila_layout)

        self.setLayout(layout)

    def boton_presionado(self, texto):
        if texto == 'OK':
            if self.on_ok:
                self.on_ok()  # Ejecuta el callback (como si fuera el enter)
            self.close()
        elif texto == 'Borrar':
            actual = self.line_edit.text()
            self.line_edit.setText(actual[:-1])
        else:
            self.line_edit.setText(self.line_edit.text() + texto)

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit
from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit
from PyQt5.QtCore import Qt

class TecladoAlfanumerico(QWidget):
    def __init__(self, line_edit, on_ok=None, parent=None):
        super().__init__(parent)
        self.line_edit = line_edit
        self.on_ok = on_ok
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.mayusculas = False  # Empieza en mayúsculas
        self.botones = []  # Lista para guardar botones de letras
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.teclas = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', 'Borrar'],
            ['Espacio', 'OK']
        ]

        for fila in self.teclas:
            fila_layout = QHBoxLayout()
            for texto in fila:
                boton = QPushButton(texto)
                boton.setFixedHeight(40)
                if texto == 'Espacio':
                    boton.setFixedWidth(100)
                elif texto in ['OK', 'Borrar', 'Shift']:
                    boton.setFixedWidth(60)
                else:
                    boton.setFixedWidth(40)

                boton.clicked.connect(lambda _, t=texto: self.boton_presionado(t))

                if texto.isalpha():
                    self.botones.append(boton)

                fila_layout.addWidget(boton)
            layout.addLayout(fila_layout)

        self.setLayout(layout)
        self.actualizar_modo_mayusculas()


    def boton_presionado(self, texto):
        if texto == 'OK':
            if self.on_ok:
                self.on_ok()
            self.close()
        elif texto == 'Borrar':
            actual = self.line_edit.text()
            self.line_edit.setText(actual[:-1])
        elif texto == 'Espacio':
            self.line_edit.setText(self.line_edit.text() + ' ')
        elif texto == 'Shift':
            self.mayusculas = not self.mayusculas
            self.actualizar_modo_mayusculas()
        else:
            # Asegurarse de que respete el estado de mayúsculas
            caracter = texto.upper() if self.mayusculas else texto.lower()
            self.line_edit.setText(self.line_edit.text() + caracter)

    def actualizar_modo_mayusculas(self):
        for boton in self.botones:
            texto = boton.text()
            if self.mayusculas:
                boton.setText(texto.upper())
            else:
                boton.setText(texto.lower())



class VentanaVideo(QMainWindow):
    def __init__(self, video_thread):
        super().__init__()
        self.setWindowTitle("Cámara en vivo")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(760, 570)
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        alto_pantalla = pantalla.height()
        self.move(0, (alto_pantalla - self.height()) // 2)

        # Video QLabel
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(760, 570)
        self.video_label.setMaximumSize(760, 570)

        # Layout principal sin botón de cerrar
        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        layout_principal.addWidget(self.video_label)

        # Contenedor con borde redondeado
        contenedor = QWidget()
        contenedor.setLayout(layout_principal)
        contenedor.setStyleSheet("""
            QWidget {
                background-color: black;
                border: 4px solid #4CAF50;
                border-radius: 20px;
            }
        """)

        self.setCentralWidget(contenedor)

        # Conectar hilo de video
        video_thread.frame_signal.connect(self.actualizar_imagen)

    def actualizar_imagen(self, frame):
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()

        pixmap = QPixmap.fromImage(q_img)

        scaled_pixmap = pixmap.scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )

        self.video_label.setPixmap(scaled_pixmap)

    # Cerrar al hacer clic o tocar en cualquier parte
    def mousePressEvent(self, event):
        self.close()







class VisionApp(QWidget):
    update_data_signal = pyqtSignal(tuple)  # Señal para actualizar los datos

    def iniciar_hilos(self):
        print("[INFO] Iniciando hilos en segundo plano...")

        self.cola_datos = queue.Queue()
        self.stop_event = threading.Event()

        self.threads = [
            threading.Thread(target=task_modbus, daemon=True),
            threading.Thread(target=task_gps, daemon=True),
            threading.Thread(target=publicador_mqtt, daemon=True),
            threading.Thread(target=Threads_valvula_derecha, daemon=True),
            threading.Thread(target=Threads_valvula_izquierda, daemon=True),
            threading.Thread(target=lector_ads1115, args=(self.cola_datos, self.stop_event), daemon=True),
            threading.Thread(target=procesador, args=(self.cola_datos, self.stop_event), daemon=True),
            threading.Thread(target=server_jetson, daemon=True), 
            threading.Thread(target=lector_base, daemon=True)
        
            
        ]

        for i, t in enumerate(self.threads):
            t.start()
            print(f"[DEBUG] Hilo {i} iniciado.")


            
    def __init__(self, video_path):
        super().__init__()
        QTimer.singleShot(1000, self.iniciar_hilos) 
        self.estado_internet = "⏳ Verificando..."
        self.video_path = video_path
        
        # Indicador de conexión
        self.estado_internet_label = QLabel("Conexión: Sin Enlace")     

        # Ventana principal
        self.setWindowFlags(Qt.FramelessWindowHint)  # Quitá esta si querés ventana con borde
        self.showMaximized()  # O reemplazá por resize si querés ventana fija

        # Variables y etiquetas iniciales
        self.boquilla = None
        self.presion_trabajo = None
        self.micras_seleccionadas = None
        self.producto_seleccionado = None

        self.altura_label = QLabel("Altura de Aplicación:\n -")
        self.producto_label = QLabel("Producto seleccionado: Ninguno")


              
               
        font = QFont("Arial", 14)  # Usa Arial con tamaño 14
        self.estado_internet_label.setFont(font)
         # Video
        self.video_label = QLabel(self)
        # Crear la fuente


        # Widget de mapa
        #self.web_view = QWebEngineView()
        #self.web_view.setVisible(True)  # visible inicialmente o no

        # Widget alternativo: contenedor con botones u otros elementos
        self.botones_widget = QWidget()
        botones_layout = QVBoxLayout(self.botones_widget)

        # Agregás tus botones, sliders, etc.
        
        estilo_boton_web = """
            QPushButton {
                background-color: #0078D7;
                color: #333333;
                font = QFont("Arial", 14);
                border-radius: 0.5px;
                padding: 0.5px 4px;
            }
            QPushButton:hover {
                background-color: #005bb5;
            }
        """

       
       
        
      


        self.boton1 = QPushButton("www.nexelix.com.ar")
        self.boton1.clicked.connect(self.abrir_nexelix)
        self.boton1.setStyleSheet(estilo_boton_web)

        self.boton2 = QPushButton("www.windguru.cz")
        self.boton2.clicked.connect(self.abrir_windguru)
        self.boton2.setStyleSheet(estilo_boton_web)

        self.boton3 = QPushButton("Imagen real time")
        self.boton3.clicked.connect(self.mostrar_mapa)
        self.boton3.setStyleSheet(estilo_boton_web)

        self.boton4 = QPushButton("Camara")
        self.boton4.clicked.connect(self.abrir_ventana_video)
        self.boton4.setStyleSheet(estilo_boton_web)
        
       

  

        botones_layout.addWidget(self.boton1)
        botones_layout.addWidget(self.boton2)
        botones_layout.addWidget(self.boton3)
        botones_layout.addWidget(self.boton4)
        #botones_layout.addWidget(self.estado_internet_label)

        
        self.stack = QStackedWidget()
        self.stack.addWidget(self.botones_widget)  
        #self.stack.addWidget(self.web_view)        
        self.botones_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        #self.web_view.setMinimumSize(0, 300)
        #self.web_view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        
        #self.web_view = QWebEngineView()
        self.video_label.setMinimumSize(500,390)  # Elimina cualquier restricción de tamaño mínimo
        #self.video_label.setMaximumSize(1400, 1200)  # No establecer límites máximos
        self.video_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # Controles a la derecha
        self.id_label = QLabel("ID Dato: 0")
        self.fecha_label = QLabel("Fecha: 0")
        self.rumbo_label = QLabel("Rumbo: 0")
        self.velocidad_tractor_label = QLabel("Velocidad Tractor: 0")
        self.temp_label = QLabel("Temperatura: 0")
        self.humedad_relativa_label = QLabel("Humedad Relativa: 0")
        self.viento_label = QLabel("Velocidad Viento: 0")
        self.velocidad_aparente_label = QLabel("Velocidad Viento Aparente: 0")
        self.angulo_viento_label = QLabel("Ángulo Viento: 0")
        self.angulo_relativo_ajustado_label = QLabel("Ángulo Viento: 0")
        self.presion_label = QLabel("Presión: 0")
        self.rendimiento_label = QLabel("Rendimiento: 0")
        self.presion_barra_label = QLabel("Presion Barrra: 0")

        self.boquilla_label = QLabel(f"Boquilla: {self.boquilla}")
        self.presion_trabajo_label = QLabel(f"Presión T.{self.presion_trabajo}bar")
        

        
        

        
        # Aplicar la fuente a todas las etiquetas
        self.id_label.setFont(font)
        self.fecha_label.setFont(font)
        self.rumbo_label.setFont(font)
        self.velocidad_tractor_label.setFont(font)
        self.temp_label.setFont(font)
        self.humedad_relativa_label.setFont(font)
        self.viento_label.setFont(font)
        self.velocidad_aparente_label.setFont(font)
        self.angulo_viento_label.setFont(font)
        self.angulo_relativo_ajustado_label.setFont(font)
        self.presion_label.setFont(font)
        self.rendimiento_label.setFont(font)
        self.presion_barra_label.setFont(font)

        estilo_general = """
            QLabel {
                color: #333333;
                background-color: #0078D7;
                border-radius: 8px;
                padding: 5px;
                font-size: 14px;
            }
            QLabel:hover {
                background-color: #005bb5;
            }
            
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
            }
        """

        self.setStyleSheet(estilo_general)




        # Cambiar el color de cada control
        self.id_label.setStyleSheet(estilo_general)
        self.fecha_label.setStyleSheet(estilo_general)
        self.rumbo_label.setStyleSheet(estilo_general)
        self.velocidad_tractor_label.setStyleSheet(estilo_general)
        self.temp_label.setStyleSheet(estilo_general)
        self.humedad_relativa_label.setStyleSheet(estilo_general)
        self.viento_label.setStyleSheet(estilo_general)
        self.velocidad_aparente_label.setStyleSheet(estilo_general)
        self.angulo_viento_label.setStyleSheet(estilo_general)
        self.angulo_relativo_ajustado_label.setStyleSheet(estilo_general)
        self.presion_label.setStyleSheet(estilo_general)
        self.rendimiento_label.setStyleSheet(estilo_general)
        self.presion_barra_label.setStyleSheet(estilo_general)

        self.boquilla_label.setFont(font)
        self.presion_trabajo_label.setFont(font)
        self.boquilla_label.setStyleSheet(estilo_general)
        self.presion_trabajo_label.setStyleSheet(estilo_general)



        # Crear un contenedor horizontal
        self.coord_widget = QWidget()
        coord_layout = QHBoxLayout()
        coord_layout.setContentsMargins(10, 10,10, 10)  # Sin márgenes internos
        coord_layout.setSpacing(5)  # Espacio entre las etiquetas

        


        
        control_layout = QGridLayout()

        control_layout.addWidget(self.id_label, 1, 0)
        control_layout.addWidget(self.fecha_label, 0, 0)

        control_layout.addWidget(self.boquilla_label, 0, 1)
        control_layout.addWidget(self.presion_trabajo_label, 1, 2)

        
        control_layout.addWidget(self.rumbo_label, 2, 0)
        control_layout.addWidget(self.velocidad_tractor_label, 2, 1)
        control_layout.addWidget(self.velocidad_aparente_label, 2, 2)
        
        
        control_layout.addWidget(self.temp_label, 3, 0)
        control_layout.addWidget(self.humedad_relativa_label, 3, 1)
        control_layout.addWidget(self.presion_barra_label, 3, 2)
        
        control_layout.addWidget(self.angulo_relativo_ajustado_label, 4, 0)
        control_layout.addWidget(self.presion_label, 4, 1)
        control_layout.addWidget(self.rendimiento_label, 4, 2)

        self.boton_modificar = QPushButton("Boquilla-Presion.")
        self.boton_modificar.setFont(font)
        self.boton_modificar.setStyleSheet("""
            QPushButton {
                color: #333333;
                background-color: #0078D7;
                border-radius: 8px;
                padding: 5px;
                font-size: 14px;
                font-weight: bold; /* Negrita */
            }
            QPushButton:hover {
                background-color: #005bb5;  /* Azul más oscuro al pasar el mouse */
            }
        """)
        
        self.boton_modificar.clicked.connect(self.modificar_parametros)
        control_layout.addWidget(self.boton_modificar, 1, 1)  # Ubicalo en la grilla

        self.modificar_parametros()
        if not self.boquilla or not self.presion_trabajo:
            sys.exit()
        # Botón para cerrar la aplicación y apagar la PC
        self.cerrar_boton = QPushButton("Apagar \nAplicacion", self)
        self.cerrar_boton.clicked.connect(self.cerrar_app)
        self.cerrar_boton.setStyleSheet("""
            QPushButton {
                color: #333333;
                background-color: green;
                border-radius: 8px;
                padding: 5px;
                font-size: 14px;
                font-weight: bold; /* Negrita */
            }
            QPushButton:hover {
                background-color: red  /* Azul más oscuro al pasar el mouse */
            }
        """)







        
          # Botón para mostrar la ventana emergente
        self.boton_mostrar = QPushButton("Estados\n Real Time", self)
        self.boton_mostrar.clicked.connect(self.mostrar_ventana)
        self.boton_mostrar.setStyleSheet("""
            QPushButton {
                color: #333333;
                background-color: #0078D7;
                border-radius: 8px;
                padding: 5px;
                font-size: 14px;
                font-weight: bold; /* Negrita */
            }
            QPushButton:hover {
                background-color: #005bb5;  /* Azul más oscuro al pasar el mouse */
            }
        """)
        

        # Botón para mostrar lote
        self.boton_lotes = QPushButton("Especificaciones\n Tecnicas", self)
        self.boton_lotes.clicked.connect(self.mostrar_lotes)
        self.boton_lotes.setStyleSheet("""
            QPushButton {
                color: #333333;
                background-color: #0078D7;
                border-radius: 8px;
                padding: 5px;
                font-size: 14px;
                font-weight: bold; /* Negrita */
            }
            QPushButton:hover {
                background-color: #005bb5;  /* Azul más oscuro al pasar el mouse */
            }
        """)
        
        
        
               
        # Botón para ver y configurar maquinas
        self.map_button = QPushButton("Setup \nMaquina", self)
        self.map_button.clicked.connect(self.mostrar_maquinas_config)
        self.map_button.setStyleSheet("""
        QPushButton {
            color: #333333;
            background-color: #0078D7;
            border-radius: 8px;
            padding: 5px;
            font-size: 14px;
            font-weight: bold; /* Negrita */
        }
        QPushButton:hover {
            background-color: #005bb5;  /* Azul más oscuro al pasar el mouse */
        }
        """)
        
        control_layout.addWidget(self.map_button, 5, 0)  # Colocamos el botón en la fila 4, ocupando las 3 columnas

        control_layout.addWidget(self.boton_mostrar, 5, 1) 
        control_layout.addWidget(self.boton_lotes, 5, 2) 
        control_layout.addWidget(self.cerrar_boton, 0, 2) 
        
      
        
        #self.setLayout(control_layout)

        # Crear una instancia de la ventana emergente
        self.ventana_emergente = Ventana_Especificaciones()
        self.ventana_lotes = Ventana_Lotes()
        self.ventana_mapa = Ventana_mapa()
        # Cambia el tamaño mínimo y máximo si es necesario
        #self.web_view.setMinimumSize(0, 0)  # Elimina cualquier restricción de tamaño mínimo
        #self.web_view.setMaximumSize(16777215, 16777215)  # No establecer límites máximos

        # Layout principal
        main_layout = QHBoxLayout()  # Usamos QVBoxLayout para acomodar mapa y video arriba
        video_map_layout = QVBoxLayout()  # Layout horizontal para video y mapa
        
        video_map_layout.addWidget(self.video_label, alignment=Qt.AlignTop)
        
        video_map_layout.addWidget(self.stack)  # En lugar de self.web_view
        
         # Expande el mapa para ocupar el espacio restante

        main_layout.addLayout(video_map_layout)
        main_layout.addLayout(control_layout)
    


        self.setLayout(main_layout)
        #self.web_view.setVisible(True)

        
        # Hilo de video
        self.video_thread = VideoThread(self.video_path)
        self.video_thread.frame_signal.connect(lambda frame: update_video(self, frame))
        self.video_thread.start()

        # Timer para actualizar los valores automáticamente
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: update_value(self))
        self.timer.start(50)  # Actualizar cada 100 ms (0,1 segundo)

        # Timer para actualizar estado de conexión
        self.timer_internet = QTimer()
        self.timer_internet.timeout.connect(self.actualizar_estado_internet)
        self.timer_internet.start(5000)  # cada 5 segundos




        # Conectamos la señal de actualización de datos
        self.update_data_signal.connect(lambda data: update_labels(self, data))

        self.setStyleSheet("""
            QWidget {
                background-color: #333333;  /* Fondo gris oscuro */
                color: white;               /* Texto blanco */
                border: 3px solid black;    /* Borde grueso negro */
                border-radius: 5px;         /* Borde redondeado */
            }
        """)

    
    def abrir_nexelix(self):
        self.ventana_web = VentanaWeb("https://www.nexelix.com.ar")  # cambiá la URL si querés otra
        self.ventana_web.show()
   
    def abrir_windguru(self):
        self.ventana_web = VentanaWeb("https://www.windguru.cz")  # cambiá la URL si querés otra
        self.ventana_web.show()

    def abrir_ventana_video(self):
        self.ventana_video = VentanaVideo(self.video_thread)
        self.ventana_video.show()



    def actualizar_estado_internet(self):
        if tengo_internet():
            estado = "Conectado"
            self.estado_internet_label.setStyleSheet("color: green")
        else:
            estado = "Sin conexión"
            self.estado_internet_label.setStyleSheet("color: red")

        self.estado_internet_label.setText(estado)
        self.video_thread.set_estado_internet(estado)


    def mostrar_tabla_info(self):
        dialog_tabla = QDialog(self)
        dialog_tabla.setWindowTitle("Boquillas disponibles")

        layout = QVBoxLayout()

        tabla = QTableWidget()
        datos_boquillas = [
            ["#0000FF", "XR11002", "0.76", "250"],   # blue
            ["#FF0000", "XR11003", "1.14", "300"],   # red
            ["#00FF00", "XR110022215", "0.57", "200"], # green
            ["#FFFF00", "AI11004", "1.51", "400"],   # yellow
            ["#EE82EE", "XR11005", "1.89", "450"],   # violet
            ["#FFA500", "AI11006", "2.27", "500"],   # orange
            ["#8B4513", "XR11001", "0.38", "150"],   # brown
            ["#808080", "AI110025", "0.95", "275"],  # gray
            ["#000000", "XR110035", "1.32", "325"],  # black
            ["#FFFFFF", "AI110045", "1.70", "425"],  # white
            ["#FFC0CB", "XR110055", "2.08", "475"],  # pink
            ["#ADD8E6", "AI110065", "2.46", "525"],  # lightblue
            ["#32CD32", "XR110075", "2.84", "575"],  # lime
            ["#8B0000", "AI110085", "3.22", "625"]   # darkred
        ]

        tabla.setRowCount(len(datos_boquillas))
        tabla.setColumnCount(4)
        tabla.setHorizontalHeaderLabels(["Color", "Código", "Caudal (L/min)", "Micraje"])
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setSelectionMode(QTableWidget.SingleSelection)

        tabla.setMinimumWidth(600)
        tabla.setMinimumHeight(300)
        tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        for fila, datos in enumerate(datos_boquillas):
            color_nombre, codigo, caudal, micraje = datos
            item_color = QTableWidgetItem()
            item_color.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item_color.setBackground(QColor(color_nombre))
            item_color.setText("")
            tabla.setRowHeight(fila, 30)
            tabla.setItem(fila, 0, item_color)
            tabla.setItem(fila, 1, QTableWidgetItem(codigo))
            tabla.setItem(fila, 2, QTableWidgetItem(caudal))
            tabla.setItem(fila, 3, QTableWidgetItem(micraje))

        tabla.resizeColumnsToContents()
        layout.addWidget(tabla)

        btn_cerrar = QPushButton("Seleccionar y cerrar")

        def cerrar_y_guardar():
            fila_seleccionada = tabla.currentRow()
            if fila_seleccionada != -1:
                color = datos_boquillas[fila_seleccionada][0]
                codigo = tabla.item(fila_seleccionada, 1).text()
                caudal = tabla.item(fila_seleccionada, 2).text()
                micraje = tabla.item(fila_seleccionada, 3).text()

                # Guardamos la boquilla seleccionada
                self.boquilla_seleccionada = {
                    "color": color,
                    "codigo": codigo,
                    "caudal": caudal,
                    "micraje": micraje
                }

                # Solo actualizamos el texto del botón
                self.boton_modificar.setText("Modificar parámetros")
            else:
                self.boquilla_seleccionada = None

            dialog_tabla.accept()

        btn_cerrar.clicked.connect(cerrar_y_guardar)
        layout.addWidget(btn_cerrar)

        dialog_tabla.setLayout(layout)
        dialog_tabla.resize(700, 400)
        dialog_tabla.exec_()








       
    def modificar_parametros(self):

        def mostrar_teclado_numerico(line_edit):
            if line_edit == litros_input:
                teclado = TecladoNumerico(line_edit, on_ok=on_enter_litros)
            else:
                teclado = TecladoNumerico(line_edit)
            pos = line_edit.mapToGlobal(line_edit.rect().topRight())
            teclado.move(pos.x() + 10, pos.y() - 60)
            teclado.show()

        # --- Estilo general del diálogo ---
        self.setStyleSheet("""
            QWidget {
                background-color: #333333;
                color: white;
                border: 3px solid black;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout()

        # --- 1. Campo/Lote ---
        campo_combo = QComboBox()
        campo_combo.addItems(["Seleccione un campo", "Campo 1", "Campo 2", "Campo 3", "Campo 4"])
        layout.addWidget(QLabel("Seleccione el campo/lote:"))
        layout.addWidget(campo_combo)

        # --- 2. Cultivo ---
        cultivo_combo = QComboBox()
        cultivo_combo.addItems(["Seleccione un cultivo", "Temprano", "Tardío", "Primera", "Segunda"])
        cultivo_combo.setEnabled(False)
        layout.addWidget(QLabel("Seleccione el cultivo:"))
        layout.addWidget(cultivo_combo)

        # --- 3. Tratamiento ---
        tratamiento_combo = QComboBox()
        tratamiento_combo.addItems(["Seleccione un tratamiento", "Barbecho corto", "Barbecho largo", "Emergente", "Pre-Emergente"])
        tratamiento_combo.setEnabled(False)
        layout.addWidget(QLabel("Seleccione el tratamiento:"))
        layout.addWidget(tratamiento_combo)

        # dentro de modificar_parametros(), justo después de crear tratamiento_combo
        def actualizar_tratamiento():
            import estado_global
            estado_global.tratamiento = tratamiento_combo.currentText().lower()
            estado_global.tratamiento_seleccionado = tratamiento_combo.currentIndex()

        tratamiento_combo.currentIndexChanged.connect(actualizar_tratamiento)

        

        # --- 4. Litros por hectárea ---
        litros_input = QLineEdit()
        litros_input.setPlaceholderText("Litros por hectárea")
        litros_input.setEnabled(False)
        layout.addWidget(QLabel("Ingrese los litros por hectárea:"))
        layout.addWidget(litros_input)
        litros_input.mousePressEvent = lambda event: mostrar_teclado_numerico(litros_input)

        # --- 5. Presión ---
        presion_input = QLineEdit()
        presion_input.setPlaceholderText("Presión en bar")
        presion_input.setEnabled(False)
        layout.addWidget(QLabel("Ingrese la presión de trabajo:"))
        layout.addWidget(presion_input)
        presion_input.mousePressEvent = lambda event: mostrar_teclado_numerico(presion_input)

        # --- 6. Altura de aplicación ---
        altura_input = QLineEdit()
        altura_input.setPlaceholderText("Altura en mts")
        altura_input.setEnabled(False)
        layout.addWidget(QLabel("Ingrese la altura de aplicación:"))
        layout.addWidget(altura_input)
        altura_input.mousePressEvent = lambda event: mostrar_teclado_numerico(altura_input)

        # --- Reglas de habilitación ---
        campo_combo.currentIndexChanged.connect(lambda: cultivo_combo.setEnabled(campo_combo.currentIndex() != 0))
        cultivo_combo.currentIndexChanged.connect(lambda: tratamiento_combo.setEnabled(cultivo_combo.currentIndex() != 0))
        tratamiento_combo.currentIndexChanged.connect(lambda: litros_input.setEnabled(tratamiento_combo.currentIndex() != 0))

        # --- Función al presionar ENTER en litros ---
        def on_enter_litros():
            texto = litros_input.text().strip()
            if texto.replace(".", "", 1).isdigit():
                self.mostrar_tabla_info()
                if self.boquilla_seleccionada:
                    presion_input.setEnabled(True)
                    altura_input.setEnabled(True)
                    if self.producto_seleccionado:
                        producto = self.producto_seleccionado["producto"]
                        dosis = self.producto_seleccionado["dosis"]
                        self.producto_label.setText(f"Producto: {producto} - Dosis: {dosis} L/ha")
                    else:
                        self.producto_label.setText("Producto seleccionado: Ninguno")
                else:
                    QMessageBox.warning(self, "Falta selección", "Seleccioná una boquilla de la tabla antes de continuar")
            else:
                QMessageBox.warning(self, "Valor inválido", "Ingresá un número válido para los litros por hectárea")

        litros_input.returnPressed.connect(on_enter_litros)

        # --- Crear el diálogo ---
        dialog = QDialog(self)
        dialog.setWindowTitle("Modificar parámetros")
        dialog.setLayout(layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        # --- Validación y cierre ---
        def validar_y_cerrar():
            nueva_presion = presion_input.text().strip()
            litros_texto = litros_input.text().strip()
            altura_texto = altura_input.text().strip()

            if (self.boquilla_seleccionada and
                nueva_presion.replace(".", "", 1).isdigit() and
                litros_texto.replace(".", "", 1).isdigit() and
                altura_texto.replace(".", "", 1).isdigit()):

                # Guardar variables seleccionadas
                self.campo_seleccionado = campo_combo.currentText()
                self.cultivo_seleccionado = cultivo_combo.currentText()
                self.tratamiento_seleccionado = tratamiento_combo.currentText()
                self.litros_por_hectarea = float(litros_texto)
                self.boquilla = self.boquilla_seleccionada["codigo"]
                self.micras_seleccionadas = int(self.boquilla_seleccionada["micraje"])
                self.presion_trabajo = float(nueva_presion)
                self.altura_aplicacion = float(altura_texto)

                # --- Actualiza etiquetas ---
                self.boquilla_label.setText(f"Boq:{self.boquilla} - {self.micras_seleccionadas} µm")
                self.presion_trabajo_label.setText(f"Presión T. {self.presion_trabajo} bar")
                self.altura_label.setText(f"Altura de Aplicación:\n {self.altura_aplicacion} mts")

                # --- Cambiar color SOLO del label de boquilla ---
                color = self.boquilla_seleccionada["color"]

                def es_color_claro(hex_color: str) -> bool:
                    hex_color = hex_color.lstrip("#")
                    if len(hex_color) == 6:
                        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                        luminancia = 0.299*r + 0.587*g + 0.114*b
                        return luminancia > 186
                    return False

                texto_color = "black" if es_color_claro(color) else "white"

                # --- Aplicar color SOLO al QLabel ---
                self.boquilla_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {color};
                        color: {texto_color};
                        border: 2px solid #222;
                        border-radius: 6px;
                        padding: 3px;
                        font-size: 13px;
                        font-weight: bold;

                    }}
                """)

                # --- Actualizar estado global ---
                estado_global.campo_seleccionado = self.campo_seleccionado
                estado_global.cultivo_seleccionado = self.cultivo_seleccionado
                estado_global.tratamiento_seleccionado = self.tratamiento_seleccionado
                estado_global.litros_por_hectarea = self.litros_por_hectarea
                estado_global.presion_trabajo = self.presion_trabajo
                estado_global.boquilla = self.boquilla
                estado_global.micras_seleccionadas = self.micras_seleccionadas
                estado_global.altura_aplicacion = self.altura_aplicacion

                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Entrada inválida", "Verificá que todos los campos estén completos y correctos")

        buttons.accepted.connect(validar_y_cerrar)
        buttons.rejected.connect(dialog.reject)

        dialog.exec_()





            
    def mostrar_ventana(self):
        self.ventana_emergente.setWindowModality(Qt.ApplicationModal)
        self.ventana_emergente.show()
        

    def mostrar_lotes(self):
        self.ventana_lotes.setWindowModality(Qt.ApplicationModal)
        self.ventana_lotes.show()

    def mostrar_mapa(self):
        self.ventana_mapa.setWindowModality(Qt.ApplicationModal)
        self.ventana_mapa.show()    
        
    def cerrar_app(self):
        
       
        print("Cerrando aplicación...")
        for t in self.threads:
            if t.is_alive():
                print(f"Deteniendo hilo {t.name}")
                # Aquí podrías mandar una señal para que cada hilo termine limpiamente
        QApplication.quit()  # Cierra la aplicación 

    def mostrar_maquinas_config(self):
        # Aquí se inicializa la ventana para mostrar máquinas y configuraciones
        dialog = QDialog(self)
        dialog.setWindowTitle(" Máquinas y Configuración ")

        layout = QVBoxLayout()
        
        # Botón para mostrar la tabla de máquinas
        boton_tabla_maquinas = QPushButton("   Ver Máquinas Registradas   ", dialog)
        boton_tabla_maquinas.clicked.connect(self.mostrar_tabla_maquinas)
        layout.addWidget(boton_tabla_maquinas)

        # Botón para mostrar configuración de máquinas
        boton_config_maquina = QPushButton("   Configurar Nueva Máquina   ", dialog)
        boton_config_maquina.clicked.connect(self.mostrar_configuracion_maquina)
        layout.addWidget(boton_config_maquina)

        # Agregar más botones si es necesario

        dialog.setLayout(layout)
        
        dialog.exec_()
               

# Inicializa la base de datos y crea la tabla si no existe
    def inicializar_base():
        try:
            with sqlite3.connect(archivo_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS maquinas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tipo TEXT,
                        marca TEXT,
                        alto TEXT,
                        ancho TEXT,
                        largo TEXT,
                        -- fumigador
                        ancho_botalon TEXT,
                        cant_secciones TEXT,
                        sep_picos TEXT,
                        tipo_picos TEXT,
                        -- cosechadora
                        ancho_corte TEXT,
                        cant_surcos TEXT,
                        -- semabradora
                        campo1 TEXT,
                        campo2 TEXT
                    )
                """)
                conn.commit()
                
                print("Base de datos SQLite iniciada correctamente.")
        except Exception as e:
            print(f"\033[33mError al iniciar la base de datos: {e}\033[0m")
   
    

    def mostrar_tabla_maquinas(parent):
        dialog = QDialog(parent)
        dialog.setWindowTitle("Listado de máquinas registradas")
        layout = QVBoxLayout()
        tabla = QTableWidget()

        # Tamaño para que aparezca el scroll si es necesario
        tabla.setMinimumWidth(1000)
        tabla.setMinimumHeight(450)
        tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # scroll horizontal automático

        layout.addWidget(tabla)

        conn = sqlite3.connect(archivo_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM maquinas")
        registros = cursor.fetchall()
        nombres_columnas = [desc[0] for desc in cursor.description]
        conn.close()

        tabla.setColumnCount(len(nombres_columnas))
        tabla.setRowCount(len(registros))
        tabla.setHorizontalHeaderLabels(nombres_columnas)

        for fila_idx, fila in enumerate(registros):
            for col_idx, valor in enumerate(fila):
                item = QTableWidgetItem(str(valor) if valor is not None else "")
                tabla.setItem(fila_idx, col_idx, item)

        # Ajustar tamaño columnas para mostrar encabezados completos
        tabla.resizeColumnsToContents()

        # También podés permitir que algunas columnas se puedan redimensionar manualmente
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.accept)
        layout.addWidget(btn_cerrar)
        dialog.setLayout(layout)

        dialog.resize(700, 500)  # Tamaño del diálogo

        dialog.exec_()

    def mostrar_configuracion_maquina(parent):
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QLabel,
            QDialogButtonBox, QMessageBox
        )
        from PyQt5.QtGui import QDoubleValidator
        import sqlite3

        # --- Helpers ---
        def convertir_numero(valor: str):
            """
            Devuelve float si es número (acepta coma decimal), None si está vacío,
            o el mismo valor original si no es número.
            """
            if valor is None:
                return None
            s = str(valor).strip()
            if s == "":
                return None
            s = s.replace(",", ".")
            try:
                return float(s)
            except ValueError:
                return s  # texto (ej: "AB")

        def es_campo_numerico(nombre: str) -> bool:
            return nombre in {
                "Alto", "Ancho", "Largo",
                "Ancho de botalon", "Cantidad de secciones",
                "Separacion de picos", "Ancho de corte", "Cantidad de surcos"
            }

        # --- Diálogo ---
        dialog = QDialog(parent)
        dialog.setWindowTitle("Configuración de máquina")

        def mostrar_teclado_alfanumerico(line_edit):
            teclado = TecladoAlfanumerico(line_edit)
            pos = line_edit.mapToGlobal(line_edit.rect().topLeft())
            teclado.move(pos.x() + 20, pos.y() - 60)
            teclado.show()

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        combo_tipo = QComboBox()
        combo_tipo.addItems(["Sembradora", "Fumigador", "Cosechadora"])
        form_layout.addRow("Tipo de máquina", combo_tipo)

        # Campos comunes
        campos_comunes = {}
        for nombre in ["Marca", "Alto", "Ancho", "Largo"]:
            campo = QLineEdit()
            if es_campo_numerico(nombre):
                campo.setValidator(QDoubleValidator(0.0, 9999.0, 2))  # ✅ Solo números
            campo.mousePressEvent = (lambda event, c=campo: mostrar_teclado_alfanumerico(c))
            campos_comunes[nombre] = campo
            form_layout.addRow(nombre, campo)

        # Campos opcionales
        campos_fumigador = {}
        for nombre in ["Ancho de botalon", "Cantidad de secciones", "Separacion de picos", "Tipos de picos"]:
            campo = QLineEdit()
            if es_campo_numerico(nombre):
                campo.setValidator(QDoubleValidator(0.0, 9999.0, 2))
            campo.mousePressEvent = (lambda event, c=campo: mostrar_teclado_alfanumerico(c))
            campos_fumigador[nombre] = campo

        campos_cose = {}
        for nombre in ["Ancho de corte", "Cantidad de surcos"]:
            campo = QLineEdit()
            if es_campo_numerico(nombre):
                campo.setValidator(QDoubleValidator(0.0, 9999.0, 2))
            campo.mousePressEvent = (lambda event, c=campo: mostrar_teclado_alfanumerico(c))
            campos_cose[nombre] = campo

        campos_sembradora = {}
        for nombre in ["Campo 1", "Campo 2"]:
            campo = QLineEdit()
            campo.mousePressEvent = (lambda event, c=campo: mostrar_teclado_alfanumerico(c))
            campos_sembradora[nombre] = campo

        contenedor_campos_opcionales = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addLayout(contenedor_campos_opcionales)

        def limpiar_layout(layout_):
            while layout_.count():
                item = layout_.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)

        def actualizar_campos():
            limpiar_layout(contenedor_campos_opcionales)
            tipo = combo_tipo.currentText()
            if tipo == "Fumigador":
                for nombre, campo in campos_fumigador.items():
                    contenedor_campos_opcionales.addWidget(QLabel(nombre))
                    contenedor_campos_opcionales.addWidget(campo)
            elif tipo == "Cosechadora":
                for nombre, campo in campos_cose.items():
                    contenedor_campos_opcionales.addWidget(QLabel(nombre))
                    contenedor_campos_opcionales.addWidget(campo)
            elif tipo == "Sembradora":
                for nombre, campo in campos_sembradora.items():
                    contenedor_campos_opcionales.addWidget(QLabel(nombre))
                    contenedor_campos_opcionales.addWidget(campo)

        combo_tipo.currentIndexChanged.connect(actualizar_campos)
        actualizar_campos()

        # --- Persistencia en SQLite ---
        def guardar_maquina_en_sqlite(datos: dict):
            valores = {
                "tipo": datos.get("tipo"),
                "marca": datos.get("Marca"),
                "alto": convertir_numero(datos.get("Alto")),
                "ancho": convertir_numero(datos.get("Ancho")),
                "largo": convertir_numero(datos.get("Largo")),
                "ancho_botalon": convertir_numero(datos.get("Ancho de botalon")),
                "cant_secciones": convertir_numero(datos.get("Cantidad de secciones")),
                "sep_picos": convertir_numero(datos.get("Separacion de picos")),
                "tipo_picos": datos.get("Tipos de picos"),
                "ancho_corte": convertir_numero(datos.get("Ancho de corte")),
                "cant_surcos": convertir_numero(datos.get("Cantidad de surcos")),
                "campo1": datos.get("Campo 1"),
                "campo2": datos.get("Campo 2"),
            }

            try:
                conn = sqlite3.connect(archivo_db)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO maquinas (
                        tipo, marca, alto, ancho, largo,
                        ancho_botalon, cant_secciones, sep_picos, tipo_picos,
                        ancho_corte, cant_surcos, campo1, campo2
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    valores["tipo"], valores["marca"], valores["alto"], valores["ancho"], valores["largo"],
                    valores["ancho_botalon"], valores["cant_secciones"], valores["sep_picos"], valores["tipo_picos"],
                    valores["ancho_corte"], valores["cant_surcos"], valores["campo1"], valores["campo2"]
                ))
                conn.commit()
            except Exception as e:
                QMessageBox.critical(dialog, "Error al guardar", f"No se pudo guardar la máquina.\n\nDetalle: {e}")
                raise
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        # --- Guardar y cerrar ---
        def guardar_y_cerrar():
            datos = {"tipo": combo_tipo.currentText()}
            for nombre, campo in campos_comunes.items():
                datos[nombre] = campo.text()

            tipo = combo_tipo.currentText()
            if tipo == "Sembradora":
                for nombre, campo in campos_sembradora.items():
                    datos[nombre] = campo.text()
            elif tipo == "Cosechadora":
                for nombre, campo in campos_cose.items():
                    datos[nombre] = campo.text()
            elif tipo == "Fumigador":
                for nombre, campo in campos_fumigador.items():
                    datos[nombre] = campo.text()

            # ✅ Validación antes de guardar
            for nombre, valor in datos.items():
                if es_campo_numerico(nombre):
                    try:
                        float(str(valor).replace(",", "."))
                    except ValueError:
                        QMessageBox.warning(dialog, "Dato inválido",
                            f"El campo '{nombre}' debe ser un número válido.")
                        return

            # Guarda en SQLite
            try:
                guardar_maquina_en_sqlite(datos)
            except Exception:
                return

            # Actualiza estado_global
            estado_global.tipo_maquina = datos.get("tipo", "")
            estado_global.marca = datos.get("Marca", "")
            estado_global.tipo_picos = datos.get("Tipos de picos", "")
            estado_global.campo1 = datos.get("Campo 1", "")
            estado_global.campo2 = datos.get("Campo 2", "")

            estado_global.alto = convertir_numero(datos.get("Alto", ""))
            estado_global.ancho = convertir_numero(datos.get("Ancho", ""))
            estado_global.largo = convertir_numero(datos.get("Largo", ""))
            estado_global.ancho_botalon = convertir_numero(datos.get("Ancho de botalon", ""))
            estado_global.cant_secciones = convertir_numero(datos.get("Cantidad de secciones", ""))
            estado_global.sep_picos = convertir_numero(datos.get("Separacion de picos", ""))
            estado_global.ancho_corte = convertir_numero(datos.get("Ancho de corte", ""))
            estado_global.cant_surcos = convertir_numero(datos.get("Cantidad de surcos", ""))

            dialog.accept()

        botones.accepted.connect(guardar_y_cerrar)
        botones.rejected.connect(dialog.reject)
        layout.addWidget(botones)

        dialog.setLayout(layout)
        dialog.exec_()


         
    

def run_gui(video_path):
    app = QApplication(sys.argv)
    window = VisionApp(video_path)
    window.show()
    sys.exit(app.exec_())





