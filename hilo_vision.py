from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from hilo_data_jetson import cola_total
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout ,QTableWidget, QTableWidgetItem, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QSizePolicy, QStackedWidget
from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QMessageBox
from mostrar_lotes import Ventana_Lotes
from mostrar_especificaciones import Ventana_Especificaciones
from PyQt5.QtGui import QColor
import queue
import cv2


def update_labels(self, data):
        # Actualizar las etiquetas con los nuevos datos
        (id_dato, latitud, longitud, rumbo, fecha, velocidad_tractor, temperatura, humedad_relativa, velocidad_viento, angulo_viento, presion, punto_rocio, humedad_absoluta, angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual, flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2, presion_actual, bateria, estado) = data

        latitud = f"{float(latitud):.6f}"
        longitud = f"{float(longitud):.6f}"
        velocidad_tractor = f"{velocidad_tractor:.2f}"
        temperatura = f"{temperatura:.2f}"
        humedad_relativa = f"{humedad_relativa:.2f}"
        velocidad_viento = f"{velocidad_viento:.2f}"
        angulo_viento = f"{angulo_viento:.2f}"
        presion = f"{presion:.1f}"
        punto_rocio = f"{punto_rocio:.2f}"
        humedad_absoluta = f"{humedad_absoluta:.2f}"
        angulo_relativo_ajustado = f"{angulo_relativo_ajustado:.2f}"
        velocidad_aparente = f"{velocidad_aparente:.2f}"
        altura_aplicacion = f"{altura_aplicacion:.2f}"
        delta_t = f"{delta_t:.2f}"
        caudal_actual = f"{caudal_actual:.2f}"
        flujometro = f"{flujometro:.2f}"
        taponamiento = f"{taponamiento:.2f}"
        deriva = f"{deriva:.2f}"
        evaporacion = f"{evaporacion:.2f}"
        ancho = f"{ancho:.2f}"
        largo = f"{largo:.2f}"
        presion_actual = f"{presion_actual:.2f}"
        bateria = f"{bateria:.2f}"
        
        

        
        self.id_label.setText(f"ID Dato: {id_dato}")
        self.fecha_label.setText(f"{fecha}")
        

        self.presion_barra_label.setText(f"""
        <div style="text-align: center;">
                        <span style="font-size: 15px; font-weight: bold;">
                            <img src="/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/iconos/presion_atmosferica.png" 
                                width="34" height="34" 
                                style="vertical-align: middle;">
                            Presion Actual
                        </span><br>
                        <span style="font-size: 30px; font-weight: bold;">{presion_actual}</span>
                        <span style="font-size: 20px; font-weight: bold;">&nbsp;bar</span>
                    </div>
                """)

        

        self.velocidad_tractor_label.setText(f"""
        <div style="text-align: center;">
                    <span style="font-size: 15px; font-weight: bold;">
                        <img src="/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/iconos/tractor.png" 
                            width="34" height="34" 
                            style="vertical-align: middle;">
                        Velocidad
                    </span><br>
                    <span style="font-size: 30px; font-weight: bold;">{velocidad_tractor}</span>
                    <span style="font-size: 20px; font-weight: bold;">&nbsp;km/h</span>
                </div>
            """)

        

        self.humedad_relativa_label.setText(f"""
        <div style="text-align: center;">
                    <span style="font-size: 15px; font-weight: bold;">
                        <img src="/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/iconos/humedad.png" 
                            width="34" height="34" 
                            style="vertical-align: middle;">
                        Humedad
                    </span><br>
                    <span style="font-size: 30px; font-weight: bold;">{humedad_relativa}</span>
                    <span style="font-size: 20px; font-weight: bold;">&nbsp;%</span>
                </div>
            """)
        self.rumbo_label.setText(f"""
        <div style="text-align: center;">
                    <span style="font-size: 15px; font-weight: bold;">
                        <img src="/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/iconos/angulo_viento.png" 
                            width="34" height="34" 
                            style="vertical-align: middle;">
                        Rumbo
                    </span><br>
                    <span style="font-size: 30px; font-weight: bold;">{rumbo}</span>
                    <span style="font-size: 20px; font-weight: bold;">&nbsp;&deg;</span>
                </div>
            """)
        
        self.temp_label.setText(f"""
            <div style="text-align: center;">
                <span style="font-size: 15px; font-weight: bold;">
                    <img src="/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/iconos/temperatura.png" 
                        width="34" height="34" 
                        style="vertical-align: middle;">
                    Temperatura
                </span><br>
                <span style="font-size: 30px; font-weight: bold;">{temperatura}</span>
                <span style="font-size: 20px; font-weight: bold;">&nbsp;&deg;</span>
            </div>
        """)
        
        self.velocidad_aparente_label.setText(f"""
         <div style="text-align: center;">
                <span style="font-size: 15px; font-weight: bold;">
                    <img src="/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/iconos/velocidad_viento.png" 
                        width="34" height="34" 
                        style="vertical-align: middle;">
                    Viento
                </span><br>
                <span style="font-size: 30px; font-weight: bold;">{velocidad_aparente}</span>
                <span style="font-size: 20px; font-weight: bold;">&nbsp;km/h</span>
            </div>
        """)
        self.angulo_relativo_ajustado_label.setText(f"""
              <div style="text-align: center;">
                <span style="font-size: 15px; font-weight: bold;">
                    <img src="/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/iconos/angulo_viento.png" 
                        width="34" height="34" 
                        style="vertical-align: middle;">
                    Viento
                </span><br>
                <span style="font-size: 30px; font-weight: bold;">{angulo_relativo_ajustado}&nbsp;&deg;</span>
            </div>
        """)
        self.presion_label.setText(f"""
         <div style="text-align: center;">
                <span style="font-size: 15px; font-weight: bold;">
                    <img src="/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/iconos/presion_atmosferica.png" 
                        width="34" height="34" 
                        style="vertical-align: middle;">
                    P. Atmosferica
                </span><br>
                <span style="font-size: 30px; font-weight: bold;">{presion}</span>
                <span style="font-size: 18px; font-weight: bold;">&nbsp;hPa</span>
            </div>
        """)
        self.rendimiento_label.setText(f"Rendimiento:\n {presion}")

                                                                                                                                                                                                                                                                                                                                        
        self.ventana_mapa.update_map_marker(latitud, longitud)


        self.rendimiento_label.setText(f"""
            <p style="text-align: center;">
                <span style="font-size: 20px; font-weight: bold;">Calidad %</span><br>
                <span style="font-size: 70px; font-weight: bold;">{estado}</span>
            </p>
        """)

        if estado >= 80:
            rendimiento_color = "background-color: green;"     # Excelente
        elif 60 <= estado < 80:
            rendimiento_color = "background-color: yellow;"    # Aceptable
        elif 40 <= estado < 60:
            rendimiento_color = "background-color: orange;"    # Riesgoso
        else:  # estado < 40
            rendimiento_color = "background-color: red;"       # No recomendable




        # Aplicar estilo al rendimiento_label
        self.rendimiento_label.setStyleSheet(f"""
            QLabel {{
                color: #333333;
                {rendimiento_color}
                border-radius: 10px;
                padding: 10px;
                font-size: 20px;  /* Tamaño del texto superior */
                font-weight: bold; /* Negrita */
                text-align: center;
                qproperty-alignment: AlignCenter;
            }}
        """)

        # Asegurar alineación del contenido dentro del QLabel
        self.rendimiento_label.setAlignment(Qt.AlignCenter)

        self.ventana_emergente.actualizar_datos(latitud, longitud, rumbo, fecha, velocidad_tractor, temperatura, humedad_relativa, velocidad_viento, angulo_viento, presion,punto_rocio, humedad_absoluta, angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual, flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2, presion_actual, bateria, estado)
        
def update_video(self, frame):
        
        # Obtener el tamaño del widget donde se muestra el video
        widget_width = self.video_label.width()  # Ancho del widget
        widget_height = self.video_label.height()  # Alto del widget

        # Mantener la relación de aspecto del video original
        h, w, ch = frame.shape
        aspect_ratio = w / h  # Relación de aspecto del video original

        # Calcular las nuevas dimensiones basadas en el tamaño del widget
        if widget_width / widget_height > aspect_ratio:
            new_width = int(widget_height * aspect_ratio)
            new_height = widget_height
        else:
            new_width = widget_width
            new_height = int(widget_width / aspect_ratio)

        # Redimensionar el frame al nuevo tamaño calculado
        frame = cv2.resize(frame, (new_width, new_height))

        # Convertir el frame a formato QImage para mostrar en QLabel
        bytes_per_line = ch * new_width
        qimg = QImage(frame.data, new_width, new_height, bytes_per_line, QImage.Format_RGB888)

        # Actualizar el QLabel con el nuevo frame
        self.video_label.setPixmap(QPixmap.fromImage(qimg))
        

def update_value(self):
    try:
        tot = cola_total.get_nowait()  # Intentamos obtener los datos de la cola
        (id_dato, latitud, longitud, rumbo, fecha, velocidad_tractor, temperatura, humedad_relativa, velocidad_viento, angulo_viento, presion,punto_rocio, humedad_absoluta, angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual, flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2, presion_actual, bateria, estado) = tot
        # Emitimos la señal con los nuevos datos
        self.update_data_signal.emit((id_dato, latitud, longitud, rumbo, fecha, velocidad_tractor, temperatura, humedad_relativa, velocidad_viento, angulo_viento, presion,punto_rocio, humedad_absoluta, angulo_relativo_ajustado, velocidad_aparente, altura_aplicacion, delta_t, caudal_actual, flujometro, taponamiento, deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2, presion_actual, bateria, estado))

    except queue.Empty:
        # Si la cola está vacía, simplemente no hacemos nada
        pass        