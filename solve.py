import math
import threading
from hilo_email import send_email
from hilo_adc import lector_ads1115
from adc_shared import datos_adc, lock_adc
import queue
import estado_global

boquillas = {
    "azul XR11002": {1.5: 250, 2: 220, 3: 180},
    "roja AI11003": {2: 400, 3: 350, 4: 300},
    "amarilla TT110015": {1.5: 200, 2: 180, 3: 150}
}


def procesador(cola, stop_event):
    while not stop_event.is_set():
        try:
            datos = cola.get(timeout=1.0)
            with lock_adc:
                datos_adc.clear()
                datos_adc.update(datos)
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[Procesador] ⚠️ Error inesperado: {e}")
    print("[Procesador] 🛑 Hilo detenido.")


def all_data(datos_combinados):
    ## Obtener datos del ADC protegidos por lock
    with lock_adc:
        bateria = datos_adc.get('bateria', 0)
         # presión cruda leída desde ADC
        presion_actual_cruda = datos_adc.get('presion_actual', 0)

        # coeficiente de corrección configurable
        coef_presion = float(getattr(estado_global, 'presion_coef', 1.00))

        # presión corregida
        presion_actual = presion_actual_cruda * coef_presion
        caudal_actual = 1.3  # datos_adc.get('caudal_actual', 0)
        flujometro = datos_adc.get('flujometro', 0)

    (id_dato, latitud, longitud, rumbo, fecha, velocidad_tractor,
     temperatura, humedad_relativa, velocidad_viento, angulo_viento, presion) = datos_combinados
   

    
    def evaluar_caudal():
        """
        Evalúa el caudal actual respecto al esperado (según la boquilla, presión de trabajo y cantidad de picos).
        Devuelve un puntaje (0 a 100) y un mensaje de diagnóstico claro para el operario.
        """

        caudal_actual = getattr(estado_global, 'caudal_actual', 0)
        caudal_esperado = getattr(estado_global, 'caudal_esperado', 0)
        presion_trabajo = getattr(estado_global, 'presion_trabajo', 0)
        presion_requerida = getattr(estado_global, 'presion_requerida_para_objetivo', None)
        umbral = getattr(estado_global, 'umbral_caudal', 0.1)  # 10% por defecto

        boquilla = getattr(estado_global, 'boquilla', None)
        caudal_nominal = getattr(estado_global, 'caudal_nominal_boquilla', None)
        cantidad_picos = getattr(estado_global, 'tipo_picos', 20)
        litros_por_hectarea = getattr(estado_global, 'litros_por_hectarea', 100)

        # Tabla de boquillas (a 3 bar)
        datos_boquillas = [
            ["#0000FF", "XR11002", 0.76, 250],
            ["#FF0000", "XR11003", 1.14, 300],
            ["#00FF00", "XR110022215", 0.57, 200],
            ["#FFFF00", "AI11004", 1.51, 400],
            ["#EE82EE", "XR11005", 1.89, 450],
            ["#FFA500", "AI11006", 2.27, 500],
            ["#8B4513", "XR11001", 0.38, 150],
            ["#808080", "AI110025", 0.95, 275],
            ["#000000", "XR110035", 1.32, 325],
            ["#FFFFFF", "AI110045", 1.70, 425],
            ["#FFC0CB", "XR110055", 2.08, 475],
            ["#ADD8E6", "AI110065", 2.46, 525],
            ["#32CD32", "XR110075", 2.84, 575],
            ["#8B0000", "AI110085", 3.22, 625]
        ]

        # --- Validaciones iniciales ---
        if not boquilla or caudal_esperado <= 0 or presion_trabajo <= 0:
            return 0, "Datos insuficientes para evaluar caudal"

        # --- Calcular desvío porcentual ---
        desvio = abs(caudal_actual - caudal_esperado) / caudal_esperado * 100

        # --- Evaluar desvío del caudal ---
        if desvio <= 5:
            score = 100
            mensaje = f"✅ Caudal correcto ({boquilla}) a {presion_trabajo:.1f} bar"
        elif desvio <= 15:
            # Penalización progresiva suave
            score = 100 - (desvio - 5) * 5   # cada 1% fuera del rango quita 5 puntos
            mensaje = f"⚠️ Caudal con leve desvío ({desvio:+.1f}%)"
        elif desvio <= 40:
            # Penalización más fuerte
            score = 50 - (desvio - 15) * 2   # baja más rápido si el error es grande
            mensaje = f"❌ Caudal fuera de rango ({desvio:+.1f}%)"
        else:
            score = 0
            mensaje = f"❌ Caudal crítico ({desvio:+.1f}%)"

        # --- Limitar el score entre 0 y 100 ---
        score = max(0, min(100, score))

        # --- Ajuste adicional por presión no ideal ---
        if presion_requerida:
            diff_presion = abs(presion_trabajo - presion_requerida)
            if diff_presion > 0.5:
                mensaje += f" | 💡 Recomendado: {presion_requerida:.1f} bar para L/ha objetivo"

        # --- Cálculo de caudal total (esperado vs real) ---
        caudal_total_esperado = caudal_esperado * cantidad_picos
        caudal_total_real = caudal_actual * cantidad_picos

        # --- Penalización física por boquilla insuficiente ---
        sugerencia = ""
        if caudal_nominal and caudal_esperado > caudal_nominal * 1.1:
            exceso_fisico = ((caudal_esperado / caudal_nominal) - 1) * 100
            penalizacion = min(30, exceso_fisico * 0.3)
            score = max(0, score - penalizacion)

            # Buscar boquilla alternativa
            alternativa = None
            for color, codigo, caudal_nom, micraje in datos_boquillas:
                if caudal_nom >= caudal_esperado * 0.95:
                    alternativa = (codigo, caudal_nom, color)
                    break

            if alternativa:
                sugerencia = (
                    f"<br>💡 Sugerencia: usar boquilla <b>{alternativa[0]}</b> "
                    f"({alternativa[2]}) con caudal nominal {alternativa[1]:.2f} L/min a 3 bar."
                )

            mensaje += (
                f" ⚠️ El caudal esperado ({caudal_esperado:.2f} L/min) "
                f"supera el nominal ({caudal_nominal:.2f} L/min a 3 bar). "
                f"Penalización aplicada (-{penalizacion:.1f} puntos)."
                f"{sugerencia}"
            )

        # --- NUEVO BLOQUE: detección de boquilla grande o exceso de caudal ---
        if litros_por_hectarea < 150 and caudal_actual > caudal_esperado * 1.1:
            mensaje += (
                "<br>💡 <b>Boquilla posiblemente sobredimensionada</b>: "
                "para bajos litros por hectárea, el caudal esperado es pequeño, "
                "pero la boquilla entrega demasiado flujo.<br>"
                "👉 Sugerencia: usar una boquilla más chica o reducir presión para evitar sobreaplicación."
            )
            score = max(0, score - 15)

        # --- Mostrar resumen ---
        mensaje += (
            f"<br>📈 Boquillas totales: {cantidad_picos} "
            f"| Caudal total real: {caudal_total_real:.2f} L/min "
            f"| Esperado total: {caudal_total_esperado:.2f} L/min."
        )

        print(
            f"💧 [Caudal] actual={caudal_actual:.3f} L/min | "
            f"esperado={caudal_esperado:.3f} L/min | "
            f"boquilla={boquilla} | presión={presion_trabajo:.2f} bar | "
            f"score ajustado={score:.1f}"
        )

        return score, mensaje





    
    def calcular_punto_rocio(temperatura, humedad_relativa):
        a = 17.27
        b = 237.7
        alpha = (a * temperatura) / (b + temperatura) + math.log(humedad_relativa / 100)
        return (b * alpha) / (a - alpha)

    def calcular_bulbo_humedo(temperatura, humedad_relativa, presion=None, gamma_factor=1.28):
        T = float(temperatura)
        RH = float(humedad_relativa)
        RH = max(5.0, min(99.0, RH))

        def _es_buck_hpa(t_c):
            return 6.1121 * math.exp((18.678 - (t_c / 234.5)) * (t_c / (257.14 + t_c)))

        def _to_hpa(P):
            P = float(P)
            if 80000 <= P <= 120000:  # Pa
                return P / 100.0
            if 80 <= P <= 120:  # kPa
                return P * 10.0
            if 800 <= P <= 1200:  # hPa
                return P
            return P

        try:
            P_hPa = _to_hpa(presion if presion is not None else 1013.25)
        except Exception:
            P_hPa = 1013.25

        e_real = (RH / 100.0) * _es_buck_hpa(T)

        Tw = (T * math.atan(0.151977 * math.sqrt(RH + 8.313659))
              + math.atan(T + RH)
              - math.atan(RH - 1.676331)
              + 0.00391838 * (RH ** 1.5) * math.atan(0.023101 * RH)
              - 4.686035)

        for _ in range(60):
            es_tw = _es_buck_hpa(Tw)
            gamma = gamma_factor * 0.00066 * (1 + 0.00115 * Tw) * P_hPa
            f = es_tw - gamma * (T - Tw) - e_real
            h = 1e-3
            des = (_es_buck_hpa(Tw + h) - es_tw) / h
            df = des + gamma
            Tw_new = Tw - f / df
            if abs(Tw_new - Tw) < 1e-6:
                Tw = Tw_new
                break
            Tw = Tw_new
        return Tw

    def calcular_delta_t(temperatura, humedad_relativa, presion=None, redondear_a_025=True, gamma_factor=1.28):
        T = float(temperatura)
        Tw = calcular_bulbo_humedo(temperatura, humedad_relativa, presion, gamma_factor)
        dt = T - Tw
        return round(dt * 4) / 4.0 if redondear_a_025 else dt

    def calcular_humedad_absoluta(temperatura, humedad_relativa):
        presion_vapor = 6.112 * math.exp((17.62 * temperatura) / (243.12 + temperatura))
        humedad_abs = 216.7 * (humedad_relativa / 100 * presion_vapor) / (temperatura + 273.15)
        return humedad_abs

    def calcular_angulo_relativo(rumbo, angulo_viento):
        angulo_relativo = angulo_viento - rumbo
        return (angulo_relativo + 360) % 360

    def calcular_velocidad_aparente(velocidad_viento, velocidad_tractor, angulo_relativo_ajustado):
        return math.sqrt(
            velocidad_viento ** 2 + velocidad_tractor ** 2 +
            2 * velocidad_viento * velocidad_tractor * math.cos(math.radians(angulo_relativo_ajustado))
        )

    def estimar_evaporacion_segundos(temperatura, humedad_relativa, diametro_gota_micras):
        if diametro_gota_micras <= 0:
            return 0
        D = 2.5e-5
        rho = 1000
        d_m = diametro_gota_micras * 1e-6
        RH = humedad_relativa / 100.0
        return (rho * d_m ** 2) / (8 * D * (1 - RH))

    def estimar_deriva_real(velocidad_viento, altura_aplicacion, diametro_gota_micras):
        if diametro_gota_micras <= 0:
            return 0
        rho_agua = 1000
        rho_aire = 1.225
        g = 9.81
        d = diametro_gota_micras * 1e-6
        Cd = 0.47
        A = math.pi * (d / 2) ** 2
        m = (4 / 3) * math.pi * (d / 2) ** 3 * rho_agua
        v_terminal = math.sqrt((2 * m * g) / (rho_aire * A * Cd))
        t_caida = altura_aplicacion / v_terminal
        return velocidad_viento * t_caida

    def detectar_taponamiento(caudal_actual, presion_actual, caudal_esperado, presion_esperada,
                          umbral_caudal=0.1, umbral_presion=0.1):
        """Evalúa taponamiento y devuelve un código como antes (0–4)."""
        if caudal_esperado <= 0 or presion_esperada <= 0:
            return 3  # normal por defecto

        diff_caudal = abs(caudal_actual - caudal_esperado) / caudal_esperado
        diff_presion = abs(presion_actual - presion_esperada) / presion_esperada

        desviacion = (diff_caudal + diff_presion) / 2

        # Clasificación progresiva compatible con tus códigos actuales
        if desviacion < 0.05:
            return 3   # normal
        elif desviacion < 0.15:
            return 2   # leve desviación
        elif desviacion < 0.3:
            return 1   # tapon parcial
        else:
            return 0   # tapon grave


    def calcular_calidad_fumigacion(delta_t, velocidad_aparente, deriva, evaporacion, taponamiento, caudal_score, temperatura=None, humedad_relativa=None):
        """
        Calcula el Índice de Calidad de Fumigación (ICF) considerando 8 variables:
        ΔT, velocidad aparente, deriva, evaporación, taponamiento, caudal, temperatura y humedad relativa.
        """
        # Pesos equilibrados entre 8 factores
        peso = 1 / 8

        # --- ΔT ---
        delta_t_score = max(0, min(100, 100 - abs(delta_t - 5) * 20))

        # --- Velocidad ---
        velocidad_score = max(0, min(100, 100 - abs(velocidad_aparente - 6.5) * 15))

        # --- Deriva ---
        deriva_score = max(0, min(100, 100 - deriva * 20))

        # --- Evaporación (escala discreta coherente con GUI) ---
        if evaporacion < 2:
            evaporacion_score = 30
        elif 2 <= evaporacion < 3:
            evaporacion_score = 50
        elif 3 <= evaporacion <= 5:
            evaporacion_score = 80
        elif 5 < evaporacion <= 7:
            evaporacion_score = 60
        else:
            evaporacion_score = 40

        # --- Taponamiento ---
        taponamiento_score = {0: 30, 1: 50, 2: 50, 3: 100}.get(taponamiento, 50)

        # --- Caudal ---
        caudal_score = max(0, min(100, caudal_score))

        # --- Temperatura (nuevo) ---
        if temperatura is not None:
            if temperatura > 35 or temperatura < 5:
                temp_score = 0
            elif temperatura > 28:
                temp_score = max(0, 100 - (temperatura - 28) * 5)
            else:
                temp_score = 100
        else:
            temp_score = 50  # valor neutro si no hay dato

        # --- Humedad relativa (nuevo) ---
        if humedad_relativa is not None:
            if humedad_relativa >= 70:
                hum_score = 100
            elif humedad_relativa >= 50:
                hum_score = 75 + (humedad_relativa - 50) * 1.25
            elif humedad_relativa >= 30:
                hum_score = 25 + (humedad_relativa - 30) * 2.5
            else:
                hum_score = 0
        else:
            hum_score = 50  # valor neutro si no hay dato

        # --- Aportes individuales al ICF (ponderados) ---
        aportes = {
            "ΔT": delta_t_score * peso,
            "Velocidad": velocidad_score * peso,
            "Deriva": deriva_score * peso,
            "Evaporación": evaporacion_score * peso,
            "Taponamiento": taponamiento_score * peso,
            "Caudal": caudal_score * peso,
            "Temperatura": temp_score * peso,
            "Humedad": hum_score * peso
        }

        icf = sum(aportes.values())

        # --- Mostrar resultados en consola ---
        print("\n📊 [DETALLE ICF CON APORTES INDIVIDUALES]")
        print(f"ΔTscore={delta_t_score:.1f} (ΔTreal={delta_t:.2f}°C) → aporta {aportes['ΔT']:.2f}")
        print(f"Velscore={velocidad_score:.1f} (Velreal={velocidad_aparente:.2f} km/h) → aporta {aportes['Velocidad']:.2f}")
        print(f"DerivaScore={deriva_score:.1f} → aporta {aportes['Deriva']:.2f}")
        print(f"EvaporacionScore={evaporacion_score:.1f} (EvapSeg={evaporacion:.2f} s) → aporta {aportes['Evaporación']:.2f}")
        print(f"TaponamientoScore={taponamiento_score:.1f} → aporta {aportes['Taponamiento']:.2f}")
        print(f"CaudalScore={caudal_score:.1f} → aporta {aportes['Caudal']:.2f}")
        print(f"TempScore={temp_score:.1f} (T={temperatura}°C) → aporta {aportes['Temperatura']:.2f}")
        print(f"HumedadScore={hum_score:.1f} (HR={humedad_relativa}%) → aporta {aportes['Humedad']:.2f}")
        print("--------------------------------------------------")
        print(f"✅ ICF total (con T y HR): {round(icf, 1)}")
        print(f"🔹 Suma de aportes = {sum(aportes.values()):.2f} (debería dar 100 si todos están en 100)\n")

        return round(icf, 1)




    

       
    # --- Cálculo del caudal esperado ---
    # Parámetros configurables del equipo
    litros_por_hectarea = getattr(estado_global, 'litros_por_hectarea', 100)  # L/ha
    ancho_botalon = getattr(estado_global, 'ancho_botalon', 20)              # metros
    cantidad_picos = getattr(estado_global, 'tipo_picos', 20)              # cantidad de boquillas
    altura_aplicacion = estado_global.altura_aplicacion
    caudal_esperado = estado_global.caudal_esperado
    presion_esperada = estado_global.presion_trabajo
    diametro_gota_micras = estado_global.micras_seleccionadas

    # Evitar división por cero
    if velocidad_tractor > 0 and cantidad_picos > 0:
        # Fórmula de caudal total (L/min)
        caudal_total_esperado = (velocidad_tractor * ancho_botalon * litros_por_hectarea) / 600
        # Caudal por boquilla (L/min)
        caudal_esperado = caudal_total_esperado / cantidad_picos
    else:
        caudal_total_esperado = 0
        caudal_esperado = 0

    estado_global.caudal_actual = caudal_actual
    estado_global.caudal_esperado = caudal_esperado

    punto_rocio = calcular_punto_rocio(temperatura, humedad_relativa)
    delta_t = calcular_delta_t(temperatura, humedad_relativa, presion=1013.25)
    humedad_absoluta = calcular_humedad_absoluta(temperatura, humedad_relativa)
    angulo_relativo_ajustado = calcular_angulo_relativo(rumbo, angulo_viento)
    velocidad_aparente = calcular_velocidad_aparente(velocidad_viento, velocidad_tractor, angulo_relativo_ajustado)
    taponamiento = detectar_taponamiento(caudal_actual, presion_actual, caudal_esperado, presion_esperada)
    deriva = estimar_deriva_real(velocidad_viento, altura_aplicacion, diametro_gota_micras)
   
   
   

        
    # --- Ajuste de diámetro de gota según presión ---
    if presion_actual > 0 and estado_global.presion_trabajo > 0:
        diametro_gota_ajustado = diametro_gota_micras * math.sqrt(estado_global.presion_trabajo / presion_actual)
    else:
        diametro_gota_ajustado = diametro_gota_micras

    # --- Calcular evaporación instantánea ---
    evaporacion_nueva = estimar_evaporacion_segundos(
        temperatura,
        humedad_relativa,
        diametro_gota_ajustado
    )

    # --- Inicializar si no existe ---
    if not hasattr(estado_global, "evap_suavizada"):
        estado_global.evap_suavizada = evaporacion_nueva

    # --- Filtro adaptativo según cambio relativo ---
    dif = abs(evaporacion_nueva - estado_global.evap_suavizada)
    rel = dif / max(evaporacion_nueva, 1)

    # si cambia mucho → responde rápido; si es estable → filtra más
    if rel > 0.3:
        alpha = 0.7   # respuesta rápida (70% del cambio nuevo)
    elif rel > 0.1:
        alpha = 0.5   # respuesta media
    else:
        alpha = 0.3   # respuesta suave

    # --- Actualizar suavizado ---
    estado_global.evap_suavizada = (
        (1 - alpha) * estado_global.evap_suavizada + alpha * evaporacion_nueva
    )
    evaporacion = estado_global.evap_suavizada


    score_caudal, mensaje_caudal = evaluar_caudal()
    print(f"💧 Caudal actual={estado_global.caudal_actual:.3f} | "
      f"esperado={estado_global.caudal_esperado:.3f} | "
      f"Score={score_caudal:.1f} | Mensaje={mensaje_caudal}")

    estado = calcular_calidad_fumigacion(
        delta_t,
        velocidad_aparente,
        deriva,
        evaporacion,
        taponamiento,
        score_caudal,
        temperatura,
        humedad_relativa
    )


    # --- Scores base ---
    delta_t_score = max(0, min(100, 100 - abs(delta_t - 5) * 20))
    velocidad_score = max(0, min(100, 100 - abs(velocidad_aparente - 6.5) * 15))
    deriva_score = max(0, min(100, 100 - deriva * 20))

    # ✅ Definimos evaporacion_score en este alcance con la fórmula correcta
    # ✅ Definimos evaporacion_score con la misma escala discreta que el ICF
    if evaporacion < 2:
        evaporacion_score = 30
    elif 2 <= evaporacion < 3:
        evaporacion_score = 50
    elif 3 <= evaporacion <= 5:
        evaporacion_score = 80
    elif 5 < evaporacion <= 7:
        evaporacion_score = 60
    else:
        evaporacion_score = 40

    score_evap_cod = int(round(evaporacion_score))


    taponamiento_score = {0: 30, 1: 50, 2: 50, 3: 100}.get(taponamiento, 50)

    

    if temperatura > 35 or temperatura < 5:
        score_temp_cod = 0
    elif temperatura > 28:
        score_temp_cod = int(round(max(0, 100 - (temperatura - 28) * 5)))
    else:
        score_temp_cod = 100

    tratamiento_texto = str(estado_global.tratamiento).lower() if hasattr(estado_global, 'tratamiento') else ""
    if "pre" in tratamiento_texto:
        if humedad_relativa >= 60:
            score_hum_cod = 100
        elif humedad_relativa >= 40:
            score_hum_cod = int(round(60 + (humedad_relativa - 40) * 2))
        else:
            score_hum_cod = 0
    else:
        if humedad_relativa >= 70:
            score_hum_cod = 100
        elif humedad_relativa >= 50:
            score_hum_cod = int(round(75 + (humedad_relativa - 50) * 1.25))
        elif humedad_relativa >= 30:
            score_hum_cod = int(round(25 + (humedad_relativa - 30) * 2.5))
        else:
            score_hum_cod = 0
    score_hum_cod = int(round(score_hum_cod))

  


    # --- Enviar TODOS los códigos y scores ---
    codigos_con_score = []
    codigos_todos = {
        1: delta_t_score,
        3: velocidad_score,
        5: deriva_score,
        6: score_evap_cod,
        7: taponamiento_score,
        8: score_caudal,       # ← nuevo código para caudal
        10: score_temp_cod,
        11: score_hum_cod
    }

    for codigo, score in codigos_todos.items():
        codigos_con_score.append(f"{codigo}{int(round(score * 10)):04d}")
        #codigos_con_score.append(f"{codigo}{int(score * 10 + 0.5):04d}")


    condiciones = ",".join(codigos_con_score)

    print(f"📊 Enviando TODOS los códigos: {condiciones}")
    print(
        f"📡 Datos actualizados:\n"
        f"   ├─ Litros por hectárea: {litros_por_hectarea:.1f} L/ha\n"
        f"   ├─ Velocidad tractor: {velocidad_tractor:.2f} km/h\n"
        f"   ├─ Caudal esperado por boquilla: {caudal_esperado:.3f} L/min\n"
        f"   ├─ Caudal total esperado: {caudal_total_esperado:.3f} L/min\n"
        f"   └─ Caudal actual: {caudal_actual:.3f} L/min\n"
        f"   └─ Cantidad de picos: {cantidad_picos:} \n"
    )



    total = datos_combinados + (
        round(punto_rocio, 3),
        round(humedad_absoluta, 3),
        round(angulo_relativo_ajustado, 3),
        round(velocidad_aparente, 3),
        round(altura_aplicacion, 3),
        round(delta_t, 3),
        round(caudal_actual, 3),
        round(flujometro, 3),
        taponamiento,
        round(deriva, 3),
        round(evaporacion, 3),
        condiciones,
        round(estado_global.ancho, 3),
        round(estado_global.largo, 3),
        round(diametro_gota_micras, 3),
        estado_global.boquilla,
        round(presion_actual, 3),
        round(bateria, 3),
        round(estado, 3)
    )

    return total
