<?php
session_start();
if (!isset($_SESSION['usuario'])) {
    header("Location: index.php");
    exit();
}
?>
<!DOCTYPE html>
<html lang="es">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoreo Fumigador</title>

    <script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyAfvCvQYCVdNg3-RlbZNcvLoMCcv92xaP4&callback=initMap"
        async defer></script>

    <script>
        let map;
        let pathCoordinates = [];
        let markers = [];
        let positionCount = 5;
        let isUpdating = false;
        let zoomLevel = 2; // Zoom inicial
        let maxZoom = 18; // Zoom final
        let zoomInterval;

        function initMap() {
            map = new google.maps.Map(document.getElementById('map'), {
                center: { lat: -33.8937, lng: -60.5716 },
                mapTypeId: 'hybrid',
                zoom: zoomLevel
            });

            setInterval(getCoordinates, 3000);
        
            // Iniciar zoom progresivo
            zoomInterval = setInterval(() => {
                if (zoomLevel < maxZoom) {
                    zoomLevel++;
                    map.setZoom(zoomLevel);
                } else {
                    clearInterval(zoomInterval);
                }
            }, 500); // Ajusta el tiempo para cambiar el zoom más rápido o más lento
        }



        function updatePositionCount() {
            positionCount = parseInt(document.getElementById('positionCount').value) || 5;
            getCoordinates();
        }

        function toggleUpdate() {
            isUpdating = !isUpdating;
            const button = document.getElementById('toggleButton');
            button.textContent = isUpdating ? 'Detener Actualización' : 'Iniciar Actualización';
            if (isUpdating) updatePositionCount();
        }

        function getCoordinates() {
            if (!isUpdating) return;
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "get_coordinates.php", true);
            xhr.onreadystatechange = function () {
                if (xhr.readyState == 4 && xhr.status == 200) {
                    var coordenadas = JSON.parse(xhr.responseText);

                    if (coordenadas.length > 0) {
                        markers.forEach(marker => marker.setMap(null));
                        markers = [];
                        pathCoordinates = [];

                        let lastCoords = coordenadas.slice(-positionCount);
                        let lastCoord = lastCoords[lastCoords.length - 1];
                        
                        document.getElementById('idBox').value = lastCoord.id;
                        document.getElementById('latBox').value = lastCoord.lat;
                        document.getElementById('lngBox').value = lastCoord.lng;
                        document.getElementById('fechaBox').value = lastCoord.fecha;
                        document.getElementById('velBox').value = lastCoord.vel;
                        document.getElementById('tempBox').value = lastCoord.temperatura;
                        document.getElementById('humBox').value = lastCoord.humedad;
                        document.getElementById('velVientoBox').value = lastCoord.velocidad_viento;
                        document.getElementById('angVientoBox').value = lastCoord.angulo_viento;
                        document.getElementById('presionBox').value = lastCoord.presion;
                        
                        lastCoords.forEach(coord => {
                            let marker = new google.maps.Marker({
                                position: { lat: coord.lat, lng: coord.lng },
                                map: map,
                                title: `Id: ${coord.id}\nLatitud: ${coord.lat}\nLongitud: ${coord.lng}\nFecha: ${coord.fecha}\nVelocidad: ${coord.vel}\nTemperatura: ${coord.temperatura}\nHumedad: ${coord.humedad}\nVelocidad Viento: ${coord.velocidad_viento}\nÁngulo Viento: ${coord.angulo_viento}\nPresión: ${coord.presion}`
                            });
                            markers.push(marker);
                            pathCoordinates.push({ lat: coord.lat, lng: coord.lng });
                        });

                        map.setCenter({ lat: lastCoord.lat, lng: lastCoord.lng });

                        if (window.currentPath) {
                            window.currentPath.setMap(null);
                        }

                        window.currentPath = new google.maps.Polyline({
                            path: pathCoordinates,
                            geodesic: true,
                            strokeColor: '#FF0000',
                            strokeOpacity: 1.0,
                            strokeWeight: 2
                        });

                        window.currentPath.setMap(map);
                    }
                }
            };
            xhr.send();
        }

        setInterval(getCoordinates, 5000);
    </script>
    <style>
        .container {
            display: flex;
        }
        #map {
            height: 400px;
            width: 90%;
        }
        .data-box {
            width: 30%;
            padding-left: 10px;
        }
    </style>
<head>
    <style>
        body {
            background-color: green;
            color: rgb(47, 192, 218);
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        h1 {
            font-size: 36px; /* Aumenta el tamaño del texto */
            text-align: center;
            font-family: 'Arial', sans-serif; /* Cambia el tipo de letra */
            font-weight: bold; /* Hace el texto en negrita */
            color: rgb(255, 255, 255);
            margin-top: 10px; /* Espacio superior */
        }

        .container {
            display: flex;
            justify-content: space-between;
            padding: 20px;
            flex-wrap: wrap;
            position: relative; /* Esto hace que el contenedor sea el marco de referencia para la celda */
        }

        #map {
            width: 50%;
            height: 700px;
            background-color: lightgray;
        }
        .celda-posiciones {
            width: 100px;
            height: 30px;
            background-color: transparent;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            color: white;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-sizing: border-box;
            position: relative; /* Posición dentro del contenedor */
            top: 15px; /* Ajusta la distancia desde la parte superior del contenedor */
            left: 1px; /* Ajusta la distancia desde la izquierda del contenedor */

        }
              
        /* El contenedor de datos de las variables */
        .data-box {
            width: 100%;  /* Asegura que el contenedor ocupe todo el espacio disponible */
            max-width: 600px;  /* Limita el ancho máximo del contenedor */
            background-color:rgb(39, 41, 40);
            padding: 20px;
            border-radius: 8px;
            display: grid;
            grid-template-columns: 1fr 1fr;  /* Dos columnas iguales */
            gap: 5px;  /* Espacio entre las celdas */
            box-sizing: border-box;
            position: relative;
        }

        /* Etiquetas de las box o inputs */a
        .data-box label {
            display: block;
            font-size: 50px;
            margin-bottom: 5px;
            color: rgb(218, 47, 113);
            text-align: center; /* Centra la etiqueta */
        }

        /* Estilo para los inputs */
        input[type="text"], input[type="number"] {
            width: 100%;  /* El input ocupará todo el espacio de su contenedor */
            height: 100px;  /* Altura del input para que sea cuadrado */
            font-size: 30px;
            background-color:rgb(58, 57, 56);
            color: rgb(255, 255, 255);
            border: 2px rgb(5, 5, 5);
            border-radius: 5px;
            text-align: center;
            box-sizing: border-box; /* Asegura que el padding no afecte al ancho */
        }

        /* Cambia el fondo de los inputs solo lectura */
        input[type="text"]:read-only {
            background-color:rgb(58, 57, 56);
        }

        /* Estilo del botón */
        button {
            background-color: rgb(130, 218, 47);
            color: rgb(245, 86, 12);
            border: 2px solid orange;
            border-radius: 5px;
            padding: 10px;
            cursor: pointer;
            border-radius: 6px;
            width: 180px;
            height: 40px;
            
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            padding: 10px;
           
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            box-sizing: border-box;
            position: absolute; /* Posición dentro del contenedor */
            top: 3px; /* Ajusta la distancia desde la parte superior del contenedor */
            left: 90px; /* Ajusta la distancia desde la izquierda del contenedor */

        }  


        button:hover {
            background-color: darkorange;
        }

        /* Enlace */
        a {
            color: orange;
            text-decoration: none;
            font-size: 15px;
        }

        a:hover {
            text-decoration: underline;
        }

        .user-info {
            position: absolute;
            top: 10px;
            right: 10px;
            display: flex;
            flex-direction: column; /* Esto coloca los elementos uno debajo del otro */
            gap: 10px; /* Espacio entre los elementos */
            font-size: 18px;
            color: white;
        }

        .user-info a {
            color: orange;
            text-decoration: none;
            font-size: 18px;
            font-weight: bold;
        }

        .user-info a:hover {
            text-decoration: underline;
        }
    </style>
</head>

<body onload="initMap()">
    <h1>Monitoreo del Fumigador en tiempo real</h1>
    
      
    
<div>
    <div class="celda-posiciones">
        <input type="number" id="positionCount" value="5" min="1" />
        
        <button id="toggleButton" onclick="toggleUpdate()">Iniciar Actualización</button>   
    </div>     
    
    <div class="user-info">
        <label>Bienvenido, <?php echo $_SESSION['usuario']; ?> (<?php echo $_SESSION['modelo']; ?>)</label>
        <a href="logout.php">Cerrar sesión</a>
    </div>

    <div class="container">
        <div id="map"></div>
        <div class="data-box">
            
            <div>
                <label for="idBox">ID:</label>
                <input type="text" id="idBox" readonly>
            </div>
            <div>
                <label for="latBox">Latitud:</label>
                <input type="text" id="latBox" readonly>
            </div>
            <div>
                <label for="lngBox">Longitud:</label>
                <input type="text" id="lngBox" readonly>
            </div>
            <div>
                <label for="fechaBox">Fecha:</label>
                <input type="text" id="fechaBox" readonly>
            </div>
            <div>
                <label for="velBox">Velocidad:</label>
                <input type="text" id="velBox" readonly>
            </div>
            <div>
                <label for="tempBox">Temperatura:</label>
                <input type="text" id="tempBox" readonly>
            </div>
            <div>
                <label for="humBox">Humedad:</label>
                <input type="text" id="humBox" readonly>
            </div>
            <div>
                <label for="velVientoBox">Velocidad Viento:</label>
                <input type="text" id="velVientoBox" readonly>
            </div>
            <div>
                <label for="angVientoBox">Ángulo Viento:</label>
                <input type="text" id="angVientoBox" readonly>
            </div>
            <div>
                <label for="presionBox">Presión:</label>
                <input type="text" id="presionBox" readonly>
            </div>
        </div>
    </div>
</body>







