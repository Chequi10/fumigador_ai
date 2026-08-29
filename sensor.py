from smbus2 import SMBus
import time

ADS1115_ADDRESS = 0x48  # Dirección por defecto del ADS1115
CONFIG_REGISTER = 0x01
CONVERSION_REGISTER = 0x00

class ADS1115:
    def __init__(self, bus_id=1):
        try:
            self.bus = SMBus(bus_id)
            self.addr = ADS1115_ADDRESS
            print("ADS1115 detectado (o al menos el bus I2C está activo)")
        except Exception as e:
            print("No se pudo acceder al bus I2C.")
            print(f"Detalle: {e}")
            self.bus = None

    def leer_canal(self, canal=0):
        if self.bus is None:
            print("Bus I2C no disponible.")
            return None

        if canal < 0 or canal > 3:
            raise ValueError("Canal debe estar entre 0 y 3")

        # Configurar canal (solo lectura simple, sin modo continuo)
        mux = 0x4000 + (canal << 12)  # AINx vs GND
        config = 0x8000 | mux | 0x0083  # 128SPS, single-shot

        try:
            self.bus.write_i2c_block_data(self.addr, CONFIG_REGISTER, [(config >> 8) & 0xFF, config & 0xFF])
            time.sleep(0.1)  # Espera para conversión

            result = self.bus.read_i2c_block_data(self.addr, CONVERSION_REGISTER, 2)
            raw_adc = (result[0] << 8) | result[1]
            if raw_adc > 0x7FFF:
                raw_adc -= 0x10000

            # Convertir a voltaje (ganancia por defecto ±4.096V → 0.125mV/LSB)
            voltaje = raw_adc * 0.125 / 1000
            return voltaje
        except Exception as e:
            print("Error al leer del ADS1115.")
            print(f"Detalle: {e}")
            return None

# --- Prueba simple ---
adc = ADS1115()

while True:
    v = adc.leer_canal(0)
    if v is not None:
        print(f"Voltaje: {v:.3f} V")
    else:
        print("⚠️  ADS1115 no conectado o sin respuesta.")

    time.sleep(1)
