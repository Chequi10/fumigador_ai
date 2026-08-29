import Jetson.GPIO as GPIO
import time

# Configuración del pin físico 7 (GPIO4)
PIN = 29
GPIO.setmode(GPIO.BOARD)   # Usamos numeración física de pines
GPIO.setup(PIN, GPIO.OUT)  # Configuramos el pin como salida

try:
    while True:
        GPIO.output(PIN, GPIO.HIGH)  # Encender LED
        print("LED encendido")
        time.sleep(1)

        GPIO.output(PIN, GPIO.LOW)   # Apagar LED
        print("LED apagado")
        time.sleep(1)

except KeyboardInterrupt:
    print("Programa interrumpido")

finally:
    GPIO.cleanup()  # Limpia configuración GPIO al salir
