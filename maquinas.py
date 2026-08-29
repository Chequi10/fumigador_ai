import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QLineEdit, QFormLayout, QDialogButtonBox
)
archivo_db = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/coordenadas_db"
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
                    gps TEXT,
                    -- sembradora
                    ancho_botalon TEXT,
                    cant_secciones TEXT,
                    sep_picos TEXT,
                    tipo_picos TEXT,
                    -- cosechadora
                    ancho_corte TEXT,
                    cant_surcos TEXT,
                    -- tractor
                    campo1 TEXT,
                    campo2 TEXT
                )
            """)
            conn.commit()
            
            print("Base de datos SQLite iniciada correctamente.")
    except Exception as e:
        print(f"\033[33mError al iniciar la base de datos: {e}\033[0m")
    

# Guarda una máquina en la base de datos
def guardar_maquina_en_sqlite(datos):
    conn = sqlite3.connect(archivo_db)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO maquinas (
            tipo, marca, alto, ancho, largo, gps,
            ancho_botalon, cant_secciones, sep_picos, tipo_picos,
            ancho_corte, cant_surcos, campo1, campo2
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datos.get("tipo"), datos.get("Marca"), datos.get("Alto"), datos.get("Ancho"),
        datos.get("Largo"), datos.get("GPS (lat, lon)"), datos.get("Ancho de botalon"),
        datos.get("Cantidad de secciones"), datos.get("Separacion de picos"), datos.get("Tipos de picos"),
        datos.get("Ancho de corte"), datos.get("Cantidad de surcos"),
        datos.get("Campo 1"), datos.get("Campo 2")
    ))
    conn.commit()
    conn.close()

# Muestra la tabla con las máquinas guardadas
def mostrar_tabla_maquinas(parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle("Listado máquinas registradas")
    layout = QVBoxLayout()
    tabla = QTableWidget()
    layout.addWidget(tabla)

    conn = sqlite3.connect("maquinas.db")
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

    tabla.resizeColumnsToContents()
    btn_cerrar = QPushButton("Cerrar")
    btn_cerrar.clicked.connect(dialog.accept)
    layout.addWidget(btn_cerrar)
    dialog.setLayout(layout)
    dialog.exec_()

# Muestra el diálogo para ingresar una nueva máquina
def mostrar_configuracion_maquina(parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle("Configuración de máquina")

    layout = QVBoxLayout()
    form_layout = QFormLayout()

    combo_tipo = QComboBox()
    combo_tipo.addItems(["Tractor", "Sembradora", "Cosechadora"])
    form_layout.addRow("Tipo de máquina", combo_tipo)

    campos_comunes = {}
    for nombre in ["Marca", "Alto", "Ancho", "Largo", "GPS (lat, lon)"]:
        campo = QLineEdit()
        campos_comunes[nombre] = campo
        form_layout.addRow(nombre, campo)

    # Campos opcionales
    campos_semb = {}
    for nombre in ["Ancho de botalon", "Cantidad de secciones", "Separacion de picos", "Tipos de picos"]:
        campo = QLineEdit()
        campos_semb[nombre] = campo

    campos_cose = {}
    for nombre in ["Ancho de corte", "Cantidad de surcos"]:
        campo = QLineEdit()
        campos_cose[nombre] = campo

    campos_tractor = {}
    for nombre in ["Campo 1", "Campo 2"]:
        campo = QLineEdit()
        campos_tractor[nombre] = campo

    contenedor_campos_opcionales = QVBoxLayout()
    layout.addLayout(form_layout)
    layout.addLayout(contenedor_campos_opcionales)

    def actualizar_campos():
        for i in reversed(range(contenedor_campos_opcionales.count())):
            item = contenedor_campos_opcionales.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        tipo = combo_tipo.currentText()
        if tipo == "Sembradora":
            for nombre, campo in campos_semb.items():
                contenedor_campos_opcionales.addWidget(QLabel(nombre))
                contenedor_campos_opcionales.addWidget(campo)
        elif tipo == "Cosechadora":
            for nombre, campo in campos_cose.items():
                contenedor_campos_opcionales.addWidget(QLabel(nombre))
                contenedor_campos_opcionales.addWidget(campo)
        elif tipo == "Tractor":
            for nombre, campo in campos_tractor.items():
                contenedor_campos_opcionales.addWidget(QLabel(nombre))
                contenedor_campos_opcionales.addWidget(campo)

    combo_tipo.currentTextChanged.connect(actualizar_campos)
    actualizar_campos()

    botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

    def guardar_y_cerrar():
        datos = {"tipo": combo_tipo.currentText()}
        for nombre, campo in campos_comunes.items():
            datos[nombre] = campo.text()

        tipo = combo_tipo.currentText()
        if tipo == "Sembradora":
            for nombre, campo in campos_semb.items():
                datos[nombre] = campo.text()
        elif tipo == "Cosechadora":
            for nombre, campo in campos_cose.items():
                datos[nombre] = campo.text()
        elif tipo == "Tractor":
            for nombre, campo in campos_tractor.items():
                datos[nombre] = campo.text()

        guardar_maquina_en_sqlite(datos)
        dialog.accept()

    botones.accepted.connect(guardar_y_cerrar)
    botones.rejected.connect(dialog.reject)
    layout.addWidget(botones)

    dialog.setLayout(layout)
    dialog.exec_()