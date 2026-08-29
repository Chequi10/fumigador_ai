from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QDialog, QVBoxLayout, QTextEdit
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import estado_global
from eventos_globales import evento_valvula_izquierda, evento_valvula_derecha
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtCore import QEvent
from teclados import mostrar_teclado_numerico_para_widget



from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDoubleSpinBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, QEvent

import estado_global
from eventos_globales import evento_valvula_izquierda, evento_valvula_derecha


class DialogoValvulasManual(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Control manual de válvulas")
        self.setModal(True)
        self.resize(420, 320)

        # Timer para sincronizar estado real
        self.timer_sync = QTimer(self)
        self.timer_sync.timeout.connect(self.sync_buttons)
        self.timer_sync.start(120)

        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2f;
                color: white;
                border: 2px solid #444;
                border-radius: 12px;
            }
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                padding: 10px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        titulo = QLabel("Modo manual: activá válvula izquierda o derecha")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setFont(QFont("Segoe UI", 11, QFont.Bold))

        self.btn_left = QPushButton("Izquierda: OFF")
        self.btn_right = QPushButton("Derecha: OFF")
        self.btn_close = QPushButton("Cerrar")

        self.btn_left.clicked.connect(self.toggle_left)
        self.btn_right.clicked.connect(self.toggle_right)
        self.btn_close.clicked.connect(self.close)

        # -----------------------------
        # Blink
        # -----------------------------
        lbl_blink = QLabel("Tiempo blink (s):")
        lbl_blink.setFont(QFont("Segoe UI", 10))

        self.spin_blink = QDoubleSpinBox()
        self.spin_blink.setRange(0.01, 2.0)
        self.spin_blink.setSingleStep(0.01)
        self.spin_blink.setDecimals(2)
        self.teclado_activo = None

        from PyQt5.QtCore import QSettings
        settings = QSettings("TeroD", "FumigadorIA")
        blink_guardado = settings.value("valvulas/blink_s", 0.10, type=float)

        self.spin_blink.setValue(float(blink_guardado))
        estado_global.blink_valvulas_s = float(blink_guardado)

        self.spin_blink.setFocusPolicy(Qt.NoFocus)
        self.spin_blink.installEventFilter(self)
        self.spin_blink.lineEdit().installEventFilter(self)
        self.spin_blink.valueChanged.connect(self.cambiar_blink)

        fila_blink = QHBoxLayout()
        fila_blink.addWidget(lbl_blink)
        fila_blink.addWidget(self.spin_blink)

        # -----------------------------
        # Coeficiente presión
        # -----------------------------
        lbl_presion_coef = QLabel("Coef. presión:")
        lbl_presion_coef.setFont(QFont("Segoe UI", 10))

        self.spin_presion_coef = QDoubleSpinBox()
        self.spin_presion_coef.setRange(0.10, 5.00)
        self.spin_presion_coef.setSingleStep(0.01)
        self.spin_presion_coef.setDecimals(2)
        self.spin_presion_coef.setValue(float(getattr(estado_global, "presion_coef", 1.00)))

        self.spin_presion_coef.setFocusPolicy(Qt.NoFocus)
        self.spin_presion_coef.installEventFilter(self)
        self.spin_presion_coef.lineEdit().installEventFilter(self)
        self.spin_presion_coef.valueChanged.connect(self.cambiar_presion_coef)

        fila_presion_coef = QHBoxLayout()
        fila_presion_coef.addWidget(lbl_presion_coef)
        fila_presion_coef.addWidget(self.spin_presion_coef)

        # Layout botones válvulas
        row = QHBoxLayout()
        row.addWidget(self.btn_left)
        row.addWidget(self.btn_right)

        bottom = QHBoxLayout()
        bottom.addWidget(self.btn_close)

        lay = QVBoxLayout()
        lay.addWidget(titulo)
        lay.addLayout(row)
        lay.addSpacing(6)
        lay.addLayout(fila_blink)
        lay.addSpacing(6)
        lay.addLayout(fila_presion_coef)
        lay.addSpacing(10)
        lay.addLayout(bottom)
        self.setLayout(lay)

        

        estado_global.modo_manual_valvulas = True
        estado_global.autopilot_habilitado = False
        self.sync_buttons()

    def eventFilter(self, obj, event):
       
        if event.type() == QEvent.MouseButtonPress:

            if obj in (self.spin_blink, self.spin_blink.lineEdit()):
                self.abrir_teclado_spin(self.spin_blink, self.aplicar_blink)
                return True

            if obj in (self.spin_presion_coef, self.spin_presion_coef.lineEdit()):
                self.abrir_teclado_spin(self.spin_presion_coef, self.aplicar_presion_coef)
                return True

        return super().eventFilter(obj, event)
    
    

    def abrir_teclado_spin(self, spinbox, on_ok):
        if self.teclado_activo is not None and self.teclado_activo.isVisible():
            return

        self.teclado_activo = mostrar_teclado_numerico_para_widget(
            spinbox,
            spinbox.lineEdit(),
            on_ok=on_ok,
            parent=self
        )

        self.teclado_activo.destroyed.connect(
            lambda: setattr(self, "teclado_activo", None)
        )

    def aplicar_blink(self):
        txt = self.spin_blink.lineEdit().text().strip().replace(",", ".")
        try:
            val = float(txt)
        except ValueError:
            return

        val = max(self.spin_blink.minimum(), min(self.spin_blink.maximum(), val))
        self.spin_blink.setValue(val)
        estado_global.blink_valvulas_s = val

    def aplicar_presion_coef(self):
        txt = self.spin_presion_coef.lineEdit().text().strip().replace(",", ".")
        try:
            val = float(txt)
        except ValueError:
            return

        val = max(self.spin_presion_coef.minimum(), min(self.spin_presion_coef.maximum(), val))
        self.spin_presion_coef.setValue(val)
        estado_global.presion_coef = val
        print("Nuevo presion_coef =", estado_global.presion_coef)

    def cambiar_blink(self, val):
        v = float(val)
        estado_global.blink_valvulas_s = v

        from PyQt5.QtCore import QSettings
        settings = QSettings("TeroD", "FumigadorIA")
        settings.setValue("valvulas/blink_s", v)

    def cambiar_presion_coef(self, val):
        estado_global.presion_coef = float(val)
        print("Nuevo presion_coef =", estado_global.presion_coef)

    def set_btn_style(self, btn, on: bool):
        if on:
            btn.setStyleSheet("background-color: green; color: white;")
        else:
            btn.setStyleSheet("background-color: #8b0000; color: white;")

    def sync_buttons(self):
        left_on = evento_valvula_izquierda.is_set()
        right_on = evento_valvula_derecha.is_set()

        self.btn_left.setText("Left: ON" if left_on else "Left: OFF")
        self.btn_right.setText("Right: ON" if right_on else "Right: OFF")

        self.set_btn_style(self.btn_left, left_on)
        self.set_btn_style(self.btn_right, right_on)
        self.btn_close.setStyleSheet("background-color: #2c2c3c; color: white;")

    def toggle_left(self):
        if evento_valvula_izquierda.is_set():
            evento_valvula_izquierda.clear()
        else:
            evento_valvula_izquierda.set()
            evento_valvula_derecha.clear()
        self.sync_buttons()

    def toggle_right(self):
        if evento_valvula_derecha.is_set():
            evento_valvula_derecha.clear()
        else:
            evento_valvula_derecha.set()
            evento_valvula_izquierda.clear()
        self.sync_buttons()

    def closeEvent(self, event):
        evento_valvula_izquierda.clear()
        evento_valvula_derecha.clear()
        estado_global.modo_manual_valvulas = False
        self.sync_buttons()
        super().closeEvent(event)



class Ventana_Especificaciones(QWidget):
    def abrir_valvulas_manual(self):
        dlg = DialogoValvulasManual(self)
        dlg.exec_()

    
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Especificaciones Técnicas")
        self.setGeometry(150, 150, 900, 600)

        # Estilo general
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2f;
                color: #ffffff;
                border: 2px solid #444;
                border-radius: 12px;
            }
            QLabel {
                font-size: 13px;
                padding: 6px;
                border-bottom: 1px solid #444;
            }
        """)

        fuente = QFont("Segoe UI", 10)
        self.layout = QGridLayout()
        self.layout.setSpacing(10)

        # Crear etiquetas principales
        self.labels = [
            ("latitud_label", "Latitud: "),
            ("longitud_label", "Longitud: "),
            ("rumbo_label", "Rumbo: "),
            ("fecha_label", "Fecha: "),
            ("velocidad_tractor_label", "Velocidad Tractor: "),
            ("temperatura_label", "Temperatura: "),
            ("humedad_relativa_label", "Humedad Relativa: "),
            ("velocidad_viento_label", "Velocidad del Viento: "),
            ("angulo_viento_label", "Ángulo del Viento: "),
            ("presion_label", "Presión: "),
            ("punto_rocio_label", "Punto de Rocio: "),
            ("humedad_absoluta_label", "Humedad Absoluta: "),
            ("angulo_relativo_ajustado_label", "Ángulo Relativo: "),
            ("velocidad_aparente_label", "Velocidad Aparente: "),
            ("altura_aplicacion_label", "Altura Aplicacion: "),
            ("delta_t_label", "Delta T: "),
            ("caudal_actual_label", "Caudal Actual: "),
            ("flujometro_label", "Flujómetro: "),
            ("taponamiento_label", "Taponamiento: "),
            ("deriva_label", "Deriva: "),
            ("evaporacion_label", "Evaporación: "),
            ("condiciones_label", "Condiciones: "),
            ("ancho_label", "Ancho: "),
            ("largo_label", "Largo: "),
            ("extra_1_label", "Tratamiento: "),
            ("extra_2_label", "Extra 2: "),
            ("presion_actual_label", "Presión Actual: "),
            ("bateria_label", "Voltaje Batería: "),
            ("estado_label", "Estado: ")
        ]

        self.label_objects = {}
        for i, (nombre_variable, texto) in enumerate(self.labels):
            label = QLabel(texto)
            label.setFont(fuente)
            label.setAlignment(Qt.AlignLeft)
            fila = i % 10
            columna = i // 10
            self.layout.addWidget(label, fila, columna)
            setattr(self, nombre_variable, label)
            self.label_objects[nombre_variable] = label

        # --- BOTÓN para recomendaciones ---
        self.recomendaciones_btn = QPushButton("View Recommendations")
        self.recomendaciones_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.recomendaciones_btn.setStyleSheet("""
            QPushButton {
                background-color: #2c2c3c;
                color: #FFA500;
                padding: 8px;
                border-radius: 6px;
                border: 1px solid #555;
            }
            QPushButton:hover {
                background-color: #3c3c4c;
            }
        """)
        self.recomendaciones_btn.clicked.connect(self.mostrar_recomendaciones)
        self.layout.addWidget(self.recomendaciones_btn, 11, 0, 1, 3, alignment=Qt.AlignCenter)

        self.setLayout(self.layout)
        self.ultimo_texto_recomendaciones = "Waiting for data..."
        self.dialogo_recomendaciones = None
        self.texto_recomendaciones = None

     # --- BOTÓN para control manual de válvulas (en el hueco) ---
        self.valvulas_btn = QPushButton("Valve && Pressure Sensor Calibration")  # <- IMPORTANTE: crear el botón
        

        self.valvulas_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.valvulas_btn.setMinimumHeight(36)   # opcional, misma altura visual

        self.valvulas_btn.setFont(QFont("Segoe UI", 10))
        self.valvulas_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e2a3a;
                color: #00FF7F;
                border: 1px solid #444;
                border-radius: 12px;
                padding: 8px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #26384f;
            }
        """)

        self.valvulas_btn.clicked.connect(self.abrir_valvulas_manual)

        self.layout.addWidget(self.valvulas_btn, 9, 2, 1, 1)




    # ============================================================
    def actualizar_datos(
        self, latitud, longitud, rumbo, fecha, velocidad_tractor, temperatura,
        humedad_relativa, velocidad_viento, angulo_viento, presion, punto_rocio,
        humedad_absoluta, angulo_relativo_ajustado, velocidad_aparente,
        altura_aplicacion, delta_t, caudal_actual, flujometro, taponamiento,
        deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2,
        presion_actual, bateria, estado
    ):
        """Actualiza los valores numéricos y genera la interpretación de scores"""
        # --- Actualizar etiquetas principales ---
        self.latitud_label.setText(f"Latitud: {latitud}")
        self.longitud_label.setText(f"Longitud: {longitud}")
        self.rumbo_label.setText(f"Rumbo: {rumbo}")
        self.fecha_label.setText(f"Fecha: {fecha}")
        self.velocidad_tractor_label.setText(f"Velocidad Tractor: {velocidad_tractor} km/h")
        self.temperatura_label.setText(f"Temperatura: {temperatura} °C")
        self.humedad_relativa_label.setText(f"Humedad Relativa: {humedad_relativa} %")
        self.velocidad_viento_label.setText(f"Velocidad del Viento: {velocidad_viento} km/h")
        self.angulo_viento_label.setText(f"Ángulo del Viento: {angulo_viento}°")
        self.presion_label.setText(f"Presión Atmosférica: {presion} hPa")
        self.punto_rocio_label.setText(f"Punto de Rocío: {punto_rocio} °C")
        self.humedad_absoluta_label.setText(f"Humedad Absoluta: {humedad_absoluta} g/m³")
        self.angulo_relativo_ajustado_label.setText(f"Ángulo Relativo: {angulo_relativo_ajustado}°")
        self.velocidad_aparente_label.setText(f"Velocidad Aparente: {velocidad_aparente} km/h")
        self.altura_aplicacion_label.setText(f"Altura de Aplicación: {altura_aplicacion} cm")
        self.delta_t_label.setText(f"Delta T: {delta_t} °C")
        self.caudal_actual_label.setText(f"Caudal Actual: {caudal_actual} L/min")
        self.flujometro_label.setText(f"Flujómetro: {flujometro} L")
        self.taponamiento_label.setText(f"Taponamiento: {taponamiento}")
        self.deriva_label.setText(f"Deriva: {deriva}")
        self.evaporacion_label.setText(f"Evaporación: {evaporacion}")
        self.condiciones_label.setText(f"Condiciones: {condiciones}")
        self.ancho_label.setText(f"Ancho: {ancho} m")
        self.largo_label.setText(f"Largo: {largo} m")
        self.extra_1_label.setText(f"Tratamiento: {getattr(estado_global, 'tratamiento', 'Desconocido')}")
        self.extra_2_label.setText(f"Extra 2: {extra_2}")
        self.presion_actual_label.setText(f"Presión Actual: {presion_actual}")
        self.bateria_label.setText(f"Voltaje Batería: {bateria} V")
        self.estado_label.setText(f"Estado: {estado}")

                # --- Mostrar datos de la boquilla y caudal ---
        boquilla = getattr(estado_global, "boquilla", "Desconocida")
        caudal_nominal = getattr(estado_global, "caudal_nominal_boquilla", 0)
        presion_trabajo = getattr(estado_global, "presion_trabajo", 0)
        caudal_esperado = getattr(estado_global, "caudal_esperado", 0)
        caudal_actual = getattr(estado_global, "caudal_actual", 0)
        presion_requerida = getattr(estado_global, "presion_requerida_para_objetivo", None)

                     # ============================================================
        # --- Interpretar todos los códigos y mostrar scores ---
        lista_codigos = []
        if isinstance(condiciones, str) and "," in condiciones:
            partes = [p.strip() for p in condiciones.split(",") if p.strip()]
        else:
            partes = [condiciones]

        for p in partes:
            try:
                p = str(p).strip()
                if len(p) >= 2:
                    # Manejo robusto de códigos (10, 11, 12)
                    if (p.startswith("10") or p.startswith("11") or p.startswith("12")) and len(p) > 5:
                        codigo = int(p[:2])
                        score_val = int(p[2:]) / 10.0
                    else:
                        codigo = int(p[0])
                        score_val = int(p[1:]) / 10.0
                    lista_codigos.append((codigo, score_val))
            except Exception:
                pass

        # ------------------------------------------------------------
        # Extraer valores actuales desde etiquetas
        def get_val(label, unidad=None):
            try:
                val = float(label.text().split(":")[-1].split()[0])
                return val
            except Exception:
                return 0.0

        temp_val = get_val(self.temperatura_label)
        hum_val = get_val(self.humedad_relativa_label)
        delta_t_val = get_val(self.delta_t_label)
        vel_aparente = get_val(self.velocidad_aparente_label)
        deriva_val = get_val(self.deriva_label)
        evap_val = get_val(self.evaporacion_label)
        presion_val = get_val(self.presion_actual_label)
        taponamiento_val = getattr(estado_global, "taponamiento_valor", 3)

        # ------------------------------------------------------------
        # Mapa dinámico de recomendaciones
        mapa_condiciones = {}

        # ΔT
        if delta_t_val < 2:
            mapa_condiciones[1] = f"ΔT bajo ({delta_t_val:.1f} °C). 👉 Riesgo de condensación o deriva hacia abajo."
        elif delta_t_val > 8:
            mapa_condiciones[1] = f"ΔT alto ({delta_t_val:.1f} °C). 👉 Riesgo de evaporación. Aplicar en horas frescas."
        else:
            mapa_condiciones[1] = f"ΔT ideal ({delta_t_val:.1f} °C). 👉 Condición térmica óptima."

        # Velocidad aparente
        if vel_aparente < 3:
            mapa_condiciones[3] = f"Velocidad baja ({vel_aparente:.1f} km/h). 👉 Posible inversión térmica."
        elif vel_aparente > 10:
            mapa_condiciones[3] = f"Velocidad alta ({vel_aparente:.1f} km/h). 👉 Riesgo de deriva, reducir velocidad."
        else:
            mapa_condiciones[3] = f"Velocidad adecuada ({vel_aparente:.1f} km/h). 👉 Correcta penetración de aspersión."

        # Deriva
        if deriva_val > 5:
            mapa_condiciones[5] = f"Deriva alta ({deriva_val:.1f} m). 👉 Usar gotas más grandes o menor presión."
        else:
            mapa_condiciones[5] = f"Deriva controlada ({deriva_val:.1f} m). 👉 Sin riesgo significativo."

        # Evaporación (ajustada con recomendaciones prácticas)
        if evap_val < 2:
            mapa_condiciones[6] = (
                f"Evaporación muy rápida ({evap_val:.1f} s). 💨 Las gotas se secan antes del impacto. "
                f"👉 Usar <b>boquillas de mayor caudal</b> o de <b>mayor tamaño de gota</b> (más micras). "
                f"También ayuda <b>bajar la presión</b> o aplicar en horas más frescas."
            )
        elif 2 <= evap_val < 3:
            mapa_condiciones[6] = (
                f"Evaporación moderada ({evap_val:.1f} s). ⚠️ Las gotas se evaporan algo rápido. "
                f"👉 Podés aumentar levemente el tamaño de gota o reducir presión."
            )
        elif 3 <= evap_val <= 5:
            mapa_condiciones[6] = (
                f"Evaporación adecuada ({evap_val:.1f} s). 👍 Balance ideal entre tamaño y persistencia. "
                f"👉 No se requiere ajuste de boquillas ni presión."
            )
        elif 5 < evap_val <= 7:
            mapa_condiciones[6] = (
                f"Evaporación algo lenta ({evap_val:.1f} s). 💧 Gotas algo grandes. "
                f"👉 Podés usar boquillas más finas o aumentar un poco la presión."
            )
        else:
            mapa_condiciones[6] = (
                f"Evaporación muy lenta ({evap_val:.1f} s). 💧 Ambiente muy húmedo o gotas excesivamente grandes. "
                f"👉 Recomendado: usar <b>boquillas más chicas</b> o aplicar a presión ligeramente superior."
            )

        # Presión / Taponamiento
                # --- Presión / Taponamiento con comparación a presión deseada ---
        presion_val = get_val(self.presion_actual_label)

        # Valor de referencia: podés configurarlo desde otra variable global o etiqueta
        presion_deseada = getattr(estado_global, "presion_trabajo", 0.2)  # bar
        tolerancia = 0.05  # margen aceptable ±0.05 bar

        if presion_val > presion_deseada + tolerancia:
            mapa_condiciones[7] = (
                f"<font color='red'>Presión alta</font> "
                f"({presion_val:.1f} bar). 👉 Por encima del valor deseado ({presion_deseada:.1f} bar). "
                f"Esto puede indicar <b>taponamiento parcial</b> en alguna boquilla."
            )
        elif presion_val < presion_deseada - tolerancia:
            mapa_condiciones[7] = (
                f"<font color='orange'>Presión baja</font> "
                f"({presion_val:.1f} bar). 👉 Por debajo del valor deseado ({presion_deseada:.1f} bar). "
                f"Posible <b>fuga</b> o boquilla obstruida parcialmente."
            )
        else:
            mapa_condiciones[7] = (
                f"<font color='lime'>Presión normal</font> "
                f"({presion_val:.1f} bar). 👉 Sistema presurizado correctamente, "
                f"<b>sin indicios de taponamiento</b> en las boquillas."
            )

        # Temperatura
        if temp_val < 5:
            mapa_condiciones[10] = f"Temperatura baja ({temp_val:.1f} °C). 👉 Riesgo de condensación."
        elif temp_val > 35:
            mapa_condiciones[10] = f"Temperatura muy alta ({temp_val:.1f} °C). 👉 Suspender aplicación."
        elif temp_val > 28:
            mapa_condiciones[10] = f"Temperatura alta ({temp_val:.1f} °C). 👉 Aplicar en horarios más frescos."
        else:
            mapa_condiciones[10] = f"Temperatura ideal ({temp_val:.1f} °C). 👉 Condición óptima."

        # Humedad relativa
        tratamiento = getattr(estado_global, "tratamiento", "").lower()
        limite = 40 if "pre" in tratamiento else 50
        if hum_val < limite:
            mapa_condiciones[11] = f"Humedad baja ({hum_val:.1f} %). 👉 Riesgo de evaporación o deriva."
        elif hum_val > 80:
            mapa_condiciones[11] = f"Humedad alta ({hum_val:.1f} %). 👉 Posible escurrimiento, reducir caudal."
        else:
            mapa_condiciones[11] = f"Humedad ideal ({hum_val:.1f} %). 👉 Buena absorción y mínima deriva."

                # ------------------------------------------------------------
        # Mostrar todas las variables con su score e interpretación
        if lista_codigos:
            mensajes = []
            for codigo, score_val in lista_codigos:
                # --- Ajuste dinámico según variable específica ---
                if codigo == 1:  # ΔT
                    if 2 <= delta_t_val <= 8:
                        color_score, estado_txt = "lime", "✅ Óptimo"
                    elif delta_t_val < 2:
                        color_score, estado_txt = "orange", "⚠️ Riesgo de condensación"
                    else:
                        color_score, estado_txt = "red", "❌ Riesgo de evaporación"
                elif codigo == 10:  # Temperatura
                    if 15 <= temp_val <= 28:
                        color_score, estado_txt = "lime", "✅ Óptimo"
                    elif 5 <= temp_val < 15 or 28 < temp_val <= 35:
                        color_score, estado_txt = "orange", "⚠️ Aceptable"
                    else:
                        color_score, estado_txt = "red", "❌ Riesgoso"
                elif codigo == 11:  # Humedad relativa
                    if 50 <= hum_val <= 80:
                        color_score, estado_txt = "lime", "✅ Óptimo"
                    elif 40 <= hum_val < 50 or 80 < hum_val <= 90:
                        color_score, estado_txt = "orange", "⚠️ Aceptable"
                    else:
                        color_score, estado_txt = "red", "❌ Riesgoso"
                elif codigo == 7:  # Presión / Taponamiento
                    if presion_val > getattr(estado_global, "presion_deseada", 0.2) + 0.05:
                        color_score, estado_txt = "red", "❌ Alta (posible taponamiento)"
                    elif presion_val < getattr(estado_global, "presion_deseada", 0.2) - 0.05:
                        color_score, estado_txt = "orange", "⚠️ Baja (posible fuga)"
                    else:
                        color_score, estado_txt = "lime", "✅ Óptima"
                else:
                    # Escala refinada de interpretación general
                    if score_val >= 85:
                        color_score, estado_txt = "lime", "✅ Óptimo"
                    elif score_val >= 70:
                        color_score, estado_txt = "#66ff99", "💚 Buena"
                    elif score_val >= 50:
                        color_score, estado_txt = "orange", "⚠️ Aceptable"
                    elif score_val >= 30:
                        color_score, estado_txt = "red", "❌ Riesgosa"
                    else:
                        color_score, estado_txt = "#ff4d4d", "☠️ Crítica"



                
                # --- Descripción de la variable ---
                descripcion = {
                    1: "ΔT (Condición térmica)",
                    3: "Velocidad aparente",
                    5: "Deriva",
                    6: "Evaporación",
                    7: "Presión / Taponamiento",
                    8: "Caudal (flujo esperado vs real)",  # ✅ nuevo código 8
                    10: "Temperatura",
                    11: "Humedad relativa"
                }.get(codigo, f"Código {codigo}")

                # --- Recomendación específica para el código 8 (Caudal) ---
                if codigo == 8:
                    caudal_actual = getattr(estado_global, "caudal_actual", 0.0)
                    caudal_esperado = getattr(estado_global, "caudal_esperado", 0.0)
                    caudal_nominal = getattr(estado_global, "caudal_nominal_boquilla", 0.0)
                    boquilla = getattr(estado_global, "boquilla", "Desconocida")
                    color_boquilla = getattr(estado_global, "color_boquilla", "")
                    presion_trabajo = getattr(estado_global, "presion_trabajo", 0.0)
                    presion_requerida = getattr(estado_global, "presion_requerida_para_objetivo", None)
                    presion_nominal = 3.0  # bar — referencia del caudal nominal
                    cantidad_picos = getattr(estado_global, "tipo_picos", 20)

                    # --- Tabla local de boquillas (a 3 bar, igual que tu base) ---
                    datos_boquillas = [
                        ["#0000FF", "XR11002", 0.76, 250],
                        ["#FF0000", "XR11003", 1.14, 300],
                        ["#00FF00", "XR110022215", 0.57, 200],
                        ["#FFFF00", "AI11004", 1.51, 400],
                        ["#EE82EE", "XR11005", 1.89, 450],
                        ["#FFA500", "AI11006", 2.27, 500],
                        ["#8B4513", "XR11001", 0.38, 150],
                        ["#808080", "AI110025", 0.95, 275],
                        ["#000000", "XR110035", 1.32, 325],
                        ["#FFFFFF", "AI110045", 1.70, 425],
                        ["#FFC0CB", "XR110055", 2.08, 475],
                        ["#ADD8E6", "AI110065", 2.46, 525],
                        ["#32CD32", "XR110075", 2.84, 575],
                        ["#8B0000", "AI110085", 3.22, 625]
                    ]

                    if caudal_esperado > 0:
                        desvio = ((caudal_actual - caudal_esperado) / caudal_esperado) * 100
                        desvio_abs = abs(desvio)

                        # ✅ Determinar color del score
                        if score_val >= 90:
                            color_score = "lime"
                            estado_txt = "✅ Óptimo"
                        elif score_val >= 70:
                            color_score = "orange"
                            estado_txt = "⚠️ Aceptable"
                        elif score_val >= 40:
                            color_score = "red"
                            estado_txt = "❌ Riesgoso"
                        else:
                            color_score = "#ff4d4d"

                            estado_txt = "❌ Crítico"

                        # --- Imagen de color de boquilla ---
                        from base64 import b64encode
                        from PIL import Image
                        import io
                        color_hex = (color_boquilla or "#999999").strip()
                        if not color_hex.startswith("#"):
                            color_hex = f"#{color_hex}"
                        img = Image.new("RGB", (30, 12), color_hex)
                        buffer = io.BytesIO()
                        img.save(buffer, format="PNG")
                        img_b64 = b64encode(buffer.getvalue()).decode()
                        color_html = f"<img src='data:image/png;base64,{img_b64}' " \
                                    f"style='margin-right:6px; vertical-align:middle;'/>"

                        # --- Mensaje base ---
                        texto_extra = (
                            f"{color_html}<b>{boquilla}</b><br>"
                            f"<font color='{color_score}'>💧 Caudal actual: {caudal_actual:.3f} L/min</font> "
                            f"(esperado {caudal_esperado:.3f} L/min, desvío {desvio:+.1f} %).<br>"
                            f"Caudal nominal de la boquilla: {caudal_nominal:.2f} L/min a {presion_nominal:.1f} bar.<br>"
                        )

                        # --- Comparar presión actual vs nominal ---
                        if presion_trabajo > presion_nominal + 0.2:
                            texto_extra += f"⚠️ Presión actual {presion_trabajo:.2f} bar (por encima del valor nominal).<br>"
                        elif presion_trabajo < presion_nominal - 0.2:
                            texto_extra += f"⚠️ Presión actual {presion_trabajo:.2f} bar (por debajo del valor nominal).<br>"
                        else:
                            texto_extra += f"✅ Presión actual dentro del rango nominal ({presion_trabajo:.2f} bar).<br>"

                        # --- Verificar si la boquilla es insuficiente físicamente ---
                        sugerencia = ""
                        if caudal_nominal and caudal_esperado > caudal_nominal * 1.1:
                            exceso_fisico = ((caudal_esperado / caudal_nominal) - 1) * 100
                            penalizacion = min(30, exceso_fisico * 0.3)
                            # Buscar boquilla sugerida
                            for color, codigo_bq, caudal_nom, micraje in datos_boquillas:
                                if caudal_nom >= caudal_esperado * 0.95:
                                    sugerencia = (
                                        f"<br>💡 <b>Sugerencia:</b> usar boquilla <b>{codigo_bq}</b> "
                                        f"(<font color='{color}'>{color}</font>) con caudal nominal "
                                        f"{caudal_nom:.2f} L/min a 3 bar."
                                    )
                                    break

                            texto_extra += (
                                f"⚠️ El caudal esperado por boquilla ({caudal_esperado:.2f} L/min) supera "
                                f"el caudal nominal ({caudal_nominal:.2f} L/min a 3 bar). "
                                f"Penalización aplicada (-{penalizacion:.1f} puntos). "
                                "Es probable que esta boquilla no alcance el objetivo con la presión actual."
                                f"{sugerencia}<br>"
                            )

                        # --- NUEVO BLOQUE: detección de boquilla grande o exceso de caudal con bajos L/ha ---
                        litros_por_hectarea = getattr(estado_global, "litros_por_hectarea", 100)
                        if litros_por_hectarea < 150 and caudal_actual > caudal_esperado * 1.1:
                            texto_extra += (
                                "<div style='margin-top:6px; padding:6px; background-color:#332b00; "
                                "border:1px solid #cc9900; border-radius:6px;'>"
                                "<font color='orange'>💡 <b>Boquilla posiblemente sobredimensionada</b>:</font> "
                                f"para bajos litros por hectárea (<b>{litros_por_hectarea:.0f} L/ha</b>), "
                                f"el caudal esperado es pequeño, pero la boquilla entrega demasiado flujo.<br>"
                                "👉 Sugerencia: usar una boquilla más chica o reducir presión para evitar sobreaplicación."
                                "</div>"
                            )

                        # --- Caudal total y diagnóstico general ---
                        caudal_total_esperado = caudal_esperado * cantidad_picos
                        caudal_total_real = caudal_actual * cantidad_picos
                        texto_extra += (
                            f"📈 Boquillas totales: {cantidad_picos} | "
                            f"Caudal total real: {caudal_total_real:.2f} L/min | "
                            f"Esperado total: {caudal_total_esperado:.2f} L/min.<br>"
                        )

                        if desvio_abs <= 5:
                            texto_extra += "👉 Sistema equilibrado."
                        elif desvio < -5:
                            texto_extra += "👉 <b>Fuga probable</b> o presión baja."
                        else:
                            texto_extra += "👉 <b>Taponamiento parcial</b> o presión alta."

                        if presion_requerida:
                            texto_extra += f"<br>💡 Presión ideal para L/ha objetivo: {presion_requerida:.2f} bar."

                    else:
                        score_val = 0
                        texto_extra = (
                            f"💧 No se pudo calcular desviación (caudal esperado no válido).<br>"
                            f"Boquilla seleccionada: {boquilla} {color_boquilla}"
                        )
                        estado_txt = "❌ Sin datos"
                        color_score = "gray"

                else:
                    texto_extra = mapa_condiciones.get(codigo, "Sin recomendación específica.")

                # --- Barra visual de progreso ---
                barra_html = (
                    f"<table width='100%' cellspacing='0' cellpadding='0' "
                    f"style='margin-top:6px; border:1px solid #555; border-radius:3px;'>"
                    f"<tr style='height:3px;'>"
                    f"<td width='{score_val:.1f}%' bgcolor='{color_score}' "
                    f"style='height:3px; font-size:1px;'>&nbsp;</td>"
                    f"<td width='{100 - score_val:.1f}%' bgcolor='#2c2c3c' "
                    f"style='height:3px; font-size:1px;'>&nbsp;</td>"
                    f"</tr></table>"
                )

                # --- Construcción del bloque HTML de cada variable ---
                mensajes.append(
                    f"""
                    <table width='100%' cellspacing='0' cellpadding='4' style='margin-bottom:13px; border-collapse:collapse;'>
                        <tr style='border-bottom:1px solid #555;'>
                            <td width='30%' valign='top' style='font-weight:bold; color:{color_score};'>
                                {descripcion}
                            </td>
                            <td width='60%' valign='top'>
                                🧭 Score: <b><font color='{color_score}'>{score_val:.1f}/100</font></b>
                                → <b>{estado_txt}</b><br>
                                <font color='#cccccc'>{texto_extra}</font>
                                {barra_html}
                            </td>
                        </tr>
                    </table>
                    """
                )

            texto_condiciones = "".join(mensajes)
            
            
        else:

            texto_condiciones = "<font color='orange'>⚠️ No se recibieron códigos válidos.</font>"

        # ------------------------------------------------------------
      # ------------------------------------------------------------
        from PyQt5.QtGui import QTextCursor

        self.ultimo_texto_recomendaciones = texto_condiciones

        if self.texto_recomendaciones:
            # Solo actualiza si hay un cambio real (para evitar flicker y salto de scroll)
            if self.texto_recomendaciones.toHtml() != self.ultimo_texto_recomendaciones:
                scrollbar = self.texto_recomendaciones.verticalScrollBar()
                valor_actual = scrollbar.value()
                maximo = scrollbar.maximum()

                cursor = self.texto_recomendaciones.textCursor()
                cursor_pos = cursor.position()

                # Actualiza el contenido sin perder posición
                self.texto_recomendaciones.blockSignals(True)
                self.texto_recomendaciones.setHtml(self.ultimo_texto_recomendaciones)
                self.texto_recomendaciones.blockSignals(False)

                # Restaurar posición del scroll
                scrollbar.setValue(valor_actual)

                # Si el usuario estaba al final, mantenerlo abajo
                if valor_actual >= maximo - 10:
                    self.texto_recomendaciones.moveCursor(QTextCursor.End)
                else:
                    cursor.setPosition(cursor_pos)
                    self.texto_recomendaciones.setTextCursor(cursor)


    # ============================================================
    def mostrar_recomendaciones(self):
        """Muestra el diálogo con todas las recomendaciones (actualizable en vivo)."""
        if self.dialogo_recomendaciones and self.dialogo_recomendaciones.isVisible():
            self.texto_recomendaciones.setHtml(self.ultimo_texto_recomendaciones)
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Recomendaciones detalladas")
        dlg.setGeometry(200, 200, 800, 600)

        dlg.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        dlg.setSizeGripEnabled(True)

        layout = QVBoxLayout()
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setFont(QFont("Segoe UI", 10))
        txt.setHtml(self.ultimo_texto_recomendaciones)
        txt.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        nota_label = QLabel(
            "📊 <b>Interpretación del Score:</b> mientras más alto el valor (cercano a 100), "
            "<font color='lime'>mejor es la condición</font>."
        )
        nota_label.setAlignment(Qt.AlignCenter)
        nota_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 12px;
                border-top: 1px solid #555;
                margin-top: 8px;
                padding-top: 6px;
            }
        """)

        layout.addWidget(txt)
        layout.addWidget(nota_label)
        dlg.setLayout(layout)

        self.dialogo_recomendaciones = dlg
        self.texto_recomendaciones = txt
        dlg.show()
