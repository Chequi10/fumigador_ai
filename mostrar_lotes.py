from PyQt5.QtWidgets import (
    QWidget, QTextEdit, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QGroupBox, QApplication, QTabWidget, QHeaderView
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt


class Ventana_Lotes(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guía de Variables – Operario de Fumigación")
        self.setGeometry(150, 150, 950, 720)

        # ==== Estilo general ====
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2f;
                color: #ffffff;
                border-radius: 10px;
            }
            QTabWidget::pane {
                border: 2px solid #444;
                border-radius: 10px;
                background-color: #2a2a3a;
            }
            QTabBar::tab {
                background: #3c3c5a;
                color: white;
                padding: 10px 30px;
                font-size: 12px;
                min-width: 180px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #5a5a8a;
            }
            QGroupBox {
                border: 1px solid #3a3a50;
                border-radius: 8px;
                margin-top: 10px;
                background-color: #2c2c3c;
                font-weight: bold;
                padding: 10px;
            }
            QTextEdit {
                background-color: #1e1e2f;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #2b2b3d;
                border: 1px solid #444;
                font-size: 11px;
                color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #3f3f5a;
                padding: 5px;
                font-weight: bold;
                border: 1px solid #444;
                color: #ffffff;
            }
        """)

        fuente = QFont("Segoe UI", 10)

        # ==== Pestañas ====
        self.tabs = QTabWidget()
        self.tabs.addTab(self.crear_tab_meteorologia(fuente), "Condiciones Meteorológicas")
        self.tabs.addTab(self.crear_tab_equipo(fuente), "Parámetros del Equipo")
        self.tabs.addTab(self.crear_tab_indices(fuente), "Índices e Interpretación")
        self.tabs.addTab(self.crear_tab_gotas(fuente), "Tamaño de Gotas")
        self.tabs.addTab(self.crear_tab_scores(fuente), "Scores e ICF")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # === Pestaña 1: Meteorología ===
    def crear_tab_meteorologia(self, fuente):
        texto = QTextEdit()
        texto.setFont(fuente)
        texto.setReadOnly(True)
        texto.setText(
            "Las condiciones meteorológicas determinan si el producto llega correctamente al objetivo:\n\n"
            "• Temperatura (°C): Ideal entre 10 y 28 °C. Evitar >32 °C.\n"
            "• Humedad relativa (%): Alta HR reduce evaporación. Pre-emergente ≥40 %, post-emergente ≥50 %.\n"
            "• Velocidad del viento (km/h): 3–15 km/h es adecuado. Evitar viento >20 km/h o calma total.\n"
            "• Dirección del viento (°): Determina la deriva.\n"
            "• Delta T (°C): Diferencia entre temperatura del aire y bulbo húmedo. "
            "Entre 2 y 8 °C es el rango ideal.\n"
        )
        tabla = QTableWidget(3, 3)
        tabla.setFont(fuente)
        tabla.setHorizontalHeaderLabels(["ΔT (°C)", "Situación", "Acción sugerida"])
        datos = [
            ["< 2", "Riesgo de condensación", "Esperar o aumentar T del caldo"],
            ["2 – 8", "Ventana operativa segura", "Aplicar con gotas medianas o gruesas"],
            ["> 8", "Evaporación excesiva", "Usar boquillas de inducción y presión baja"],
        ]
        for f, fila in enumerate(datos):
            for c, val in enumerate(fila):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                tabla.setItem(f, c, item)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout = QVBoxLayout()
        layout.addWidget(self.crearGrupo("Variables meteorológicas", texto))
        layout.addWidget(self.crearGrupo("Rangos de ΔT y acciones", tabla))
        contenedor = QWidget()
        contenedor.setLayout(layout)
        return contenedor

    # === Pestaña 2: Parámetros del equipo ===
    def crear_tab_equipo(self, fuente):
        texto = QTextEdit()
        texto.setFont(fuente)
        texto.setReadOnly(True)
        texto.setText(
            "Factores del pulverizador que influyen directamente en la calidad:\n\n"
            "• Boquilla: Tipo XR, AI o TT. Determina el tamaño de gota y el caudal.\n"
            "• Presión (bar): Modifica el tamaño de gota. Mayor presión → gotas más finas.\n"
            "• Caudal (L/min o L/ha): Volumen aplicado. Asegurar coincidencia con la receta.\n"
            "• Taponamiento:\n"
            "   0 = Total → flujo bloqueado completamente.\n"
            "   1 = Caudal bajo → flujo reducido (filtro o boquilla parcialmente obstruidos).\n"
            "   2 = Presión alta → obstrucción parcial, aumento de presión aguas arriba.\n"
            "   3 = Normal → operación correcta.\n"
            "   4 = Presión baja → posible fuga o bomba débil.\n"
            "• Altura (cm): Cuanto más baja, menor deriva.\n"
            "• Batería (V): Mantener entre 12 y 14.4 V para asegurar buena pulverización.\n"
        )

        # Tabla de ejemplo de boquillas
        tabla = QTableWidget(4, 3)
        tabla.setFont(fuente)
        tabla.setHorizontalHeaderLabels(["Boquilla", "Presión (bar)", "Caudal (L/ha)"])
        datos = [
            ["Azul XR11002", "2", "220"],
            ["Roja AI11003", "3", "350"],
            ["Amarilla TT110015", "2", "180"],
            ["Verde XR11004", "2.5", "300"],
        ]
        for f, fila in enumerate(datos):
            for c, val in enumerate(fila):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                tabla.setItem(f, c, item)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Tabla explicativa de taponamiento
        tabla_tapon = QTableWidget(5, 3)
        tabla_tapon.setFont(fuente)
        tabla_tapon.setHorizontalHeaderLabels(["Código", "Condición", "Acción recomendada"])
        datos_tapon = [
            ["0", "Taponamiento total", "Limpiar filtros y boquillas de inmediato"],
            ["1", "Caudal bajo", "Revisar filtros o restricción en mangueras"],
            ["2", "Presión alta (obstrucción parcial)", "Revisar boquillas y línea de presión"],
            ["3", "Normal", "Operación estable – sin acciones necesarias"],
            ["4", "Presión baja", "Verificar bomba, fugas o válvulas defectuosas"],
        ]
        for f, fila in enumerate(datos_tapon):
            for c, val in enumerate(fila):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                tabla_tapon.setItem(f, c, item)
        tabla_tapon.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout = QVBoxLayout()
        layout.addWidget(self.crearGrupo("Parámetros del equipo", texto))
        layout.addWidget(self.crearGrupo("Ejemplo de boquillas", tabla))
        layout.addWidget(self.crearGrupo("Códigos y acciones de Taponamiento", tabla_tapon))
        contenedor = QWidget()
        contenedor.setLayout(layout)
        return contenedor

    # === Pestaña 3: Índices ===
    def crear_tab_indices(self, fuente):
        texto = QTextEdit()
        texto.setFont(fuente)
        texto.setReadOnly(True)
        texto.setText(
            "Los índices combinan los factores ambientales y del equipo para generar una evaluación global:\n\n"
            "• Punto de rocío (°C): Temperatura a la que el aire se satura.\n"
            "• Bulbo húmedo (Tw): Base para el cálculo del ΔT.\n"
            "• ΔT (°C): Diferencia entre temperatura ambiente y Tw. Mide riesgo térmico.\n"
            "• Deriva estimada (m): Desplazamiento lateral de la gota.\n"
            "• Evaporación (s): Tiempo que tarda una gota en secarse.\n"
            "• ICF (0–100): Índice global de calidad de fumigación.\n"
        )
        tabla = QTableWidget(3, 3)
        tabla.setFont(fuente)
        tabla.setHorizontalHeaderLabels(["ICF", "Condición", "Acción sugerida"])
        datos = [
            ["< 40", "Mala", "Suspender aplicación"],
            ["40–79", "Aceptable", "Corregir presión o velocidad"],
            [">= 80", "Excelente", "Condiciones óptimas"],
        ]
        for f, fila in enumerate(datos):
            for c, val in enumerate(fila):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                tabla.setItem(f, c, item)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout = QVBoxLayout()
        layout.addWidget(self.crearGrupo("Índices principales", texto))
        layout.addWidget(self.crearGrupo("Interpretación del ICF", tabla))
        contenedor = QWidget()
        contenedor.setLayout(layout)
        return contenedor

    # === Pestaña 4: Tamaño de gotas ===
    def crear_tab_gotas(self, fuente):
        texto = QTextEdit()
        texto.setFont(fuente)
        texto.setReadOnly(True)
        texto.setText(
            "El tamaño de gota (Dv0.5 en µm) determina la cobertura y el riesgo de deriva:\n\n"
            "• Muy finas (<150 µm): Excelente cobertura, pero alta deriva y evaporación.\n"
            "• Finas (150–250 µm): Buen compromiso, sensibles a ΔT alto.\n"
            "• Medias (250–350 µm): Buen equilibrio entre cobertura y seguridad.\n"
            "• Gruesas (350–450 µm): Menor deriva, ideales con viento moderado.\n"
            "• Muy gruesas (>450 µm): Baja deriva, pero menor cobertura.\n\n"
            "El tamaño depende de la boquilla, la presión y la viscosidad del caldo.\n"
            "Las boquillas de inducción de aire generan gotas más grandes y estables.\n"
        )
        tabla = QTableWidget(5, 3)
        tabla.setFont(fuente)
        tabla.setHorizontalHeaderLabels(["Clasificación", "Dv0.5 (µm)", "Deriva esperada"])
        datos = [
            ["Muy fina", "<150", "Alta"],
            ["Fina", "150–250", "Moderada-Alta"],
            ["Media", "250–350", "Media"],
            ["Gruesa", "350–450", "Baja"],
            ["Muy gruesa", ">450", "Muy baja"],
        ]
        for f, fila in enumerate(datos):
            for c, val in enumerate(fila):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                tabla.setItem(f, c, item)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout = QVBoxLayout()
        layout.addWidget(self.crearGrupo("Clasificación ISO de gotas", texto))
        layout.addWidget(self.crearGrupo("Tamaño de gota y deriva", tabla))
        contenedor = QWidget()
        contenedor.setLayout(layout)
        return contenedor

        # === Pestaña 5: Scores e ICF ===
    def crear_tab_scores(self, fuente):
        texto = QTextEdit()
        texto.setFont(fuente)
        texto.setReadOnly(True)
        texto.setText(
            "El sistema calcula varios scores (0–100) que reflejan el aporte de cada variable al ICF total:\n\n"
            "• ΔTscore: Evalúa condiciones térmicas. Ideal cuando ΔT está entre 2–8 °C. ΔT bajo → condensación; alto → evaporación.\n"
            "• Velocidadscore: Penaliza viento excesivo (>10 km/h) o muy bajo (<3 km/h). Ambos afectan la estabilidad del caldo.\n"
            "• Derivascore: Disminuye si el viento o la altura provocan desplazamiento lateral >5 m.\n"
            "• Evaporacionscore: Refleja cuánto tarda en evaporarse una gota. <2 s → riesgo de pérdida antes del impacto.\n"
            "• TaponamientoScore: Evalúa obstrucción en boquillas y presión de trabajo.\n"
            "   - 100 = sin problemas (flujo normal).\n"
            "   - 50 = presión alta o baja parcial (obstrucción o fuga leve).\n"
            "   - 30 = taponamiento total (flujo bloqueado).\n"
            "• CaudalScore: Evalúa si el caudal real coincide con el deseado. Desvíos ±10 % reducen el score.\n"
            "• PresionScore: Evalúa la presión de trabajo respecto al valor recomendado para la boquilla seleccionada.\n\n"
            "El ICF (Índice de Calidad de Fumigación) es el promedio ponderado de los seis scores:\n\n"
            "ICF = (ΔTscore + Velocidadscore + Derivascore + Evaporacionscore + "
            "TaponamientoScore + CaudalScore + PresionScore) / 6\n\n"
            "Interpretación:\n"
            "• ICF ≥ 80 → Excelente (verde): condiciones óptimas.\n"
            "• 60–79 → Aceptable (amarillo): ajustar alguna variable.\n"
            "• <60 → Riesgoso (rojo): suspender la aplicación.\n\n"
            "Cómo mejorar:\n"
            "– Si el ΔTscore es bajo → cambiar horario o aumentar humedad.\n"
            "– Si el Velocidadscore es bajo → ajustar velocidad del tractor o esperar menos viento.\n"
            "– Si el Derivascore cae → bajar altura o usar boquillas más grandes.\n"
            "– Si el Evaporacionscore baja → usar gotas más grandes o coadyuvantes.\n"
            "– Si el TaponamientoScore baja → revisar presión: presión alta = obstrucción parcial, presión baja = fuga o bomba débil.\n"
            "– Si el CaudalScore baja → verificar filtros, picos o calibración del flujómetro.\n"
            "– Si el PresionScore baja → ajustar presión o revisar regulador.\n"
        )

        tabla = QTableWidget(7, 3)
        tabla.setFont(fuente)
        tabla.setHorizontalHeaderLabels(["Score", "Peso en el ICF (%)", "Influencia"])
        datos = [
            ["ΔTscore", "16.7", "Condiciones térmicas (2–8 °C ideales)"],
            ["Velocidadscore", "16.7", "Viento y desplazamiento relativo"],
            ["Derivascore", "16.7", "Desviación lateral de gotas"],
            ["Evaporacionscore", "16.7", "Velocidad de secado de gotas"],
            ["TaponamientoScore", "16.7", "Estado de boquillas y presión del sistema"],
            ["CaudalScore", "16.7", "Coincidencia entre caudal real y deseado"],
            ["PresionScore", "16.7", "Presión adecuada según boquilla y caudal"],
        ]
        for f, fila in enumerate(datos):
            for c, val in enumerate(fila):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                tabla.setItem(f, c, item)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout = QVBoxLayout()
        layout.addWidget(self.crearGrupo("Explicación detallada de Scores", texto))
        layout.addWidget(self.crearGrupo("Peso de cada Score en el ICF", tabla))
        contenedor = QWidget()
        contenedor.setLayout(layout)
        return contenedor


    # --- Utilidad ---
    def crearGrupo(self, titulo, widget):
        grupo = QGroupBox(titulo)
        grupo.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout = QVBoxLayout()
        layout.addWidget(widget)
        grupo.setLayout(layout)
        return grupo


# --- Prueba directa ---
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ventana = Ventana_Lotes()
    ventana.show()
    sys.exit(app.exec_())
