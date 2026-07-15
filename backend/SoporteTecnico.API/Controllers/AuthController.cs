using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using SoporteTecnico.API.Data;
using SoporteTecnico.API.Models;
using SoporteTecnico.API.Services;

namespace SoporteTecnico.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly IConfiguration _config;
    private readonly IEmailService _emailService;
    private readonly IVerificationCodeStore _codeStore;

    public AuthController(
        AppDbContext db,
        IConfiguration config,
        IEmailService emailService,
        IVerificationCodeStore codeStore)
    {
        _db = db;
        _config = config;
        _emailService = emailService;
        _codeStore = codeStore;
    }

    public record SendCodeRequest(string Email);

    [HttpPost("send-code")]
    public async Task<ActionResult> SendCode([FromBody] SendCodeRequest request)
    {
        var email = request.Email.Trim().ToLowerInvariant();

        if (string.IsNullOrWhiteSpace(email))
            return BadRequest(new { error = "El correo es requerido" });

        var code = Random.Shared.Next(100000, 999999).ToString();

        try
        {
            await _emailService.SendVerificationCodeAsync(email, code);
            _codeStore.Store(email, code);
            return Ok(new { message = "Codigo enviado al correo" });
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { error = $"Error al enviar el codigo: {ex.Message}" });
        }
    }

    public record VerifyCodeRequest(string Email, string Code);

    [HttpPost("verify-code")]
    public async Task<ActionResult> VerifyCode([FromBody] VerifyCodeRequest request)
    {
        var email = request.Email.Trim().ToLowerInvariant();

        if (string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(request.Code))
            return BadRequest(new { error = "Correo y codigo son requeridos" });

        var storedCode = _codeStore.Get(email);

        if (storedCode is null || storedCode != request.Code.Trim())
            return Unauthorized(new { error = "Codigo invalido o expirado" });

        _codeStore.Remove(email);

        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => EF.Functions.ILike(u.Email, email));

        if (usuario is null)
        {
            var displayName = DeriveDisplayNameFromEmail(email);

            var dashboardAccess = _config.GetSection("DashboardAccess").Get<string[]>() ?? [];
            var canViewDashboard = dashboardAccess.Any(a => a.Equals(email, StringComparison.OrdinalIgnoreCase)) || usuario?.Role == "Jefe";

            usuario = new Usuario
            {
                Email = email,
                DisplayName = displayName,
                Role = "Tecnico",
                EstadoActual = EstadoUsuario.Ausente,
                CanViewDashboard = canViewDashboard,
                CreatedAt = DateTime.UtcNow,
                UpdatedAt = DateTime.UtcNow
            };

            _db.Usuarios.Add(usuario);
            await _db.SaveChangesAsync();
        }

        var token = GenerateJwt(usuario);

        var canView = usuario.CanViewDashboard || usuario.Role == "Jefe";

        return Ok(new
        {
            token,
            user = new
            {
                usuario.Id,
                usuario.DisplayName,
                usuario.Role,
                usuario.Email,
                usuario.EstadoActual,
                canViewDashboard = canView
            }
        });
    }

    private string GenerateJwt(Usuario usuario)
    {
        var key = new SymmetricSecurityKey(
            Encoding.UTF8.GetBytes(_config["Jwt:Key"]!));
        var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, usuario.Id.ToString()),
            new Claim(ClaimTypes.Name, usuario.DisplayName),
            new Claim(ClaimTypes.Role, usuario.Role),
            new Claim(ClaimTypes.Email, usuario.Email),
            new Claim("sub", usuario.Id.ToString()),
        };

        var token = new JwtSecurityToken(
            issuer: _config["Jwt:Issuer"],
            audience: _config["Jwt:Audience"],
            claims: claims,
            expires: DateTime.UtcNow.AddDays(365),
            signingCredentials: credentials
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    private static string DeriveDisplayNameFromEmail(string email)
    {
        var localPart = email.Split('@')[0];
        var name = localPart.Replace('.', ' ');
        return Thread.CurrentThread.CurrentCulture.TextInfo.ToTitleCase(name.ToLower());
    }
}
