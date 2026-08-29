from smbus2 import SMBus
import time

ADS1115_ADDRESS = 0x48
ADS1115_POINTER_CONVERT = 0x00
ADS1115_POINTER_CONFIG = 0x01

# Configuración para una lectura de AIN0 (A0) en modo single-shot
CONFIG = 0b1100000110000011
# Bits:
# [15] OS=1 (iniciar conversión)
# [14:12] MUX=100 (AIN0 vs GND)
# [11:9] PGA=001 (±4.096 V)
# [8] MODE=1 (single-shot)
# [7:5] DR=100 (128 SPS)
# [4:0] Comparator off

def leer_ads1115():
    with SMBus(1) as bus:
        # Escribir la configuración
        config_high = (CONFIG >> 8) & 0xFF
        config_low = CONFIG & 0xFF
        bus.write_i2c_block_data(ADS1115_ADDRESS, ADS1115_POINTER_CONFIG, [config_high, config_low])
        
        # Esperar que termine la conversión (tiempo mínimo 8 ms para 128 SPS)
        time.sleep(0.01)
        
        # Leer los 2 bytes de resultado
        data = bus.read_i2c_block_data(ADS1115_ADDRESS, ADS1115_POINTER_CONVERT, 2)
        raw_adc = (data[0] << 8) | data[1]

        # Convertir a valor con signo
        if raw_adc > 0x7FFF:
            raw_adc -= 0x10000

        # Convertir a voltaje (ganancia ±4.096 V → 1 bit = 125 µV)
        voltage = raw_adc * 4.096 / 32768.0
        print(f"Lectura: {raw_adc} | Voltaje: {voltage:.4f} V")

if __name__ == "__main__":
    while True:
        leer_ads1115()
        time.sleep(1)
