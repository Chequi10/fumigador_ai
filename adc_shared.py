# adc_shared.py
import threading

datos_adc = {}
lock_adc = threading.Lock()