import gpiod
import time

chip = gpiod.Chip("gpiochip0")
line_offset = 17  # Cambia por el offset correcto para tu GPIO
line = chip.get_line(line_offset)

line.request(consumer="test", type=gpiod.LINE_REQ_DIR_OUT)

try:
    estado = 0
    while True:
        estado = 1 - estado  # Alterna entre 0 y 1
        line.set_value(estado)
        print(f"GPIO {line_offset} estado: {estado}")
        time.sleep(1)  # Espera 1 segundo
except KeyboardInterrupt:
    print("Terminando...")

finally:
    line.release()

