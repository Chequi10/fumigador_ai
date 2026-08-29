import queue
import sys
import cv2
import numpy as np
import warnings
import sqlite3
from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from hilo_data_jetson import cola_total
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout ,QTableWidget, QTableWidgetItem, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import QSize
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QSizePolicy, QStackedWidget
from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QMessageBox



class Ventana_mapa(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Imagen Satelital Real Time")
        self.setGeometry(150, 150, 900, 600)
        self.web_view = QWebEngineView()
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.web_view)
        self.setCentralWidget(central_widget)

        # Coordenadas de ejemplo
        lat = -34.6037
        lon = -58.3816

      
        self.load_google_maps(lat, lon)

    def load_google_maps(self, lat, lon):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyAfvCvQYCVdNg3-RlbZNcvLoMCcv92xaP4"></script>
            <script>
                var map;
                var zoomLevel = 0;
                var maxZoom = 16;
                var zoomInterval;
                var marker;
                var infoWindow;

                function initMap() {{
                    var location = {{lat: {lat}, lng: {lon} }};
                    map = new google.maps.Map(document.getElementById("map"), {{
                        zoom: zoomLevel,
                        center: location,
                        mapTypeId: 'hybrid'
                    }});

                    marker = new google.maps.Marker({{
                        position: location,
                        map: map,
                        title: "Ubicación actual"
                    }});

                    // Crear la ventana de información
                    infoWindow = new google.maps.InfoWindow({{
                        content: 'Latitud: ' + location.lat.toFixed(6) + '<br>Longitud: ' + location.lng.toFixed(6),
                        disableAutoPan: true  // evita que se mueva el mapa
                    }});

                    // Mostrar info al pasar el mouse
                    marker.addListener('mouseover', function() {{
                        infoWindow.open(map, marker);
                    }});

                    // Ocultar info al quitar el mouse
                    marker.addListener('mouseout', function() {{
                        infoWindow.close();
                    }});

                    // Zoom progresivo
                    zoomInterval = setInterval(() => {{
                        if (zoomLevel < maxZoom) {{
                            zoomLevel++;
                            map.setZoom(zoomLevel);
                        }} else {{
                            clearInterval(zoomInterval);
                        }}
                    }}, 300);
                }}

                function updateMarker(lat, lng) {{
                    var newLocation = {{lat: lat, lng: lng}};
                    marker.setPosition(newLocation);
                    map.setCenter(newLocation);
                    infoWindow.setContent('Latitud: ' + lat.toFixed(6) + '<br>Longitud: ' + lng.toFixed(6));
                }}
            </script>
        </head>
        <body onload="initMap()">
            <div id="map" style="width:100%; height:100vh; margin:0; padding:0;"></div>
        </body>
        </html>
        """
        self.web_view.setHtml(html)



    
    def update_map_marker(self, lat, lon):
        js_code = f"updateMarker({lat}, {lon});"
        self.web_view.page().runJavaScript(js_code)       