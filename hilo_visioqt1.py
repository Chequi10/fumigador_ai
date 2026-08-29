import os
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = '/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms'
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.*=false'

import os, psutil
import queue
import sys
import cv2
import numpy as np
import warnings
import sqlite3
import pycuda.autoinit
import pycuda.driver as cuda
import tensorrt as trt

from PyQt5.QtCore import QThread, pyqtSignal

warnings.filterwarnings("ignore", category=FutureWarning)
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from hilo_data_jetson import cola_total
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QGridLayout ,QTableWidget, QTableWidgetItem, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import QSize
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QSizePolicy, QStackedWidget
from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QMessageBox
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit
from mostrar_lotes import Ventana_Lotes
from mostrar_especificaciones import Ventana_Especificaciones
from mostrar_mapa import Ventana_mapa
from PyQt5.QtGui import QColor
from text_utils import draw_background
from hilo_valve_left import Threads_valvula_izquierda
from hilo_valve_right import Threads_valvula_derecha
from hilo_station import task_modbus
from hilo_tcp_cliente import publicador_mqtt
#from hilo_tcp_cliente import lector_base
from hilo_gps import task_gps
from hilo_data_jetson import server_jetson, grabacion_activa

from hilo_adc import lector_ads1115
from solve import procesador
from seteo import modificar_parametros
from update import update_labels, update_value, update_video
import threading
from teclados import TecladoNumerico, TecladoAlfanumerico, mostrar_teclado_numerico_para_widget
#import torch

from eventos_globales import evento_valvula_izquierda, evento_valvula_derecha
import estado_global

# Establecer fuente global
stop_event = threading.Event()
archivo_db = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/coordenadas_db"


class VideoThread(QThread):
    frame_ready = pyqtSignal()


    def __init__(self, video_path):
        super().__init__()
        self.estado_internet = "Verificando"
        self._lock = threading.Lock()
        self._last_frame = None
        self.video_path = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/eduardo1.mp4"
        self.running = True

        self.engine_path = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/best_int8.engine"

        self.engine = None
        self.context = None
        self._frame_count = 0
            
        


        # OJO: NO cargues engine acá si vas a usar CUDA en QThread.
        # Se carga dentro de run() después de crear el contexto CUDA.

    def set_estado_internet(self, estado):
        self.estado_internet = estado

    def get_last_frame(self):
        with self._lock:
            if self._last_frame is None:
                return None
            return self._last_frame.copy()
        
    
    
    

    @staticmethod
    def is_camera_available(index):
        cap = cv2.VideoCapture(index)
        ok = cap.isOpened()
        cap.release()
        return ok
    
    

    def load_engine(self):
        """Carga el engine TensorRT y reserva buffers GPU (requiere contexto CUDA activo en este hilo)."""
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

        # IO names (TensorRT 10.x)
        io_names = [self.engine.get_tensor_name(i) for i in range(self.engine.num_io_tensors)]
        print(f"[INFO] IO tensors encontrados: {io_names}")

        self.input_binding = [n for n in io_names if self.engine.get_tensor_mode(n) == trt.TensorIOMode.INPUT][0]
        self.output_binding = [n for n in io_names if self.engine.get_tensor_mode(n) == trt.TensorIOMode.OUTPUT][0]

        self.input_shape = tuple(self.engine.get_tensor_shape(self.input_binding))
        self.output_shape = tuple(self.engine.get_tensor_shape(self.output_binding))

        # Si hay shape dinámico, fijamos 1x3x640x640
        if any(d < 0 for d in self.input_shape):
            fixed = (1, 3, 640, 640)
            self.context.set_input_shape(self.input_binding, fixed)
            self.input_shape = fixed
            self.output_shape = tuple(self.context.get_tensor_shape(self.output_binding))

        print(f"[INFO] Input tensor: {self.input_binding} -> shape {self.input_shape}")
        print(f"[INFO] Output tensor: {self.output_binding} -> shape {self.output_shape}")

        # Reservar memoria GPU (float32)
        input_size = trt.volume(self.input_shape) * np.dtype(np.float32).itemsize
        output_size = trt.volume(self.output_shape) * np.dtype(np.float32).itemsize

        self.d_input = cuda.mem_alloc(input_size)
        self.d_output = cuda.mem_alloc(output_size)

        # Para execute_v2 (si falla, pasamos a execute_async_v3 luego)
        self.bindings = [int(self.d_input), int(self.d_output)]

        print("[INFO] Engine TensorRT cargado correctamente ✅")

    def infer_simple(self, inp):
        """
        Inferencia mínima con execute_v2.
        inp: np.float32 (1,3,640,640)
        """
        h_input = np.ascontiguousarray(inp, dtype=np.float32)
        h_output = np.empty(self.output_shape, dtype=np.float32)

        cuda.memcpy_htod(self.d_input, h_input)

        ok = self.context.execute_v2(self.bindings)
        if not ok:
            raise RuntimeError("execute_v2 devolvió False")

        cuda.memcpy_dtoh(h_output, self.d_output)
        return h_output

    def preprocess(self, img):
        """
        img DEBE ser 640x640 BGR
        devuelve (1,3,640,640) float32
        """
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_chw = np.transpose(img_rgb, (2, 0, 1)).astype(np.float32) / 255.0
        return np.expand_dims(img_chw, axis=0)



    def postprocess(self, output, img_orig,
                    conf_th=0.25,
                    max_draw=25,
                    cultivo_id=1,
                    min_w=8,
                    min_h=12,
                    roi_y_min_ratio=0.35,
                    x_center=None,
                    band_px=None):

        preds = output[0]  # (25200, 7)

        x1 = preds[:, 0]
        y1 = preds[:, 1]
        w_box = preds[:, 2]
        h_box = preds[:, 3]
        x2 = x1 + w_box
        y2 = y1 + h_box

        def sigmoid(x):
            return 1.0 / (1.0 + np.exp(-x))

        obj = sigmoid(preds[:, 4])
        cls_scores = sigmoid(preds[:, 5:7])
        cls_id = np.argmax(cls_scores, axis=1)
        cls_score = np.max(cls_scores, axis=1)

        conf = obj * cls_score

        keep = (conf >= conf_th) & (cls_id == cultivo_id)
        idx = np.where(keep)[0]
        if idx.size == 0:
            return img_orig, 0, []

        idx = idx[np.argsort(conf[idx])[::-1]][:max_draw * 3]

        H, W = img_orig.shape[:2]
        sx = W / 640.0
        sy = H / 640.0
        roi_y_min = int(H * roi_y_min_ratio)

        n = 0
        pts = []

        for i in idx:
            a = int(max(0, min(W - 1, x1[i] * sx)))
            b = int(max(0, min(H - 1, y1[i] * sy)))
            c = int(max(0, min(W - 1, x2[i] * sx)))
            d = int(max(0, min(H - 1, y2[i] * sy)))

            if c <= a or d <= b:
                continue

            bw = c - a
            bh = d - b

            if bw < min_w or bh < min_h:
                continue

            if d < roi_y_min:
                continue

            cx = 0.5 * (a + c)
            cy = 0.5 * (b + d)

            # ✅ filtro de banda (también aplica a pts y a dibujo)
            if x_center is not None and band_px is not None:
                if abs(cx - x_center) > band_px:
                    continue

            pts.append((cx, cy))

            cv2.rectangle(img_orig, (a, b), (c, d), (0, 255, 0), 2)
            cv2.putText(img_orig, f"{conf[i]:.2f}", (a, max(0, b - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            n += 1
            if n >= max_draw:
                break

        return img_orig, n, pts









    def run(self):

        # ---------- helpers ----------
       
        def split_two_rows(pts):
            xs = np.array([p[0] for p in pts], dtype=np.float32)
            med = float(np.median(xs))
            left = [p for p in pts if p[0] <= med]
            right = [p for p in pts if p[0] > med]
            return left, right

        def fit_line_x_of_y(pts):
            ys = np.array([p[1] for p in pts], dtype=np.float32)
            xs = np.array([p[0] for p in pts], dtype=np.float32)
            m, b = np.polyfit(ys, xs, 1)
            return float(m), float(b)

        def draw_line(img, m, b, y1, y2, color, thick=2):
            H, W = img.shape[:2]
            x1 = int(m * y1 + b)
            x2 = int(m * y2 + b)
            x1 = max(0, min(W - 1, x1))
            x2 = max(0, min(W - 1, x2))
            cv2.line(img, (x1, int(y1)), (x2, int(y2)), color, thick)

        # ---------- parámetros ----------
        deadband_px = 45
        band_px = 250
        min_pts_total = 10
        min_pts_row = 4
        hold_frames = 5

        # ---------- estado ----------
        self._cmd = "NONE"
        self._hold = 0
        self._xmid_f = None     # punto rojo filtrado
        self._row_w = None      # ancho esperado entre hileras

        print(f"[INFO] Abriendo fuente: {self.video_path}")

        cuda.init()
        self.cuda_ctx = cuda.Device(0).make_context()

        try:
            if self.engine is None or self.context is None:
                self.load_engine()

            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                print("[ERROR] No se pudo abrir el video")
                return

            while self.running:
                ret, frame_raw = cap.read()
                if not ret:
                    break

                frame_640 = cv2.resize(frame_raw, (640, 640))
                inp = self.preprocess(frame_640)
                output = self.infer_simple(inp)

                H0, W0 = frame_raw.shape[:2]
                x_center0 = W0 * 0.5

                frame_out, n, pts = self.postprocess(
                    output, frame_raw,
                    x_center=x_center0,
                    band_px=band_px
)


                H, W = frame_out.shape[:2]
                x_center = W * 0.5
                y_ref = int(H * 0.75)

                # líneas de referencia
                cv2.line(frame_out, (int(x_center), 0), (int(x_center), H), (0, 255, 0), 5)
                cv2.line(frame_out, (int(x_center - band_px), 0), (int(x_center - band_px), H), (255, 0, 255), 4)
                cv2.line(frame_out, (int(x_center + band_px), 0), (int(x_center + band_px), H), (255, 0, 255), 4)

                cmd = "NONE"

                if len(pts) >= min_pts_total:
                    pts_near = [p for p in pts if abs(p[0] - x_center) <= band_px]
                    use_pts = pts_near if len(pts_near) >= min_pts_total else pts

                    left, right = split_two_rows(use_pts)

                    if len(left) >= min_pts_row and len(right) >= min_pts_row:
                        mL, bL = fit_line_x_of_y(left)
                        mR, bR = fit_line_x_of_y(right)

                        y_top = int(H * 0.35)
                        y_bot = int(H * 0.95)

                       # draw_line(frame_out, mL, bL, y_top, y_bot, (0, 255, 255))
                       # draw_line(frame_out, mR, bR, y_top, y_bot, (0, 255, 255))

                        xL = mL * y_ref + bL
                        xR = mR * y_ref + bR
                        x_mid = 0.5 * (xL + xR)

                        # ---------- control de ancho ----------
                        row_w = xR - xL
                        if row_w > 0:
                            if self._row_w is None:
                                self._row_w = row_w
                            else:
                                self._row_w = 0.9 * self._row_w + 0.1 * row_w

                            if self._row_w is not None:
                                if row_w < 0.6 * self._row_w or row_w > 1.6 * self._row_w:
                                    x_mid = self._xmid_f if self._xmid_f is not None else x_center

                        # ---------- filtro EMA ----------
                        alpha = 0.2
                        if self._xmid_f is None:
                            self._xmid_f = x_mid
                        else:
                            self._xmid_f = (1 - alpha) * self._xmid_f + alpha * x_mid

                        x_mid_use = self._xmid_f
                        error = x_mid_use - x_center

                                                # decidir cmd primero
                        # decidir cmd primero
                        if error > deadband_px:
                            cmd = "RIGHT"
                        elif error < -deadband_px:
                            cmd = "LEFT"
                        else:
                            cmd = "NONE"

                        px = int(x_mid_use)
                        py = int(y_ref)

                        arrow_len = 90
                        arrow_th = 8
                        tip_len = 0.85

                        # -------- COLOR SEGÚN CMD --------
                        if cmd == "NONE":
                            color = (0, 255, 0)   # VERDE = bien centrado
                        else:
                            color = (0, 0, 255)   # ROJO = corrigiendo izquierda o derecha

                        # -------- DIRECCIÓN --------
                        if cmd == "RIGHT":
                            end = (px + arrow_len, py)
                        elif cmd == "LEFT":
                            end = (px - arrow_len, py)
                        else:
                            end = (px, py - arrow_len)

                        cv2.arrowedLine(frame_out, (px, py), end, color, arrow_th, tipLength=tip_len)


                # ---------- hold ----------
                if cmd != self._cmd:
                    self._cmd = cmd
                    self._hold = hold_frames
                else:
                    self._hold = max(0, self._hold - 1)

               

                # ------------------ VÁLVULAS: MANUAL vs AUTOPILOT ------------------
                if getattr(estado_global, "modo_manual_valvulas", False):
                    # En modo manual NO tocamos los eventos.
                    # Los eventos los maneja el diálogo manual (o tus hilos de válvulas).
                    pass
                else:
                    if not getattr(estado_global, "autopilot_habilitado", True):
                        evento_valvula_derecha.clear()
                        evento_valvula_izquierda.clear()
                    else:
                        if self._hold > 0:
                            if self._cmd == "RIGHT":
                                evento_valvula_derecha.set()
                                evento_valvula_izquierda.clear()
                            elif self._cmd == "LEFT":
                                evento_valvula_izquierda.set()
                                evento_valvula_derecha.clear()
                            else:
                                evento_valvula_derecha.clear()
                                evento_valvula_izquierda.clear()
                        else:
                            evento_valvula_derecha.clear()
                            evento_valvula_izquierda.clear()


                cv2.putText(frame_out, f"CMD: {self._cmd}  det:{n}", (10, 30),
                            cv2.FONT_HERSHEY_DUPLEX, 1, (255, 0, 255), 2)

                with self._lock:
                    self._last_frame = frame_out

                self.frame_ready.emit()

            cap.release()

        finally:
            try:
                self.cuda_ctx.pop()
                self.cuda_ctx.detach()
            except Exception:
                pass




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
        self.video_thread = video_thread
        self.video_thread.frame_ready.connect(self.on_frame_ready)

    def on_frame_ready(self):
        frame = self.video_thread.get_last_frame()
        if frame is None:
            return
        self.actualizar_imagen(frame)


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
            threading.Thread(target=publicador_mqtt, daemon=True),   # ← usa la versión nueva sin cola
            threading.Thread(target=Threads_valvula_derecha, daemon=True),
            threading.Thread(target=Threads_valvula_izquierda, daemon=True),
            threading.Thread(target=lector_ads1115, args=(self.cola_datos, self.stop_event), daemon=True),
            threading.Thread(target=procesador, args=(self.cola_datos, self.stop_event), daemon=True),
            threading.Thread(target=server_jetson, daemon=True),
            # threading.Thread(target=lector_base, daemon=True)  # ← ELIMINAR
        ]

        for i, t in enumerate(self.threads):
            t.start()
            print(f"[DEBUG] Hilo {i} iniciado.")

    def apagar_sistema(self):
        self.cerrar_app()
        

    def confirmar_system_off(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmación")
        msg.setText("¿Seguro que querés apagar el sistema?")

        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        # Tamaño grande (touch)
        msg.setMinimumWidth(520)
        msg.setFont(QFont("Arial", 14))

        msg.setStyleSheet("""
            QMessageBox { background-color: #2b2b2b; }
            QLabel { font-size: 15px; min-width: 480px; color: white; }
            QPushButton { min-width: 160px; min-height: 55px; font-size: 16px; font-weight: bold; }
        """)

        if msg.exec_() == QMessageBox.Yes:
            self.apagar_sistema()







    def toggle_grabar(self):
        on = self.btn_grabar.isChecked()

        accion = "ACTIVAR" if on else "DETENER"
        reply = QMessageBox.question(
            self,
            "Confirmación",
            f"¿Seguro que querés {accion} el Data Logging?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            # vuelve el botón al estado anterior
            self.btn_grabar.blockSignals(True)
            self.btn_grabar.setChecked(not on)
            self.btn_grabar.blockSignals(False)
            return

        if on:
            grabacion_activa.set()
            self.btn_grabar.setText("Data Logging: ON")
            self.btn_grabar.setStyleSheet("""
                QPushButton {
                    background-color: green;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: #00AA00;
                }
            """)
            print("🟢 Grabación ACTIVADA (DB)")
        else:
            grabacion_activa.clear()
            self.btn_grabar.setText("Data Logging: OFF")
            self.btn_grabar.setStyleSheet("""
                QPushButton {
                    background-color: #7f8c8d;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: #707b7c;
                }
            """)
            print("🔴 Grabación DESACTIVADA (DB)")


    def toggle_autopilot(self):
        habilitado = self.boton2.isChecked()

        # SOLO pedir confirmación al ACTIVAR
        if habilitado:
            reply = QMessageBox.question(
                self,
                "Confirmación",
                "¿Seguro que querés ACTIVAR el Auto Pilot?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                # vuelve el botón al estado anterior
                self.boton2.blockSignals(True)
                self.boton2.setChecked(False)
                self.boton2.blockSignals(False)
                return

        # Permiso general: autopilot y válvulas
        estado_global.autopilot_habilitado = habilitado
        estado_global.valvulas_habilitadas = habilitado

        if habilitado:
            self.boton2.setText("Auto Pilot: ON")
            self.boton2.setStyleSheet("""
                QPushButton { background-color: green; color: white; font-size: 20px; font-weight: bold; }
                QPushButton:hover { background-color: #00AA00; }
            """)
        else:
            # APAGADO DIRECTO (sin preguntar)
            evento_valvula_izquierda.clear()
            evento_valvula_derecha.clear()

            self.boton2.setText("Auto Pilot: OFF")
            self.boton2.setStyleSheet("""
                QPushButton { background-color: red; color: white; font-size: 20px; font-weight: bold; }
                QPushButton:hover { background-color: #CC0000; }
            """)



            
    def __init__(self, video_path):
        super().__init__()
        QTimer.singleShot(1000, self.iniciar_hilos)

        self.video_path = video_path

        # Ventana principal
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showMaximized()

        # Variables y etiquetas iniciales
        self.boquilla = None
        self.presion_trabajo = None
        self.micras_seleccionadas = None
        self.producto_seleccionado = None

        self.altura_label = QLabel("Altura de Aplicación:\n -")
        self.producto_label = QLabel("Producto seleccionado: Ninguno")

        font = QFont("Arial", 20)

        # Video
        self.video_label = QLabel(self)

        # Widget alternativo: contenedor con botones u otros elementos
        self.botones_widget = QWidget()

        # ✅ Grilla 2x2 (dos filas, dos columnas)
        botones_layout = QGridLayout(self.botones_widget)
        botones_layout.setContentsMargins(6, 6, 6, 6)
        botones_layout.setHorizontalSpacing(8)
        botones_layout.setVerticalSpacing(8)

        estilo_boton = """
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                font-size: 20px;
                font-weight: bold;
                border-radius: 6px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #707b7c;
            }
        """

        self.boton2 = QPushButton("Auto Pilot: OFF")
        self.boton2.setCheckable(True)
        self.boton2.setChecked(False)

        # -------- BOTÓN GRABAR (DB) ----------
        self.btn_grabar = QPushButton("Data Logging: OFF")
        self.btn_grabar.setCheckable(True)
        self.btn_grabar.setChecked(False)

        # ❌ ya no uses setFixedHeight(30) porque los querés cuadrados
        # self.boton2.setFixedHeight(30)
        # self.btn_grabar.setFixedHeight(30)

        self.btn_grabar.setStyleSheet(estilo_boton)
        self.btn_grabar.clicked.connect(self.toggle_grabar)

        # --- ESTILO ROJO INICIAL ---
        self.boton2.setStyleSheet("""
            QPushButton {
                background-color: red;
                color: white;
                font-size: 20px;
                font-weight: bold;
                border-radius: 6px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        self.boton2.clicked.connect(self.toggle_autopilot)

        self.boton3 = QPushButton("Real-Time Image")
        self.boton3.clicked.connect(self.mostrar_mapa)
        self.boton3.setStyleSheet(estilo_boton)

        self.boton4 = QPushButton("Camera")
        self.boton4.clicked.connect(self.abrir_ventana_video)
        self.boton4.setStyleSheet(estilo_boton)

        # ✅ Tamaño cuadrado para los 4 botones
        BTN_W = 240
        BTN_H = 70
        for b in (self.boton2, self.btn_grabar, self.boton3, self.boton4):
            b.setMinimumSize(BTN_W, BTN_H)
            b.setMaximumSize(BTN_W, BTN_H)
            b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # ✅ Ubicación en grilla 2x2
        botones_layout.addWidget(self.boton2,     0, 0)  # Auto pilot
        botones_layout.addWidget(self.btn_grabar, 0, 1)  # Data Logging
        botones_layout.addWidget(self.boton3,     1, 0)  # Real-Time Image
        botones_layout.addWidget(self.boton4,     1, 1)  # Camera

        self.stack = QStackedWidget()
        self.stack.addWidget(self.botones_widget)
        self.botones_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self.video_label.setMinimumSize(500, 390)
        self.video_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)


        # Controles a la derecha
           
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
       
        
        self.id_label = QLabel("Machine ID: 0")
        self.fecha_label = QLabel("Fecha: 0")
        self.presion_trabajo_label = QLabel(f"Set. Pressure .{self.presion_trabajo}bar")

        self.id_label.setObjectName("infoTop")
        self.fecha_label.setObjectName("infoTop")
        self.presion_trabajo_label.setObjectName("infoTop")


              

        
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
            /* Fondo general */
            QWidget {
                background-color: #333333;
            }

            /* Estilo base para TODOS tus QLabel azules */
            QLabel {
                background-color: #0078D7;
                color: #FFFFFF;           /* blanco por defecto */
                border-radius: 8px;
                padding: 5px;
                font-size: 14px;
            }

            /* Hover opcional */
            QLabel:hover {
                background-color: #005bb5;
            }

            /* SOLO para Fecha e ID (los querés como botones: letra gris/oscura) */
            QLabel#infoTop {
                color: #333333;           /* gris/oscuro */
                font-weight: bold;
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

        self.boton_modificar = QPushButton("Edit Parameters")
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
        # Botón para cerrar la aplicación
        self.cerrar_boton = QPushButton("System Off", self)
        self.cerrar_boton.clicked.connect(self.confirmar_system_off)
        self.cerrar_boton.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: green;
                border-radius: 8px;
                padding: 5px;
                font-size: 18px;
                font-weight: bold; /* Negrita */
            }
            QPushButton:hover {
                background-color: red  /* Azul más oscuro al pasar el mouse */
            }
        """)







        
          # Botón para mostrar la ventana emergente
        self.boton_mostrar = QPushButton("Real-Time\n Status", self)
        self.boton_mostrar.clicked.connect(self.mostrar_ventana)
        self.boton_mostrar.setStyleSheet("""
            QPushButton {
                color: #333333;
                background-color: #0078D7;
                border-radius: 8px;
                padding: 5px;
                font-size: 18px;
                font-weight: bold; /* Negrita */
            }
            QPushButton:hover {
                background-color: #005bb5;  /* Azul más oscuro al pasar el mouse */
            }
        """)
        

        # Botón para mostrar lote
        self.boton_lotes = QPushButton("Technical\n Specifications", self)
        self.boton_lotes.clicked.connect(self.mostrar_lotes)
        self.boton_lotes.setStyleSheet("""
            QPushButton {
                color: #333333;
                background-color: #0078D7;
                border-radius: 8px;
                padding: 5px;
                font-size: 18px;
                font-weight: bold; /* Negrita */
            }
            QPushButton:hover {
                background-color: #005bb5;  /* Azul más oscuro al pasar el mouse */
            }
        """)
        
        
        
               
        # Botón para ver y configurar maquinas
        self.map_button = QPushButton("Equipment\n Setup", self)
        self.map_button.clicked.connect(self.mostrar_maquinas_config)
        self.map_button.setStyleSheet("""
        QPushButton {
            color: #333333;
            background-color: #0078D7;
            border-radius: 8px;
            padding: 5px;
            font-size: 18px;
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

        panel_der = QWidget()
        panel_der.setLayout(control_layout)
        panel_der.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)  # o Preferred
        panel_der.setMinimumWidth(520)  # ajustá a gusto (ej 480/520/560)
        panel_der.setContentsMargins(0, 0, 14, 0)   # ← margen derecho visible


        main_layout.addLayout(video_map_layout)
        main_layout.addWidget(panel_der)

        main_layout.setContentsMargins(10, 10, 10, 10)



        self.setLayout(main_layout)
        #self.web_view.setVisible(True)

        
        # Hilo de video
        self.video_thread = VideoThread(self.video_path)
        self.video_thread.frame_ready.connect(self.on_frame_ready)

        self.video_thread.start()

        # Timer para actualizar los valores automáticamente
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: update_value(self))
        self.timer.start(50)  # Actualizar cada 100 ms (0,1 segundo)

      

        self.timer_debug = QTimer(self)
        self.timer_debug.timeout.connect(self.debug_mem)
        self.timer_debug.start(5000)



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
   

    
    #def abrir_terod(self):
     #   self.ventana_web = VentanaWeb("https://www.terod.ai")  # cambiá la URL si querés otra
     #   self.ventana_web.show()
   
    def abrir_windguru(self):
        self.ventana_web = VentanaWeb("https://www.windguru.cz")  # cambiá la URL si querés otra
        self.ventana_web.show()

    def abrir_ventana_video(self):
        self.ventana_video = VentanaVideo(self.video_thread)
        self.ventana_video.show()

    def debug_mem(self):
        try:
            qsize = self.cola_datos.qsize()
        except Exception:
            qsize = -1
           
        p = psutil.Process(os.getpid())
        rss_mb = p.memory_info().rss / 1024 / 1024
        print(f"[DEBUG] cola={qsize}  RSS={rss_mb:.1f} MB")

    

    def on_frame_ready(self):
        frame = self.video_thread.get_last_frame()
        if frame is None:
            return
        update_video(self, frame)

    def mostrar_tabla_info(self):
        dialog_tabla = QDialog(self)
        dialog_tabla.setWindowTitle("Boquillas disponibles")

        layout = QVBoxLayout()
        # ✅ Título grande dentro del diálogo
        titulo = QLabel("Boquillas disponibles")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setFont(QFont("Arial", 17, QFont.Bold))
        titulo.setStyleSheet("""
            QLabel {
                color: white;
                padding: 6px;
                border-bottom: 2px solid #444;
            }
        """)

        layout.addWidget(titulo)


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

        tabla.setFont(QFont("Arial", 18))   # tamaño del texto de celdas

        tabla.setRowCount(len(datos_boquillas))
        tabla.setColumnCount(4)
        tabla.setHorizontalHeaderLabels(["Color", "Código", "Caudal (L/min)", "Micraje"])
        tabla.horizontalHeader().setFont(QFont("Arial", 15, QFont.Bold))
        tabla.horizontalHeader().setMinimumHeight(45)

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
            tabla.setRowHeight(fila, 40)
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

                # Guardamos la boquilla seleccionada localmente
                self.boquilla_seleccionada = {
                    "color": color,
                    "codigo": codigo,
                    "caudal": caudal,
                    "micraje": micraje
                }

                import estado_global

                # --- Guardar en estado_global para uso global en todo el sistema ---
                estado_global.boquilla = codigo

                try:
                    estado_global.micras_seleccionadas = float(micraje)
                except ValueError:
                    estado_global.micras_seleccionadas = 0.0

                try:
                    estado_global.caudal_nominal_boquilla = float(caudal)
                except ValueError:
                    estado_global.caudal_nominal_boquilla = 0.0

                estado_global.color_boquilla = color

                # Mensaje de confirmación en consola
                print(f"[INFO] Boquilla seleccionada: {codigo}, "
                    f"{estado_global.micras_seleccionadas} µm, "
                    f"{estado_global.caudal_nominal_boquilla} L/min, "
                    f"color {color}")

                # Actualizar texto del botón
                self.boton_modificar.setText("Edit Parameters")
            else:
                self.boquilla_seleccionada = None

            # Cierra el diálogo correctamente
            dialog_tabla.accept()


        # --- Botón para cerrar y guardar selección ---
        btn_cerrar = QPushButton("Seleccionar y cerrar")

        # ✅ tamaño grande
        btn_cerrar.setMinimumHeight(70)
        btn_cerrar.setMinimumWidth(300)
        btn_cerrar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # ✅ fuente más grande
        btn_cerrar.setFont(QFont("Arial", 16, QFont.Bold))

        # ✅ estilo más visible
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border-radius: 10px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005bb5;
            }
            QPushButton:pressed {
                background-color: #003f7f;
            }
        """)

        btn_cerrar.clicked.connect(cerrar_y_guardar)
        layout.addWidget(btn_cerrar)


        # --- Configuración del diálogo ---
        dialog_tabla.setLayout(layout)
        dialog_tabla.resize(600, 600)
        dialog_tabla.exec_()









       
    def modificar_parametros(self):

        def mostrar_teclado_numerico(line_edit):
            if line_edit == litros_input:
                return mostrar_teclado_numerico_para_widget(
                    line_edit,
                    line_edit,
                    on_ok=on_enter_litros,
                    parent=self
                )
            else:
                return mostrar_teclado_numerico_para_widget(
                    line_edit,
                    line_edit,
                    on_ok=None,
                    parent=self
                )

            # 1) Forzamos a que calcule su tamaño real
            teclado.adjustSize()

            # 2) Si querés forzar tamaño fijo (opcional, pero consistente)
            # teclado.resize(320, 420)

            # 3) Posición ideal: arriba del campo
            pos = line_edit.mapToGlobal(line_edit.rect().topLeft())
            screen = QGuiApplication.screenAt(pos)
            if screen is None:
                screen = QGuiApplication.primaryScreen()
            geo = screen.availableGeometry()

            x = pos.x()
            y = pos.y() - teclado.height() - 12  # arriba

            # 4) Si no entra arriba, lo ponemos abajo del campo
            if y < geo.top():
                y = pos.y() + line_edit.height() + 12

            # 5) Si tampoco entra abajo, lo centramos verticalmente cerca del campo
            if y + teclado.height() > geo.bottom():
                y = max(geo.top(), min(geo.bottom() - teclado.height(), pos.y() - teclado.height() // 2))

            # 6) Ajuste horizontal para que no se vaya a los costados
            if x + teclado.width() > geo.right():
                x = geo.right() - teclado.width() - 12
            if x < geo.left():
                x = geo.left() + 12

            teclado.move(x, y)

            # 7) Mostrar y traer al frente (clave para poder tocar OK)
            teclado.show()
            teclado.raise_()
            teclado.activateWindow()



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

        label_titulo_style = """
            QLabel {
                color: #FFFFFF;                 /* blanco puro */
                font-size: 14px;                /* tamaño uniforme */
                font-weight: 500;               /* semi-bold elegante */
                padding: 2px 2px 4px 2px;       /* espacio interno */
                margin-top: 4px;                /* separación vertical */
                border: none;                   /* sin borde duro */
                background: transparent;        /* sin fondo (oscuro limpio) */
                letter-spacing: 0.3px;          /* mejor legibilidad */
            }

            QLabel:disabled {
                color: #888888;                 /* gris cuando no está activo */
            }

            QLabel[role="titulo"] {
                font-size: 8px;
                font-weight: bold;
            }

            QLabel[role="seccion"] {
                color: #cccccc;
                margin-top: 8px;
                border-top: 1px solid #444;
                padding-top: 6px;
            }
            """


         
        # --- 1. Campo/Lote ---
        campo_combo = QComboBox()
        campo_combo.addItems(["Seleccione un lote", "Lote 1", "Lote 2", "Lote 3", "Lote 4"])
      
        layout.addWidget(campo_combo)

        # --- 2. Cultivo ---
        cultivo_combo = QComboBox()
        cultivo_combo.addItems(["Seleccione un cultivo", "Temprano", "Tardío", "Primera", "Segunda"])
        cultivo_combo.setEnabled(False)

        layout.addWidget(cultivo_combo)

        # --- 3. Tratamiento ---
        tratamiento_combo = QComboBox()
        tratamiento_combo.addItems(["Seleccione un tratamiento", "Barbecho corto", "Barbecho largo", "Emergente", "Pre-Emergente"])
        tratamiento_combo.setEnabled(False)

        layout.addWidget(tratamiento_combo)


        combo_style = """
        QComboBox {
            background-color: #2b2b2b;
            color: #00FF7F;
            font-size: 22px;
            height: 45px;
            padding-left: 10px;
            border: 1px solid #555;
            border-radius: 8px;
        }
        QComboBox::drop-down { width: 5px; border-left: 5px solid #555; }

        QComboBox QAbstractItemView {
            background-color: #1e1e1e;
            color: #00FF7F;
            font-size: 13px;
        }
        QComboBox QAbstractItemView::item {
            height: 34px;
            padding: 4px 10px;
        }
        """





        campo_combo.setStyleSheet(combo_style)
        cultivo_combo.setStyleSheet(combo_style)
        tratamiento_combo.setStyleSheet(combo_style)

        edit_verde_style = """
        QLineEdit {
            background-color: #1e1e1e;
            color: #00FF7F;
            font-size: 22px;
            height: 45px;
            padding: 5px 10px;
            border: 1px solid #555;
            border-radius: 8px;
        }
        QLineEdit:disabled {
            color: #777777;
            background-color: #2b2b2b;
        }
        """

        



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
    
        layout.addWidget(litros_input)
        litros_input.mousePressEvent = lambda event: mostrar_teclado_numerico(litros_input)

        # --- 5. Presión ---
        presion_input = QLineEdit()
        presion_input.setPlaceholderText("Presión en bar")
        presion_input.setEnabled(False)
     
        layout.addWidget(presion_input)
        presion_input.mousePressEvent = lambda event: mostrar_teclado_numerico(presion_input)

        # --- 6. Altura de aplicación ---
        altura_input = QLineEdit()
        altura_input.setPlaceholderText("Altura en mts")
        altura_input.setEnabled(False)
    
        layout.addWidget(altura_input)
        altura_input.mousePressEvent = lambda event: mostrar_teclado_numerico(altura_input)

        # --- Reglas de habilitación ---
        campo_combo.currentIndexChanged.connect(lambda: cultivo_combo.setEnabled(campo_combo.currentIndex() != 0))
        cultivo_combo.currentIndexChanged.connect(lambda: tratamiento_combo.setEnabled(cultivo_combo.currentIndex() != 0))
        tratamiento_combo.currentIndexChanged.connect(lambda: litros_input.setEnabled(tratamiento_combo.currentIndex() != 0))

        litros_input.setStyleSheet(edit_verde_style)
        presion_input.setStyleSheet(edit_verde_style)
        altura_input.setStyleSheet(edit_verde_style)



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

        # --- Aplicar estilo a títulos (labels) ---
        for w in dialog.findChildren(QLabel):
            w.setStyleSheet(label_titulo_style)


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
                self.boquilla_label.setText(f"Bq.:{self.boquilla} - {self.micras_seleccionadas} µm")
                self.presion_trabajo_label.setText(f"Set. Pressure {self.presion_trabajo} bar")
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



        def confirmar_cancelar():
            msg = QMessageBox(dialog)
            msg.setWindowTitle("Confirmación")
            msg.setText("¿Seguro que querés salir sin guardar?")

            msg.setIcon(QMessageBox.Question)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)

            # Tamaño grande (como venimos usando)
            msg.setMinimumWidth(420)
            msg.setFont(QFont("Arial", 13))

            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                }
                QLabel {
                    font-size: 14px;
                }
                QPushButton {
                    min-width: 120px;
                    min-height: 45px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)

            if msg.exec_() == QMessageBox.Yes:
                dialog.reject()




        # --- Botones OK / Cancel grandes ---
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        btn_ok = buttons.button(QDialogButtonBox.Ok)
        btn_cancel = buttons.button(QDialogButtonBox.Cancel)

        btn_ok.setText("Apply")
        btn_cancel.setText("Back")


        # Tamaño y fuente
        for b in (btn_ok, btn_cancel):
            b.setMinimumHeight(70)
            b.setMinimumWidth(180)
            b.setFont(QFont("Arial", 16, QFont.Bold))

        # Estilo (OK azul, Cancel gris)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border-radius: 10px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #005bb5; }
            QPushButton:pressed { background-color: #003f7f; }
        """)

        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border-radius: 10px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #444444; }
            QPushButton:pressed { background-color: #333333; }
        """)

        # ✅ Conexión directa (no depende de accepted/rejected)
        btn_ok.clicked.connect(validar_y_cerrar)
        btn_cancel.clicked.connect(confirmar_cancelar)



        layout.addWidget(buttons)
        

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
            estado_global.tipos_picos = convertir_numero(datos.get("Cantidad de picos", ""))
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





