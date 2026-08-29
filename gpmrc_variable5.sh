#!/bin/bash

# Coordenadas iniciales (Pergamino)
latitud=-33.8937
longitud=-60.5716

# Parámetros para simular el movimiento
distancia_surco=10  # Avance en metros por iteración (10 metros)
longitud_max=10000  # Longitud del campo en metros
latitud_max=10000   # Ancho del campo en metros
movimiento_x=0
movimiento_y=0
cambio_direccion=0
velocidad=0.0

# Función para calcular el incremento en latitud y longitud en función de los metros
calcular_incremento_lat_long() {
  metros=$1
  lat_rad=$(echo "$latitud * 3.14159265359 / 180" | bc -l)
  latitud_incremento=$(echo "scale=8; $metros / 111320" | bc -l)
  longitud_incremento=$(echo "scale=8; $metros / (111320 * c($lat_rad))" | bc -l)
  echo "$latitud_incremento $longitud_incremento"
}

# Convierte coordenadas decimales a formato NMEA
decimal_a_nmea() {
  dec=$1
  tipo=$2  # 'lat' o 'lon'

  abs_dec=$(echo "$dec" | sed 's/^-//')
  grados=$(echo "$abs_dec" | cut -d. -f1)
  minutos=$(echo "scale=6; ($abs_dec - $grados) * 60" | bc)

  if [[ $tipo == "lat" ]]; then
    grados_fmt=$(printf "%02d" $grados)
    dir=$( (( $(echo "$dec < 0" | bc -l) )) && echo "S" || echo "N" )
  else
    grados_fmt=$(printf "%03d" $grados)
    dir=$( (( $(echo "$dec < 0" | bc -l) )) && echo "W" || echo "E" )
  fi

  minutos_fmt=$minutos
  echo "$grados_fmt$minutos_fmt $dir"
}

# Bucle principal
while true; do
  # Hora y fecha del sistema
  hora=$(date +"%H%M%S")
  fecha_actual=$(date +"%d%m%y")

  # Aumentamos la velocidad
  velocidad=$(echo "$velocidad + 0.5" | bc)
  if (( $(echo "$velocidad > 50" | bc -l) )); then
    velocidad=0.0
  fi

  # Movimiento en surcos
  if (( cambio_direccion == 0 )); then
    movimiento_x=$(echo "$movimiento_x + $distancia_surco" | bc)
    if (( $(echo "$movimiento_x >= $longitud_max" | bc -l) )); then
      movimiento_x=0
      cambio_direccion=1
    fi
  else
    movimiento_y=$(echo "$movimiento_y + $distancia_surco" | bc)
    if (( $(echo "$movimiento_y >= $latitud_max" | bc -l) )); then
      movimiento_y=0
      cambio_direccion=0
    fi
  fi

  # Calculamos incrementos
  read lat_inc lon_inc < <(calcular_incremento_lat_long $distancia_surco)

  latitud=$(echo "$latitud + $lat_inc" | bc)
  longitud=$(echo "$longitud + $lon_inc" | bc)

  # Convertimos a NMEA
  read lat_nmea lat_dir <<< $(decimal_a_nmea $latitud "lat")
  read lon_nmea lon_dir <<< $(decimal_a_nmea $longitud "lon")
  
  # Trama GPRMC
  trama="\$GPRMC,$hora,A,$lat_nmea,$lat_dir,$lon_nmea,$lon_dir,$velocidad,084.4,$fecha_actual,003.1,W*6A"
  
  echo "$trama" > /dev/pts/5
  echo "$trama"

  # Esperamos 1 segundo
  sleep 1
done
