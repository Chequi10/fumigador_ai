from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class Ventana_Especificaciones(QWidget):
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
                font-size: 14px;
                padding: 6px;
                border-bottom: 1px solid #444;
            }
        """)

        fuente = QFont("Segoe UI", 11)

        self.layout = QGridLayout()
        self.layout.setSpacing(10)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 1)
        self.layout.setColumnStretch(2, 1)

        # Crear etiquetas
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
            ("condiciones_label", "Condiciones: "),  # ⚠️ Esta queda igual, muestra número
            ("ancho_label", "Ancho: "),
            ("largo_label", "Largo: "),
            ("extra_1_label", "Extra 1: "),
            ("extra_2_label", "Extra 2: "),
            ("presion_actual_label", "Presion Actual: "),
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

        # --- NUEVO BLOQUE: Recomendaciones dinámicas (debajo de todo) ---
        self.recomendaciones_label = QLabel("Recomendaciones:\nEsperando datos...")
        self.recomendaciones_label.setFont(QFont("Segoe UI", 11))
        self.recomendaciones_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.recomendaciones_label.setStyleSheet("""
            QLabel {
                background-color: #2c2c3c;
                border: 1px solid #444;
                padding: 8px;
                border-radius: 6px;
                font-size: 12px;
                color: #e0e0e0;
            }
        """)
        self.layout.addWidget(self.recomendaciones_label, 11, 0, 1, 3)

        self.setLayout(self.layout)

    def actualizar_datos(
        self, latitud, longitud, rumbo, fecha, velocidad_tractor, temperatura,
        humedad_relativa, velocidad_viento, angulo_viento, presion, punto_rocio,
        humedad_absoluta, angulo_relativo_ajustado, velocidad_aparente,
        altura_aplicacion, delta_t, caudal_actual, flujometro, taponamiento,
        deriva, evaporacion, condiciones, ancho, largo, extra_1, extra_2,
        presion_actual, bateria, estado
    ):
        # --- Actualizar etiquetas numéricas ---
        self.latitud_label.setText(f"Latitud: {latitud}")
        self.longitud_label.setText(f"Longitud: {longitud}")
        self.rumbo_label.setText(f"Rumbo: {rumbo}")
        self.fecha_label.setText(f"Fecha: {fecha}")
        self.velocidad_tractor_label.setText(f"Velocidad Tractor: {velocidad_tractor} km/h")
        self.temperatura_label.setText(f"Temperatura: {temperatura} °C")
        self.humedad_relativa_label.setText(f"Humedad Relativa: {humedad_relativa} %")
        self.velocidad_viento_label.setText(f"Velocidad del Viento: {velocidad_viento} km/h")
        self.angulo_viento_label.setText(f"Ángulo del Viento: {angulo_viento}°")
        self.presion_label.setText(f"Presión Atmosferica: {presion} hPa")
        self.punto_rocio_label.setText(f"Punto de Rocío: {punto_rocio} °C")
        self.humedad_absoluta_label.setText(f"Humedad Absoluta: {humedad_absoluta} %")
        self.angulo_relativo_ajustado_label.setText(f"Ángulo Relativo: {angulo_relativo_ajustado}°")
        self.velocidad_aparente_label.setText(f"Velocidad Aparente: {velocidad_aparente} km/h")
        self.altura_aplicacion_label.setText(f"Altura de Aplicacion: {altura_aplicacion} cm")
        self.delta_t_label.setText(f"Delta T: {delta_t} °C")
        self.caudal_actual_label.setText(f"Caudal Actual: {caudal_actual} L/min")
        self.flujometro_label.setText(f"Flujómetro: {flujometro} L")
        self.taponamiento_label.setText(f"Taponamiento: {taponamiento}")
        self.deriva_label.setText(f"Deriva: {deriva}")
        self.evaporacion_label.setText(f"Evaporación: {evaporacion}")
        self.condiciones_label.setText(f"Condiciones: {condiciones}")  # sigue mostrando el número
        self.ancho_label.setText(f"Ancho: {ancho} m")
        self.largo_label.setText(f"Largo: {largo} m")
        self.extra_1_label.setText(f"Extra 1: {extra_1}")
        self.extra_2_label.setText(f"Extra 2: {extra_2}")
        self.presion_actual_label.setText(f"Presion Actual: {presion_actual}")
        self.bateria_label.setText(f"Voltaje Batería: {bateria} V")
        self.estado_label.setText(f"Estado: {estado}")

               # --- Mapeo de condiciones a mensajes SOLO para recomendaciones_label ---
        mapa_condiciones = {
            1: "1. Delta T muy bajo (<2 °C) → riesgo de condensación.",
            2: "2. Delta T muy alto (>8 °C) → riesgo de evaporación.",
            3: "3. Velocidad aparente muy baja (<3 km/h) → inversión térmica.",
            4: "4. Velocidad aparente muy alta (>10 km/h) → deriva.",
            5: "5. Deriva alta (>5 m).",
            6: "6. Evaporación rápida (<2 s).",
            7: "7. Taponamiento total.",
            8: "8. Caudal bajo.",
            9: "9. Presión alta (obstrucción parcial).",
            10: "10. Temperatura muy alta (>28 °C).",
            11: "11. Humedad muy baja (<50%).",
            0: "✅ Condiciones óptimas: no hay mejoras necesarias."
        }

        # 🔹 Convertir condiciones en lista si viene como string "3,6,8,9"
        if isinstance(condiciones, str) and "," in condiciones:
            try:
                lista_codigos = [int(c.strip()) for c in condiciones.split(",") if c.strip().isdigit()]
            except Exception:
                lista_codigos = []
        elif isinstance(condiciones, (list, tuple)):
            lista_codigos = [int(round(float(c))) for c in condiciones]
        else:
            try:
                lista_codigos = [int(round(float(condiciones)))]
            except Exception:
                lista_codigos = []

        # 🔹 Mapear a mensajes
        if lista_codigos:
            mensajes = [mapa_condiciones.get(c, f"Condición desconocida: {c}") for c in lista_codigos]
            texto_condiciones = "\n".join(mensajes)
        else:
            texto_condiciones = "⚠️ No se pudieron interpretar las condiciones."

        # Mostrar en la celda de abajo
        self.recomendaciones_label.setText(f"Recomendaciones:\n{texto_condiciones}")
