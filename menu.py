import cv2
import numpy as np

# Dimensiones de la pantalla del menú
width, height = 800, 600

# Colores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (255, 0, 0)

# Estado del menú
menu_visible = False

# Opciones del menú
menu_options = ["Opción 1", "Opción 2", "Opción 3"]

def draw_menu(frame):
    """Dibuja el menú en la pantalla."""
    start_y = 50
    for i, option in enumerate(menu_options):
        cv2.rectangle(frame, (20, start_y + i * 40), (200, start_y + (i + 1) * 40), GRAY, -1)
        cv2.putText(frame, option, (30, start_y + i * 40 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, BLACK, 2)

def toggle_menu():
    """Alterna la visibilidad del menú."""
    global menu_visible
    menu_visible = not menu_visible

def is_menu_visible():
    """Devuelve el estado del menú."""
    return menu_visible

def mouse_callback(event, x, y, flags, param):
    """Detecta clic en el botón MENÚ."""
    if event == cv2.EVENT_LBUTTONDOWN:
        if 20 <= x <= 120 and 20 <= y <= 50:
            toggle_menu()

def start_menu_loop():
    """Bucle principal del menú."""
    cv2.namedWindow("Pantalla Menú")
    cv2.setMouseCallback("Pantalla Menú", mouse_callback)

    while True:
        screen = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Dibuja el botón "MENÚ"
        cv2.rectangle(screen, (20, 20), (120, 50), BLUE, -1)
        cv2.putText(screen, "MENÚ", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2)

        # Mostrar opciones del menú si está activo
        if is_menu_visible():
            draw_menu(screen)

        cv2.imshow("Pantalla Menú", screen)

        # Salir con 'q'
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
