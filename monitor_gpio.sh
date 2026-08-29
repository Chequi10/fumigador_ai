#!/bin/bash
CHIP=gpiochip0   # Cambiá según corresponda
LINE=7           # Cambiá por la línea correcta del GPIO

while true; do
  VAL=$(gpioget $CHIP $LINE)
  echo "$(date '+%H:%M:%S') - GPIO $LINE = $VAL"
  sleep 0.5
done
