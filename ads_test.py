from smbus2 import SMBus
import time

I2C_BUS = 1
ADDR = 0x48
REG_CONVERT = 0x00
REG_CONFIG  = 0x01

MUX = {'AIN0':0x4000,'AIN1':0x5000,'AIN2':0x6000,'AIN3':0x7000}
# OS=1 | PGA=±2.048V | single-shot | DR=860SPS | comp off
CONFIG_BASE = 0x87E3

def read_one(bus, mux_bits):
    cfg = CONFIG_BASE | mux_bits
    bus.write_i2c_block_data(ADDR, REG_CONFIG, [(cfg>>8)&0xFF, cfg&0xFF])
    # esperar conversión (OS=1 listo)
    for _ in range(50):
        rd = bus.read_i2c_block_data(ADDR, REG_CONFIG, 2)
        if rd[0] & 0x80:  # bit 15
            break
        time.sleep(0.002)
    d = bus.read_i2c_block_data(ADDR, REG_CONVERT, 2)
    raw = (d[0]<<8) | d[1]
    if raw > 0x7FFF:
        raw -= 0x10000
    v = raw * 2.048 / 32768.0
    return raw, v

if __name__ == "__main__":
    with SMBus(I2C_BUS) as bus:
        while True:
            print("\033[H\033[J", end="")
            print("Scan continuo ADS1115 (±2.048 V)\n")
            for ch in ['AIN0','AIN1','AIN2','AIN3']:
                raw, v = read_one(bus, MUX[ch])
                print(f"{ch}: raw={raw:6d}  V={v:6.3f}")
            time.sleep(0.3)
