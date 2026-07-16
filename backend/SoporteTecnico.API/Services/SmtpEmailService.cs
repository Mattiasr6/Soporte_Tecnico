using System.Text;
using System.Text.Json;

namespace SoporteTecnico.API.Services;

public class SmtpEmailService : IEmailService
{
    private readonly IConfiguration _config;
    private readonly IHttpClientFactory _httpClientFactory;

    public SmtpEmailService(IConfiguration config, IHttpClientFactory httpClientFactory)
    {
        _config = config;
        _httpClientFactory = httpClientFactory;
    }

    public async Task SendVerificationCodeAsync(string toEmail, string code)
    {
        // Mostrar en consola para pruebas locales
        Console.WriteLine($"[VERIFICATION CODE] {toEmail} -> {code}");

        var mailServiceUrl = _config["MailService:Url"] ?? "http://mail-service:8080/send.php";
        var directSmtp = bool.Parse(_config["MailService:DirectSmtp"] ?? "false");

        if (directSmtp)
        {
            await SendDirectSmtp(toEmail, code);
            return;
        }

        try
        {
            var client = _httpClientFactory.CreateClient();
            var payload = JsonSerializer.Serialize(new { to = toEmail, code });
            var content = new StringContent(payload, Encoding.UTF8, "application/json");
            var response = await client.PostAsync(mailServiceUrl, content);
            response.EnsureSuccessStatusCode();
        }
        catch
        {
            await SendDirectSmtp(toEmail, code);
        }
    }

    private async Task SendDirectSmtp(string toEmail, string code)
    {
        using var client = new System.Net.Mail.SmtpClient();
        var section = _config.GetSection("Smtp");
        client.Host = section["Host"] ?? "localhost";
        client.Port = int.Parse(section["Port"] ?? "1025");
        client.EnableSsl = bool.Parse(section["UseSsl"] ?? "false");

        var user = section["User"];
        var pass = section["Password"];
        if (!string.IsNullOrEmpty(user))
            client.Credentials = new System.Net.NetworkCredential(user, pass);

        var fromEmail = section["FromEmail"] ?? "noreply@soporte.local";
        var fromName = section["FromName"] ?? "Soporte Tecnico";

        var mailMessage = new System.Net.Mail.MailMessage(fromEmail, toEmail)
        {
            Subject = "Tu codigo de verificacion - Soporte Tecnico",
            Body = $"""
                Has solicitado iniciar sesion en el Sistema de Soporte Tecnico.

                Tu codigo de verificacion es: {code}

                Este codigo expira en 5 minutos.

                Si no solicitaste este codigo, ignora este mensaje.
                """
        };

        await client.SendMailAsync(mailMessage);
    }
}
