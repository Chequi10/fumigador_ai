<?php
session_start();
$conn = new mysqli("localhost", "root", "ezemaria", "coordenadas_db");

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $nombre = $_POST['nombre'];
    $password = $_POST['password'];

    $stmt = $conn->prepare("SELECT ID, modelo FROM usuarios WHERE nombre = ? AND password = ?");
    $stmt->bind_param("ss", $nombre, $password);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows > 0) {
        $user = $result->fetch_assoc();
        $_SESSION['usuario'] = $nombre;
        $_SESSION['modelo'] = $user['modelo'];
        $_SESSION['ID'] = $user['ID']; // Guardar el id del usuario en la sesión
        header("Location: mostrar_mapas.php");
    } else {
        echo "<p>Usuario o contraseña incorrectos</p>";
        header('Location: index.php');
        exit();
    }
    $stmt->close();
}
$conn->close();
?>
