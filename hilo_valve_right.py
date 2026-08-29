import threading
import time
import Jetson.GPIO as GPIO
from gpio import GPIOControl
from eventos_globales import evento_valvula_derecha
import estado_global



semaforo = threading.Semaphore(1)

def Threads_valvula_derecha():
    from hilo_visioqt1 import evento_valvula_derecha
    led_gpio = GPIOControl(pin=5, mode=GPIO.OUT, pull=None)  # Usa el pin GPIO 11(Físicamente es el 31)
    led_gpio.turn_off()
    try:
        while True:
            # Comprobamos si el evento ha sido activado.
            if evento_valvula_derecha.is_set():
                # Si el evento está activado, comienza la tarea
                t = float(getattr(estado_global, "blink_valvulas_s", 0.10))
                t = max(0.01, min(t, 2.0))  # límites de seguridad
             
                
                led_gpio.blink(t)
               
                

                semaforo.release()

                # Limpiar el evento después de realizar la tarea
                evento_valvula_derecha.clear()
            
            else:
                # Si el evento no está activado, podemos dormir por un corto tiempo para evitar
                # que el hilo consuma mucho CPU sin hacer nada.
                #print("[DEBUG] Esperando evento...")
                time.sleep(0.1)

    except Exception as e:
        print(f"[ERROR] En hilo de válvula derecha: {e}")