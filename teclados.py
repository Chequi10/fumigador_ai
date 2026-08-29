from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PyQt5.QtGui import QFont, QGuiApplication
from PyQt5.QtCore import Qt


class TecladoNumerico(QWidget):
    def __init__(self, line_edit, on_ok=None, parent=None):
        super().__init__(parent)
        self.line_edit = line_edit
        self.on_ok = on_ok
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
         # 👇 estilo global del teclado
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }

            QPushButton {
                background-color: #2b2b2b;
                color: #00FF7F;
                border: 1px solid #444;
                border-radius: 8px;
                font-size: 20px;
                font-weight: bold;
            }

            QPushButton:pressed {
                background-color: #00FF7F;
                color: black;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(6, 6, 6, 6)

        botones = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['0', '.', 'Borrar'],
            ['OK']
        ]

        for fila in botones:
            fila_layout = QHBoxLayout()
            fila_layout.setSpacing(4)
            fila_layout.setContentsMargins(0, 0, 0, 0)

            for texto in fila:
                boton = QPushButton(texto)
                boton.clicked.connect(lambda _, t=texto: self.boton_presionado(t))
                boton.setMinimumSize(90, 50)

                if texto == "Borrar":
                    boton.setFont(QFont("Segoe UI", 13, QFont.Bold))
                elif texto == "OK":
                    boton.setFont(QFont("Segoe UI", 16, QFont.Bold))
                else:
                    boton.setFont(QFont("Segoe UI", 20, QFont.Bold))

                boton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                boton.setStyleSheet("""
                    QPushButton {
                        background-color: #2b2b2b;
                        color: #00FF7F;
                        border: 1px solid #444;
                        border-radius: 8px;
                    }
                    QPushButton:pressed {
                        background-color: #00FF7F;
                        color: black;
                    }
                """)

                fila_layout.addWidget(boton)

            if fila == ['OK']:
                fila_layout.itemAt(0).widget().setMinimumHeight(75)

            layout.addLayout(fila_layout)

        self.setLayout(layout)

    def boton_presionado(self, texto):
        if texto == 'OK':
            if self.on_ok:
                self.on_ok()
            self.close()
        elif texto == 'Borrar':
            actual = self.line_edit.text()
            self.line_edit.setText(actual[:-1])
        else:
            self.line_edit.setText(self.line_edit.text() + texto)


class TecladoAlfanumerico(QWidget):
    def __init__(self, line_edit, on_ok=None, parent=None):
        super().__init__(parent)
        self.line_edit = line_edit
        self.on_ok = on_ok
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.mayusculas = False
        self.botones = []
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
            caracter = texto.upper() if self.mayusculas else texto.lower()
            self.line_edit.setText(self.line_edit.text() + caracter)

    def actualizar_modo_mayusculas(self):
        for boton in self.botones:
            texto = boton.text()
            boton.setText(texto.upper() if self.mayusculas else texto.lower())


def mostrar_teclado_numerico_para_widget(widget_referencia, line_edit, on_ok=None, parent=None):
    teclado = TecladoNumerico(line_edit, on_ok=on_ok, parent=parent)
    teclado.adjustSize()

    pos = widget_referencia.mapToGlobal(widget_referencia.rect().topLeft())

    from PyQt5.QtGui import QGuiApplication
    screen = QGuiApplication.screenAt(pos)
    if screen is None:
        screen = QGuiApplication.primaryScreen()

    geo = screen.availableGeometry()

    # siempre a la derecha del campo
    x = pos.x() + widget_referencia.width() + 12
    y = pos.y()

    # solo corrige verticalmente para que no se salga de pantalla
    if y + teclado.height() > geo.bottom():
        y = geo.bottom() - teclado.height() - 12

    if y < geo.top():
        y = geo.top() + 12

    teclado.move(x, y)
    teclado.show()
    teclado.raise_()
    teclado.activateWindow()

    return teclado