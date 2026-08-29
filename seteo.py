from hilo_data_jetson import cola_total
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout ,QTableWidget, QTableWidgetItem, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QMessageBox
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor

def mostrar_tabla_info(self):
        dialog_tabla = QDialog(self)
        dialog_tabla.setWindowTitle("Boquillas disponibles")

        layout = QVBoxLayout()

        tabla = QTableWidget()
        tabla.setRowCount(5)
        tabla.setColumnCount(4)
        tabla.setHorizontalHeaderLabels(["Color", "Código", "Caudal (L/min)", "Micraje"])

        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setSelectionMode(QTableWidget.SingleSelection)

        # Datos: color (clave), código, caudal, micraje
        datos_boquillas = [
            ["blue", "XR11002", "0.76", "250"],
            ["red", "XR11003", "1.14", "300"],
            ["green", "XR110015", "0.57", "200"],
            ["yellow", "AI11004", "1.51", "400"],
            ["violet", "XR11005", "1.89", "450"]
        ]

        for fila, datos in enumerate(datos_boquillas):
            color_nombre, codigo, caudal, micraje = datos

            # Celda de color como casilla pintada
            item_color = QTableWidgetItem()
            item_color.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            color_obj = QColor(color_nombre)

            item_color.setBackground(color_obj)
            item_color.setText("")  # No mostrar texto

            # Forzar tamaño cuadrado visualmente
            tabla.setRowHeight(fila, 30)  # Alto de fila
            tabla.setColumnWidth(0, 50)   # Ancho de columna del color

            tabla.setItem(fila, 0, item_color)
            tabla.setItem(fila, 1, QTableWidgetItem(codigo))
            tabla.setItem(fila, 2, QTableWidgetItem(caudal))
            tabla.setItem(fila, 3, QTableWidgetItem(micraje))

        layout.addWidget(tabla)

        btn_cerrar = QPushButton("Seleccionar y cerrar")

        def cerrar_y_guardar():
            fila_seleccionada = tabla.currentRow()
            if fila_seleccionada != -1:
                color = datos_boquillas[fila_seleccionada][0]
                codigo = tabla.item(fila_seleccionada, 1).text()
                caudal = tabla.item(fila_seleccionada, 2).text()
                micraje = tabla.item(fila_seleccionada, 3).text()
                self.boquilla_seleccionada = {
                    "color": color,
                    "codigo": codigo,
                    "caudal": caudal,
                    "micraje": micraje
                }
            else:
                self.boquilla_seleccionada = None
            dialog_tabla.accept()

        btn_cerrar.clicked.connect(cerrar_y_guardar)
        layout.addWidget(btn_cerrar)

        dialog_tabla.setLayout(layout)
        dialog_tabla.exec_()





       
def modificar_parametros(self):
    self.setStyleSheet("""
        QWidget {
            background-color: #333333;
            border: 3px solid black;
            border-radius: 5px;
        }
    """)

    layout = QVBoxLayout()

    # 1. ComboBox Campo/Lote
    campo_combo = QComboBox()
    campo_combo.addItems(["Seleccione un campo", "Campo 1", "Campo 2", "Campo 3", "Campo 4"])
    layout.addWidget(QLabel("Seleccione el campo/lote:"))
    layout.addWidget(campo_combo)

    # 2. ComboBox Cultivo
    cultivo_combo = QComboBox()
    cultivo_combo.addItems(["Seleccione un cultivo", "Temprano", "Tardío", "Primera", "Segunda"])
    cultivo_combo.setEnabled(False)
    layout.addWidget(QLabel("Seleccione el cultivo:"))
    layout.addWidget(cultivo_combo)

    # 3. ComboBox Tratamiento
    tratamiento_combo = QComboBox()
    tratamiento_combo.addItems(["Seleccione un tratamiento", "Barbecho corto", "Barbecho largo", "Emergente"])
    tratamiento_combo.setEnabled(False)
    layout.addWidget(QLabel("Seleccione el tratamiento:"))
    layout.addWidget(tratamiento_combo)

    # 4. Litros por hectárea
    litros_input = QLineEdit()
    litros_input.setPlaceholderText("Litros por hectárea")
    litros_input.setEnabled(False)
    layout.addWidget(QLabel("Ingrese los litros por hectárea:"))
    layout.addWidget(litros_input)

    # 5. Presión
    presion_input = QLineEdit()
    presion_input.setPlaceholderText("Presión en bar")
    presion_input.setEnabled(False)
    layout.addWidget(QLabel("Ingrese la presión de trabajo:"))
    layout.addWidget(presion_input)

    # Reglas de habilitación
    campo_combo.currentIndexChanged.connect(
        lambda: cultivo_combo.setEnabled(campo_combo.currentIndex() != 0)
    )
    cultivo_combo.currentIndexChanged.connect(
        lambda: tratamiento_combo.setEnabled(cultivo_combo.currentIndex() != 0)
    )
    tratamiento_combo.currentIndexChanged.connect(
        lambda: litros_input.setEnabled(tratamiento_combo.currentIndex() != 0)
    )

    def on_enter_litros():
        texto = litros_input.text().strip()
        if texto.replace(".", "", 1).isdigit():
            mostrar_tabla_info()

            if self.boquilla_seleccionada:
                presion_input.setEnabled(True)

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

    # Diálogo
    dialog = QDialog(self)
    dialog.setWindowTitle("Modificar parámetros")
    dialog.setLayout(layout)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    layout.addWidget(buttons)

    def validar_y_cerrar():
        nueva_presion = presion_input.text()
        litros_texto = litros_input.text().strip()

        if (self.boquilla_seleccionada and
            nueva_presion.replace(".", "", 1).isdigit() and
            litros_texto.replace(".", "", 1).isdigit()):

            self.campo_seleccionado = campo_combo.currentText()
            self.cultivo_seleccionado = cultivo_combo.currentText()
            self.tratamiento_seleccionado = tratamiento_combo.currentText()
            self.litros_por_hectarea = float(litros_texto)
            self.boquilla = self.boquilla_seleccionada["codigo"]
            self.micras_seleccionadas = int(self.boquilla_seleccionada["micraje"])
            self.presion_trabajo = float(nueva_presion)

            # Actualiza etiquetas
            self.boquilla_label.setText(f"Boquilla:\n {self.boquilla} - {self.micras_seleccionadas} micras")
            self.presion_trabajo_label.setText(f"Presión de Trabajo\n: {self.presion_trabajo} bar")

            dialog.accept()
        else:
            QMessageBox.warning(dialog, "Entrada inválida", "Verificá que todos los campos estén completos y correctos")

    buttons.accepted.connect(validar_y_cerrar)
    buttons.rejected.connect(dialog.reject)

    dialog.exec_()