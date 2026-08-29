import cv2
import numpy as np
import torch
import time
from pathlib import Path
from ultralytics import YOLO

# Ruta al modelo entrenado
MODEL_PATH = "/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/yolov5/best.pt"

# Inicializar el modelo YOLO
model = YOLO(MODEL_PATH)

# Cargar el modelo asegurando que está en CPU
model = torch.hub.load('ultralytics/yolov5', 'custom', path=MODEL_PATH, device='cpu')

clase_objetivo = "cultivos"  # Cambia esto según la clase que quieras detectar
# Lista para almacenar los centros de los objetos detectados
centros = []
# Obtener altura del frame

# Abrir la cámara (2 para la cámara específica)
cap = cv2.VideoCapture('/home/ezequiel/Dropbox/Ezequiel/Bayer_solutions/ia/campopie.mp4')
fps = int(cap.get(cv2.CAP_PROP_FPS))  # Obtener FPS del video


# Verificar si la cámara se abre correctamente
if not cap.isOpened():
    print("Error: No se puede abrir la cámara")
    exit()

# Establecer el nombre de la ventana
window_name = 'Detecciones'
cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

     # Inicializar la variable para la detección más alta
    # Inicializar la variable para la detección más alta
y_min_detectado = float('inf')

    # Mantener solo los puntos más altos (más cercanos al margen superior)
centros_validos = []

# Control de parpadeo de la flecha
blink_interval = 0.5  # Intervalo de tiempo en segundos
last_blink_time = time.time()
show_arrow = True  # Indica si la flecha es visible


dibujar_lineas = True

while True:
    # Capturar un frame de la cámara
    ret, frame = cap.read()
    if not ret:
        print("No se puede capturar el frame")
        break
    frame = cv2.resize(frame, (476, 648), interpolation=cv2.INTER_AREA)    

     # Dimensiones del frame
    height, width, _ = frame.shape    
     # Definir la franja de detección (esto es personalizable)
    y_min = int(height * 0.2) # Coordenada Y superior de la franja
    y_max = int(height * 0.9)  # Coordenada Y inferior de la franja

    # Definir límites de la franja en X
    x_min = int(width * 0.50)   # Límite izquierdo (ajusta según necesites)
    x_max = int(width * 0.75)   # Límite derecho (ajusta según necesites)    
    # Recortar la franja de la imagen (solo procesar la franja entre y_min y y_max)
    frame_cropped = frame[x_min:x_max]  # Recorta solo la franja vertical

    # Realizar la predicción con YOLO
    results = model(frame)
    
    # Dibujar las detecciones en el frame
    annotated_frame = results.render()[0]
    detections = results.pandas().xyxy[0]  
      
    # Calcular el tiempo actual
    current_time = time.time()
    
    # Alternar la visibilidad de la flecha cada 'blink_interval'
    if current_time - last_blink_time >= blink_interval:
        show_arrow = not show_arrow
        last_blink_time = current_time
    
   
    
    # Dibujar la flecha si está visible
    if show_arrow:
        start_point = (width // 2 + 250, 20)
        end_point = (width // 2 + 300, 20)
        color = (0, 255, 0)  # Verde
    else:
        start_point = (width // 2 - 250, 20)
        end_point = (width // 2 - 300, 20)
        color = (0, 0, 255)  # Rojo
    
    cv2.arrowedLine(frame, start_point, end_point, color, 6, tipLength=0.3)
   

    # Dibujar el texto
    text = "Active Auto Pilot"
    coordinates = (width // 2 - 140, 25)
    cv2.putText(frame, text, coordinates, cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
    
    

 

   

    for i, row in detections.iterrows():
        if row['name'] == clase_objetivo:  # Filtra por la clase deseada
            x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
            centro = (int((x1 + x2) / 2), int((y1 + y2) / 2))
            
            # Filtrar solo los centros dentro de la zona de detección
            if x_min <= centro[0] <= x_max and y_min <= centro[1] <= y_max:
                # Solo añadir centros que estén más cercanos al borde superior (más pequeños en y)
                if centro[1] < y_min_detectado:
                    y_min_detectado = centro[1]
                    centros_validos.append(centro)

    # Ordenar los centros según su valor en el eje Y (de arriba a abajo)
    centros_validos.sort(key=lambda x: x[1])

    # Dibujar las líneas entre los puntos más cercanos al margen superior
    if dibujar_lineas and len(centros_validos) > 1:
        for i in range(1, len(centros_validos)):
            cv2.line(frame, centros_validos[i - 1], centros_validos[i], (0, 240, 255), 18)  # Amarillo


    # Función para suavizar puntos usando un filtro de media móvil
    def suavizar_puntos(puntos, window_size=3):
        if len(puntos) < window_size:
            return puntos
        smoothed_points = []
        for i in range(len(puntos)):
            start = max(0, i - window_size // 2)
            end = min(len(puntos), i + window_size // 2 + 1)
            window = puntos[start:end]
            smoothed_point = (int(np.mean([p[0] for p in window])), int(np.mean([p[1] for p in window])))
            smoothed_points.append(smoothed_point)
        return smoothed_points

    # Suavizar los centros válidos
    centros_suavizados = suavizar_puntos(centros_validos, window_size=5)

    # Dibujar la línea suavizada
    if len(centros_suavizados) > 1:
        for i in range(1, len(centros_suavizados)):
            cv2.line(frame, centros_suavizados[i - 1], centros_suavizados[i], (0, 0, 255), 3)  # Línea suavizada en rojo

            


    
   

    segment_length = 40
    line_thickness = 3
    color = (168, 56, 0)  # Azul de Boca Juniors en formato BGR
    colorcruz = (0, 255, 255)
    
    # Esquinas de la mirilla
    cv2.line(frame, (x_min, y_min), (x_min + segment_length, y_min), color, line_thickness)  # Esquina superior izquierda (horizontal)
    cv2.line(frame, (x_min, y_min), (x_min, y_min + segment_length), color, line_thickness)  # Esquina superior izquierda (vertical)

    cv2.line(frame, (x_max, y_min), (x_max - segment_length, y_min), color, line_thickness)  # Esquina superior derecha (horizontal)
    cv2.line(frame, (x_max, y_min), (x_max, y_min + segment_length), color, line_thickness)  # Esquina superior derecha (vertical)

    cv2.line(frame, (x_min, y_max), (x_min + segment_length, y_max), color, line_thickness)  # Esquina inferior izquierda (horizontal)
    cv2.line(frame, (x_min, y_max), (x_min, y_max - segment_length), color, line_thickness)  # Esquina inferior izquierda (vertical)

    cv2.line(frame, (x_max, y_max), (x_max - segment_length, y_max), color, line_thickness)  # Esquina inferior derecha (horizontal)
    cv2.line(frame, (x_max, y_max), (x_max, y_max - segment_length), color, line_thickness)  # Esquina inferior derecha (vertical)

    # Puntos de inicio en la parte inferior
    """start_left = (int(width * 0.2), height)  # (128, 480) → Parte baja izquierda
    end_left = (int(width * 0.4), 0)  # (256, 288) → Se inclina hacia el centro


    start_right = (int(width * 0.8), height)  # (512, 480) → Parte baja derecha
    end_right = (int(width * 0.6), 0)  # (384, 288) → Se inclina hacia el centro



    # Dibujar líneas rojas (zona de peligro)
    cv2.line(frame, start_left, end_left, (0, 0, 255), 5)  # Rojo
    cv2.line(frame, start_right,end_right, (0, 0, 255), 5)"""

   # CRUZ PUNTEADA DENTRO DE LA MIRILLA
    center_x = (x_min + x_max) // 2
    center_y = (y_min + y_max) // 2
    dot_spacing = 14  # Espaciado entre los puntos
    dot_size = 3  # Tamaño de los puntos

    # Línea horizontal punteada dentro de la mirilla
    for x in range(x_min + 10, x_max - 10, dot_spacing):
        cv2.circle(frame, (x, center_y), dot_size, colorcruz, -1)

    # Línea vertical punteada dentro de la mirilla
    for y in range(y_min + 10, y_max - 10, dot_spacing):
        cv2.circle(frame, (center_x, y), dot_size, colorcruz, -1)



    # Redimensionar el frame y mostrarlo
    #resized_frame = cv2.resize(frame, (1280, 660))
    cv2.imshow(window_name, frame)
    cv2.moveWindow(window_name, 80, 0)
    
   # Esperar una tecla y obtener la tecla presionada
    key = cv2.waitKey(max(1, int(1000 / fps))) & 0xFF
    
    # Si se presiona 'q', cerrar
    if key == ord('q'):
        break
    # Si se presiona 'l', alternar el estado de 'dibujar_lineas'
    elif key == ord('l'):
        dibujar_lineas = not dibujar_lineas
# Liberar la cámara y cerrar ventanas
cap.release()
cv2.destroyAllWindows()


