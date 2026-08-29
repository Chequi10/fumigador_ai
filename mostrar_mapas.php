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

    <!-- Agregar la API de Google Maps -->
    <script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyAfvCvQYCVdNg3-RlbZNcvLoMCcv92xaP4&callback=initMap"
        async defer></script>

    <script>
        let map;
        let pathCoordinates = [];
        let markers = [];
        let positionCount = 5; // Cantidad predeterminada de posiciones
        // Función para inicializar el mapa
        let isUpdating = false; // Variable para controlar si la actualización está habilitada

        function initMap() {
            // Crear un mapa centrado en una ubicación predeterminada
            map = new google.maps.Map(document.getElementById('map'), {
                zoom: 20,
                center: { lat: -33.8937, lng: -60.5716 },
                mapTypeId: 'hybrid' // Buenos Aires como ejemplo
            });

            // Llamar a la función de actualización de coordenadas cada 5 segundos
            setInterval(getCoordinates, 3000); // 5 segundos de intervalo
        }

        // Función para actualizar la cantidad de posiciones a mostrar
        function updatePositionCount() {
            positionCount = parseInt(document.getElementById('positionCount').value) || 5;
            getCoordinates(); // Actualiza las coordenadas inmediatamente
        }

        // Función para iniciar o detener la actualización cuando se presiona o se suelta el botón
        function toggleUpdate() {
            isUpdating = !isUpdating; // Cambiar el estado de la variable

            // Cambiar el texto del botón según el estado
            const button = document.getElementById('toggleButton');
            if (isUpdating) {
                button.textContent = 'Detener Actualización';
                updatePositionCount()
            } else {
                button.textContent = 'Iniciar Actualización';
            }
        }







        // Función para obtener las coordenadas más recientes de la base de datos mediante AJAX
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

                        // Actualizar el cuadro de coordenadas
                        let coordText = lastCoords.map(coord =>
                            `Id: ${coord.id}| Lat: ${coord.lat}| Long: ${coord.lng}| Fecha: ${coord.fecha}| Vel: ${coord.vel}| Temp: ${coord.temperatura}| Hum: ${coord.humedad}| Vel_Viento: ${coord.velocidad_viento}| Ang_viento: ${coord.angulo_viento}| Presion: ${coord.presion}`
                        ).join('\n');
                        const coordinatesBox = document.getElementById('coordinatesBox');
                        coordinatesBox.value = coordText;

                        // Hacer scroll hacia abajo automáticamente
                        coordinatesBox.scrollTop = coordinatesBox.scrollHeight;

                        lastCoords.forEach(coord => {
                        let marker = new google.maps.Marker({
                            position: { lat: coord.lat, lng: coord.lng },
                            map: null, // Inicialmente oculto
                            zoom: 20,
                            title: 'Id: ' + coord.id + '\nLatitud: ' + coord.lat + '\nLongitud: ' + coord.lng + '\nFecha: ' + coord.fecha + '\nVelocidad: ' + coord.vel + '\nTemperatura: ' + coord.temperatura + '\nHumedad: ' + coord.humedad + '\nVelocidad_Viento: ' + coord.velocidad_viento + '\nAngulo_viento: ' + coord.angulo_viento + '\nPresion: ' + coord.presion
                        });

                        // Mostrar marcador al pasar el mouse
                        google.maps.event.addListener(map, 'mousemove', function (event) {
                            const distance = google.maps.geometry.spherical.computeDistanceBetween(
                                new google.maps.LatLng(event.latLng.lat(), event.latLng.lng()),
                                new google.maps.LatLng(coord.lat, coord.lng)
                            );

                            if (distance < 10) { // Rango de 30 metros
                                marker.setMap(map);
                            } else {
                                marker.setMap(null);
                            }
                        });

                        markers.push(marker);
                        pathCoordinates.push({ lat: coord.lat, lng: coord.lng });
                    });

                        let lastCoord = lastCoords[lastCoords.length - 1];
                        map.setCenter({ id: lastCoord.id, lat: lastCoord.lat, lng: lastCoord.lng, fecha: lastCoord.fecha, vel: lastCoord.vel, temperatura: lastCoord.temperatura, humedad: lastCoord.humedad, velocidad_viento: lastCoord.velocidad_viento, angulo_viento: lastCoord.angulo_viento, presion: lastCoord.presion   });

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
        // Llamar a getCoordinates cada 5 segundos solo si la actualización está habilitada
        setInterval(getCoordinates, 5000);


    </script>
</head>

<body onload="initMap()">
    <h1 style="font-size: 12px;">Monitoreo del Fumigador en tiempo real</h1>
    <!-- Controles para seleccionar la cantidad de posiciones -->

    <div>
        <label for="positionCount">Cantidad de posiciones a mostrar:</label>
        <input type="number" id="positionCount" value="5" min="1" />
        <button id="toggleButton" onclick="toggleUpdate()">Iniciar Actualización</button>

        <!--<button onclick="updatePositionCount()">Actualizar</button>-->
        <label style="font-size: 12px;">Bienvenido, <?php echo $_SESSION['usuario']; ?>
            (<?php echo $_SESSION['modelo']; ?>)</label>

        <a href="logout.php">Cerrar sesión</a>

    </div>

    <!-- Mostrar el mapa -->
    <div id="map" style="height: 380px; width: 100%;"></div>
    <h2>Monitoreo en tiempo real:</h2>
    <textarea id="coordinatesBox" style="width: 100%; height: 80px; resize: none;" readonly></textarea>



    <!-- Aquí podrías agregar más información sobre el recorrido -->
</body>

</html>