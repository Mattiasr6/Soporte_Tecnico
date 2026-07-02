using MailKit.Net.Smtp;
using MailKit.Security;
using MimeKit;

namespace SoporteTecnico.API.Services;

public class SmtpEmailService : IEmailService
{
    private readonly IConfiguration _config;

    public SmtpEmailService(IConfiguration config)
    {
        _config = config;
    }

    public async Task SendVerificationCodeAsync(string toEmail, string code)
    {
        var section = _config.GetSection("Smtp");
        var host = section["Host"]!;
        var port = int.Parse(section["Port"] ?? "25");
        var username = section["User"];
        var password = section["Password"];
        var fromEmail = section["FromEmail"] ?? "noreply@soporte.local";
        var fromName = section["FromName"] ?? "Soporte Tecnico";
        var useSsl = bool.Parse(section["UseSsl"] ?? "false");

        var message = new MimeMessage();
        message.From.Add(new MailboxAddress(fromName, fromEmail));
        message.To.Add(new MailboxAddress("", toEmail));
        message.Subject = "Tu codigo de verificacion - Soporte Tecnico";

        message.Body = new TextPart("plain")
        {
            Text = $"""
                Has solicitado iniciar sesion en el Sistema de Soporte Tecnico.

                Tu codigo de verificacion es: {code}

                Este codigo expira en 5 minutos.

                Si no solicitaste este codigo, ignora este mensaje.
                """
        };

        using var client = new SmtpClient();

        if (!useSsl)
            await client.ConnectAsync(host, port, SecureSocketOptions.StartTlsWhenAvailable);
        else
            await client.ConnectAsync(host, port, SecureSocketOptions.Auto);

        if (!string.IsNullOrEmpty(username))
            await client.AuthenticateAsync(username, password);

        await client.SendAsync(message);
        await client.DisconnectAsync(true);
    }
}
