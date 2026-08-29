import time
import Jetson.GPIO as GPIO

def pulso(pin, modo, nombre):
    GPIO.cleanup()
    GPIO.setmode(modo)
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    print(f"[OK] Prueba {nombre}: pin={pin} modo={'BOARD' if modo==GPIO.BOARD else 'BCM'}")
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(2)
    GPIO.output(pin, GPIO.LOW)
    time.sleep(1)

try:
    # 1) Prueba por PIN FISICO (recomendada)
    pulso(31, GPIO.BOARD, "PIN FISICO 31")
    pulso(29, GPIO.BOARD, "PIN FISICO 29")

    # 2) Prueba por BCM (por compatibilidad)
    pulso(6, GPIO.BCM, "BCM 6")
    pulso(5, GPIO.BCM, "BCM 5")

finally:
    GPIO.cleanup()
    print("[FIN] Listo")
