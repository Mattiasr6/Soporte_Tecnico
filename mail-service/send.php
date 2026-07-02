<?php
require __DIR__ . '/vendor/autoload.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\SMTP;

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Solo POST']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
$to = $input['to'] ?? '';
$code = $input['code'] ?? '';

if (!$to || !$code) {
    http_response_code(400);
    echo json_encode(['error' => 'Faltan campos: to, code']);
    exit;
}

$smtpHost = getenv('SMTP_HOST') ?: 'smtp.office365.com';
$smtpPort = (int)(getenv('SMTP_PORT') ?: 587);
$smtpUser = getenv('SMTP_USER') ?: '';
$smtpPass = getenv('SMTP_PASS') ?: '';
$fromEmail = getenv('FROM_EMAIL') ?: 'noreply@soporte.upds.edu.bo';
$fromName  = getenv('FROM_NAME') ?: 'Soporte Tecnico UPDS';

$mail = new PHPMailer(true);

try {
    $mail->isSMTP();
    $mail->Host       = $smtpHost;
    $mail->SMTPAuth   = true;
    $mail->Username   = $smtpUser;
    $mail->Password   = $smtpPass;
    $mail->SMTPSecure = $smtpPort === 465 ? PHPMailer::ENCRYPTION_SMTPS : PHPMailer::ENCRYPTION_STARTTLS;
    $mail->Port       = $smtpPort;

    $mail->setFrom($fromEmail, $fromName);
    $mail->addAddress($to);
    $mail->Subject = 'Tu codigo de verificacion - Soporte Tecnico UPDS';
    $mail->Body    = "Has solicitado iniciar sesion en el Sistema de Soporte Tecnico UPDS.\n\n"
                   . "Tu codigo de verificacion es: $code\n\n"
                   . "Este codigo expira en 5 minutos.\n\n"
                   . "Si no solicitaste este codigo, ignora este mensaje.";

    $mail->send();
    echo json_encode(['ok' => true, 'message' => 'Correo enviado']);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Error al enviar: ' . $mail->ErrorInfo]);
}
