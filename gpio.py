# gpio.py
import time
import RPi.GPIO as GPIO

class GPIOControl:
    _initialized = False
    _used_pins = set()

    def __init__(self, pin, mode=GPIO.OUT, pull=None):
        if not GPIOControl._initialized:
            GPIO.setmode(GPIO.BCM)
            GPIOControl._initialized = True

        self.pin = pin
        self.mode = mode

        if mode == GPIO.IN:
            if pull == "up":
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            elif pull == "down":
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            else:
                GPIO.setup(self.pin, GPIO.IN)
        else:
            GPIO.setup(self.pin, GPIO.OUT)

        GPIOControl._used_pins.add(self.pin)

    def turn_on(self):
        if self.mode == GPIO.OUT:
            GPIO.output(self.pin, GPIO.HIGH)

    def turn_off(self):
        if self.mode == GPIO.OUT:
            GPIO.output(self.pin, GPIO.LOW)

    def blink(self, delay=1):
        self.turn_on()
        start_time = time.time()
        time.sleep(delay)
        
        self.turn_off()
        time_on = time.time() - start_time
        print(f"\033[31m\n*********************************************************** {time_on:.4f} segundos\n\033[0m")
        
        

    def read(self):
        if self.mode == GPIO.IN:
            return GPIO.input(self.pin)
        raise RuntimeError("Pin no está configurado como entrada")

    @classmethod
    def cleanup_all(cls):
        GPIO.cleanup()
        cls._used_pins.clear()
        cls._initialized = False


        """# leer_pulsador.py

            def leer_pulsador():
                boton = GPIOControl(13, mode="IN", pull="up")  # Entrada con pull-up interno

                try:
                    while True:
                        estado = boton.read()
                        if estado == GPIO.LOW:
                            print("Botón PRESIONADO")
                        else:
                            print("Botón LIBERADO")
                        time.sleep(0.2)
                except KeyboardInterrupt:
                    print("Lectura interrumpida por el usuario")
                finally:
                    GPIOControl.cleanup_all()

        """