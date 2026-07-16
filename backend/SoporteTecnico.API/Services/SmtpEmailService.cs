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
        Console.WriteLine($"[VERIFICATION CODE] {toEmail} -> {code}");

        var url = _config["MailService:Url"] ?? "http://mail-service:8080/send.php";
        var client = _httpClientFactory.CreateClient();
        var payload = JsonSerializer.Serialize(new { to = toEmail, code });
        var content = new StringContent(payload, Encoding.UTF8, "application/json");
        var res = await client.PostAsync(url, content);

        if (!res.IsSuccessStatusCode)
            Console.WriteLine($"[MAIL ERROR] Status {res.StatusCode}");
    }
}
