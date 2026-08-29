# estado_global.py

campo_seleccionado = 1
cultivo_seleccionado = 1
tratamiento_seleccionado = 1  # ← se actualiza desde la interfaz
tratamiento = "emergente"     # ← texto final que usará el diagnóstico

# estado_global.py
autopilot_habilitado = False   # arranca habilitado (cambialo si querés)
valvulas_habilitadas = False   # permiso para escribir GPIO
modo_manual_valvulas = False   # <- NUEVO
# estado_global.py
blink_valvulas_s = 0.10   # 100 ms (valor inicial)
presion_coef = 1.00


litros_por_hectarea = 300
presion_trabajo = 0.2
caudal_actual = 0.3       # L/min  ← simulado coherente con baja presión
caudal_esperado = 0.15     # L/min  ← igual para evitar desvío
umbral_caudal = 0.1        # 10% tolerancia
umbral_presion = 0.1       # 10% tolerancia

  # Guardar en estado_global o donde uses los valores
caudal_total_esperado=1


# --- Boquilla seleccionada (disponible globalmente) ---
# Código de boquilla (ej: "XR11002", "AI11003")
boquilla = ""                 # str

# Micraje de la boquilla en micras (se actualiza desde la GUI)
micras_seleccionadas = 0.0    # float, ej: 250.0

# Caudal nominal de la boquilla a 3 bar (L/min) según tabla de selección
caudal_nominal_boquilla = 0.0 # float, ej: 0.76

# Color visual de la boquilla (para UI)
color_boquilla = "#000000"    # str, ej: "#0000FF"

# Valor calculado: cuánto daría esa boquilla a la presión de trabajo actual
# (lo carga solve.py cuando calcula Q = K*sqrt(P))
caudal_por_pico_boquilla = None  # float | None

# Valor calculado: presión necesaria para alcanzar el objetivo de L/ha
# (si lo calculás, podés publicarlo aquí para mostrar recomendación en la UI)
presion_requerida_para_objetivo = None  # float | None

# (Opcional) Diccionario global por si querés cargar toda la tabla una sola vez
# clave = código de boquilla, valor = dict con color/caudal_nominal_3bar/micraje
boquillas_datos = {}  # ejemplo: {"XR11002": {"color":"#0000FF","caudal":0.76,"micraje":250}}





tipo_maquina = 1
marca = 1
alto = 5
ancho = 1
largo = 15

altura_aplicacion = 65
ancho_botalon = 15
cant_secciones = 20 
sep_picos = 5
tipo_picos = 20


ancho_corte = 15
cant_surcos = 10
campo1 = 2
campo2 = 3
