<?php
session_start();

// Verifica si el usuario está logueado
if (!isset($_SESSION['usuario'])) {
    die("Acceso denegado");
}

$host = "localhost";
$user = "root";
$pass = "ezemaria";
$db = "coordenadas_db";

// Conectar a la base de datos
$conn = new mysqli($host, $user, $pass, $db);

// Verificar la conexión
if ($conn->connect_error) {
    die("Error de conexión: " . $conn->connect_error);
}

// Obtener el id del usuario de la sesión
$user_id = $_SESSION['usuario'];  // Suponiendo que 'usuario' es el nombre de usuario, debes obtener su id de usuario en lugar de nombre

// Consulta para obtener las coordenadas asociadas al id del usuario
$sql = "SELECT id, latitud, longitud, fecha, velocidad, temperatura, humedad, velocidad_viento, angulo_viento, presion, delta_t FROM coordenadas WHERE id = (SELECT ID FROM usuarios WHERE nombre = ?)"; // Filtra las coordenadas por el id de usuario
$stmt = $conn->prepare($sql);
$stmt->bind_param("s", $user_id); // Suponiendo que $_SESSION['usuario'] contiene el nombre de usuario
$stmt->execute();
$result = $stmt->get_result();

// Crear un array de coordenadas
$coordenadas = [];

if ($result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        $coordenadas[] = [
            'id' => floatval($row['id']),
            'lat' => floatval($row['latitud']),
            'lng' => floatval($row['longitud']),
            'fecha' => date("Y-m-d H:i:s", strtotime($row['fecha'])),
            'vel' => floatval($row['velocidad']),
            'temperatura' => floatval($row['temperatura']),
            'humedad' => floatval($row['humedad']),
            'velocidad_viento' => floatval($row['velocidad_viento']),
            'angulo_viento' => floatval($row['angulo_viento']),
            'presion' => floatval($row['presion']),
            'delta_t' => floatval($row['delta_t'])

        ];
    }
}

// Cerrar la conexión
$stmt->close();
$conn->close();

// Convertir el array a formato JSON y devolverlo
echo json_encode($coordenadas);
?>
