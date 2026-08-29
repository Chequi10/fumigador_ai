#!/bin/bash

# Coordenadas iniciales (centro del círculo en Pergamino)
centro_latitud=-33.8937
centro_longitud=-60.5716

# Parámetros del círculo
radio_metros=100  # Radio del círculo en metros
velocidad=0.0
angulo=0  # Ángulo inicial

# Función para calcular el incremento en latitud y longitud en función de los metros
calcular_incremento_lat_long() {
  metros=$1
  lat_rad=$(echo "$centro_latitud * 3.14159265359 / 180" | bc -l)
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

# Calculamos los incrementos correspondientes al radio
read radio_lat radio_lon < <(calcular_incremento_lat_long $radio_metros)

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

  # Calculamos la posición sobre el círculo
  radianes=$(echo "$angulo * 3.14159265359 / 180" | bc -l)
  latitud=$(echo "$centro_latitud + $radio_lat * s($radianes)" | bc -l)
  longitud=$(echo "$centro_longitud + $radio_lon * c($radianes)" | bc -l)

  # Convertimos a NMEA
  read lat_nmea lat_dir <<< $(decimal_a_nmea $latitud "lat")
  read lon_nmea lon_dir <<< $(decimal_a_nmea $longitud "lon")

  # Trama GPRMC
  trama="\$GPRMC,$hora,A,$lat_nmea,$lat_dir,$lon_nmea,$lon_dir,$velocidad,084.4,$fecha_actual,003.1,W*6A"

  echo "$trama" > /dev/pts/5
  echo "$trama"

  # Avanzamos en el ángulo
  angulo=$((angulo + 5))
  if (( angulo >= 360 )); then
    angulo=0
  fi

  # Esperamos 1 segundo
  sleep 1
done
