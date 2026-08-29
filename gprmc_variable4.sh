#!/bin/bash

# Establecemos la hora inicial en formato HHMMSS
hora="000001"
velocidad=0.0

latitud=-33.8937
longitud=-60.5716



while true; do
  # Convertimos la hora HHMMSS a segundos desde medianoche (1970-01-01)
  hora_segundos=$((10#${hora:0:2} * 3600 + 10#${hora:2:2} * 60 + 10#${hora:4:2}))

  # Incrementamos en un segundo
  hora_segundos=$((hora_segundos + 1))

  # Convertimos los segundos de vuelta a formato HHMMSS
  hora=$(printf "%02d%02d%02d" $((hora_segundos / 3600)) $(((hora_segundos / 60) % 60)) $((hora_segundos % 60)))

  # Incrementamos la velocidad en 0.5 km/h
  velocidad=$(echo "$velocidad + 0.5" | bc)

  # Opcional: Reiniciar la velocidad si llega a 100 km/h
  if (( $(echo "$velocidad > 100" | bc -l) )); then
    velocidad=0.0
  fi

  # Creamos la trama GPRMC con la hora y velocidad actualizadas
  echo "\$GPRMC,$hora,A,3353.370,S,06034.320,W,$velocidad,084.4,250505,003.1,W*6A" > /dev/pts/5

  # Esperamos 1 segundo antes de la siguiente iteración
  sleep 1
done
