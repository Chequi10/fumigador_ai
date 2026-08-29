from smbus2 import SMBus
import time
import queue

# Dirección I2C del ADS1115
ADS1115_ADDRESS = 0x48

# Registros del ADS1115
ADS1115_REG_CONVERT = 0x00
ADS1115_REG_CONFIG = 0x01

# Canales en modo single-ended
CHANNELS = {
    'bateria': 0x4000,       # AIN0 - voltaje batería
    'presion_actual': 0x7000,       # AIN3 - sensor 4–20 mA (ajustado según tu conexión)
    'caudal': 0x6000,        # AIN2 - sensor 4–20 mA
    'flujometro': 0x5000     # AIN1 - voltaje flujómetro
}

# Configuración base del ADS1115
CONFIG_BASE = 0x8183  # OS=1, PGA=±6.144V, single-shot, 128SPS, comp off

def leer_adc(bus, canal):
    """Lee un canal del ADS1115 y devuelve el voltaje medido (V)."""
    config = CONFIG_BASE | CHANNELS[canal]
    config_msb = (config >> 8) & 0xFF
    config_lsb = config & 0xFF
    try:
        bus.write_i2c_block_data(ADS1115_ADDRESS, ADS1115_REG_CONFIG, [config_msb, config_lsb])
        time.sleep(0.1)
        data = bus.read_i2c_block_data(ADS1115_ADDRESS, ADS1115_REG_CONVERT, 2)
        raw_adc = (data[0] << 8) | data[1]
        if raw_adc > 0x7FFF:
            raw_adc -= 0x10000
        voltaje = raw_adc * 6.144 / 32768.0  # PGA ±6.144V
        return voltaje
    except Exception as e:
        print(f"⚠️  Error al leer canal '{canal}': {e}")
        return None

def calcular_corriente(voltaje, resistencia=100):
    """Convierte el voltaje en corriente (mA) según el valor del shunt."""
    return (voltaje / resistencia) * 1000

def convertir_lineal_4_20ma(corriente_mA, escala_max):
    """Convierte una señal de 4–20 mA en un valor lineal entre 0 y escala_max."""
    return max(0, (corriente_mA - 4) * (escala_max / 16))

def lector_ads1115(cola, stop_event):
    """
    Hilo principal que lee los sensores conectados al ADS1115
    y envía los datos a la cola.
    """
    try:
        bus = SMBus(1)
        print("✅ Bus I2C inicializado.")
    except Exception as e:
        print(f"❌ No se pudo iniciar el bus I2C: {e}")
        return

    FACTOR_DIVISOR_BATERIA = 12.17 / 2.20  # ≈ 4.35
    resistencia_shunt = 100  # Ohm

    # --- Calibración automática del offset de presión ---
    OFFSET_PRESION_MANUAL = None  # Cambiá este valor si querés forzarlo (ej: -1.34)
    OFFSET_PRESION_AUTO = 0
    calibrado = False

    while not stop_event.is_set():
        try:
            v_bateria = leer_adc(bus, 'bateria')
            v_presion = leer_adc(bus, 'presion_actual')
            v_caudal = leer_adc(bus, 'caudal')
            v_flujometro = leer_adc(bus, 'flujometro')

            if None in (v_bateria, v_presion, v_caudal, v_flujometro):
                print("⏳ Datos incompletos, reintentando...")
                time.sleep(2)
                continue

            i_presion = calcular_corriente(v_presion, resistencia_shunt)
            i_caudal = calcular_corriente(v_caudal, resistencia_shunt)

            presion_actual = convertir_lineal_4_20ma(i_presion, escala_max=10)  # bar
            caudal_actual = convertir_lineal_4_20ma(i_caudal, escala_max=100)   # L/h

            # Calibración automática del offset al inicio
            if not calibrado:
                if OFFSET_PRESION_MANUAL is not None:
                    OFFSET_PRESION_AUTO = OFFSET_PRESION_MANUAL
                    print(f"🔧 Offset de presión configurado manualmente: {OFFSET_PRESION_AUTO:+.2f} bar")
                else:
                    OFFSET_PRESION_AUTO = -presion_actual
                    print(f"🔧 Offset de presión calibrado automáticamente: {OFFSET_PRESION_AUTO:+.2f} bar")
                calibrado = True

            # Aplicar offset de presión
            presion_actual += OFFSET_PRESION_AUTO
            if presion_actual < 0:
                presion_actual = 0

            v_bateria_real = v_bateria * FACTOR_DIVISOR_BATERIA

            datos = {
                'bateria': round(v_bateria_real, 2),
                'presion_actual': round(presion_actual, 2),
                'caudal_actual': round(caudal_actual, 2),
                'flujometro': round(v_flujometro, 3)
            }

            cola.put(datos)
            # print("📥 Datos capturados:", datos)

        except Exception as e:
            print(f"⚠️ Error en lector_ads1115: {e}")

        time.sleep(1)

    print("🛑 Hilo lector_ads1115 detenido.")
