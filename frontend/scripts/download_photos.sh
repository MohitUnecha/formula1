#!/bin/bash
cd /Users/mohitunecha/F1/frontend/public/images/drivers

BASE="https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers"

download() {
  local code=$1 folder=$2 file=$3
  local letter="${folder:0:1}"
  local url="${BASE}/${letter}/${folder}/${file}.png"
  echo -n "${code}... "
  local http_code=$(curl -s -o "${code}.png" -w "%{http_code}" "${url}")
  if [ "$http_code" = "200" ]; then
    local size=$(wc -c < "${code}.png" | tr -d ' ')
    echo "OK (${size} bytes)"
  else
    echo "FAIL (${http_code}), trying fallback..."
    rm -f "${code}.png"
  fi
}

download "VER" "MAXVER01_Max_Verstappen" "maxver01"
download "HAM" "LEWHAM01_Lewis_Hamilton" "lewham01"
download "LEC" "CHALEC01_Charles_Leclerc" "chalec01"
download "NOR" "LANNOR01_Lando_Norris" "lannor01"
download "PIA" "OSCPIA01_Oscar_Piastri" "oscpia01"
download "RUS" "GEORUS01_George_Russell" "georus01"
download "SAI" "CARSAR01_Carlos_Sainz" "carsar01"
download "ALO" "FERALO01_Fernando_Alonso" "feralo01"
download "STR" "LANSTR01_Lance_Stroll" "lanstr01"
download "GAS" "PIEGAS01_Pierre_Gasly" "piegas01"
download "OCO" "ESTOCO01_Esteban_Ocon" "estoco01"
download "ALB" "ALEALB01_Alexander_Albon" "alealb01"
download "TSU" "YUKTSUN01_Yuki_Tsunoda" "yuktsun01"  
download "HUL" "NICHUL01_Nico_Hulkenberg" "nichul01"
download "MAG" "KEVMAG01_Kevin_Magnussen" "kevmag01"
download "LAW" "LIALAW01_Liam_Lawson" "lialaw01"
download "BEA" "OLIBEA01_Oliver_Bearman" "olibea01"
download "ANT" "KIMAN01_Kimi_Antonelli" "kiman01"
download "BOR" "GABORT01_Gabriel_Bortoleto" "gabort01"
download "HAD" "ISAHAD01_Isack_Hadjar" "isahad01"
download "DOO" "JACDOO01_Jack_Doohan" "jacdoo01"
download "COL" "FRACOL01_Franco_Colapinto" "fracol01"
download "PER" "SERPER01_Sergio_Perez" "serper01"
download "BOT" "VALBOT01_Valtteri_Bottas" "valbot01"

echo ""
echo "Downloaded files:"
ls -la *.png 2>/dev/null
echo "Total: $(ls *.png 2>/dev/null | wc -l | tr -d ' ') photos"
