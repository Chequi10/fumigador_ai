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



// Obtener los polígonos de la base de datos
$sql = "SELECT coordenadas FROM lotes";
$result = $conn->query($sql);

$polygons = [];

if ($result->num_rows > 0) {
    while($row = $result->fetch_assoc()) {
        $polygons[] = json_decode($row['coordenadas']);
    }
    echo json_encode($polygons);
} else {
    echo "No polygons found";
}

$conn->close();
?>
