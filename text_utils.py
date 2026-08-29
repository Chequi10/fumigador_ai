# text_utils.py
from PIL import ImageFont, ImageDraw, Image
import numpy as np
import cv2
import numpy as np


def draw_text_with_symbol(frame, text, position, position_symbol=0, symbol=None, font_size=32, symbol_font_size=None, font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", text_color=(0, 0, 0), symbol_color=(0, 255, 0), text_thickness=1):
    """
    Dibuja texto con un símbolo en una imagen usando PIL, con opción de grosor para el texto.
    
    :param frame: Imagen de OpenCV donde se dibujará el texto.
    :param text: El texto que se quiere mostrar (sin el símbolo).
    :param position: Coordenadas donde empezar a dibujar el texto (x, y).
    :param symbol: El símbolo a dibujar (por ejemplo, "✓").
    :param font_size: Tamaño de la fuente para el texto.
    :param font_path: Ruta de la fuente (debe soportar símbolos).
    :param text_color: Color del texto (en formato BGR).
    :param symbol_color: Color del símbolo (en formato BGR).
    :param text_thickness: Grosor del texto (simulado).
    :return: Imagen con el texto y símbolo dibujados.
    """
    # Convertir de OpenCV a formato PIL
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # Crear un objeto de dibujo en PIL
    draw = ImageDraw.Draw(pil_img)

    # Cargar la fuente
    font = ImageFont.truetype(font_path, font_size)

    # Dibujar el texto con grosor (contorno)
    for offset_x in range(-text_thickness, text_thickness + 1):
        for offset_y in range(-text_thickness, text_thickness + 1):
            if offset_x != 0 or offset_y != 0:
                draw.text((position[0] + offset_x, position[1] + offset_y), text, font=font, fill=text_color)

    # Dibujar el texto principal (para que quede nítido encima del contorno)
    draw.text(position, text, font=font, fill=text_color)

    # Si hay un símbolo, dibujamos el símbolo con un color diferente
    if symbol:
        # Calcular el tamaño del texto con textbbox() para obtener el ancho
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]  # Ancho del texto

        # Ajustamos la posición del símbolo (desplazamos un poco a la derecha si es necesario)
        symbol_position = (position[0] + text_width, position[1] - position_symbol)
        
        # Si se especifica un tamaño de fuente para el símbolo, lo usamos
        if symbol_font_size:
            symbol_font = ImageFont.truetype(font_path, symbol_font_size)
        else:
            symbol_font = font  # Usar el tamaño de fuente original para el símbolo

        # Dibujar el símbolo con el mismo grosor
        for offset_x in range(-text_thickness, text_thickness + 1):
            for offset_y in range(-text_thickness, text_thickness + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text((symbol_position[0] + offset_x, symbol_position[1] + offset_y), symbol, font=symbol_font, fill=symbol_color)

        # Dibujar el símbolo principal (nítido)
        draw.text(symbol_position, symbol, font=symbol_font, fill=symbol_color)

    # Convertir de nuevo a OpenCV
    frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    return frame

def draw_background(frame, position, width, height, color):
    x, y = position
    cv2.rectangle(frame, (x, y), (x + width, y + height), color, -1)
    return frame