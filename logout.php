<?php
session_start();
session_destroy();
header("Location: index.php");
?>


// db_connect.php - Conexión a la base de datos
<?php
$conn = new mysqli("localhost", "root", "ezemaria", "coordenadas_db");

if ($conn->connect_error) {
    die("Conexión fallida: " . $conn->connect_error);
}
?>