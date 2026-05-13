using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Data;

namespace SoporteTecnico.API.Middleware;

public class MockAuthMiddleware(RequestDelegate next)
{
    public async Task InvokeAsync(HttpContext context, AppDbContext db)
    {
        if (context.Request.Headers.TryGetValue("X-Mock-User-Id", out var userIdStr)
            && int.TryParse(userIdStr, out var userId))
        {
            var usuario = await db.Usuarios
                .Where(u => u.Id == userId)
                .Select(u => new { u.Id, u.MicrosoftId, u.DisplayName, u.Email, u.Role })
                .FirstOrDefaultAsync();

            if (usuario is not null)
            {
                var claims = new[]
                {
                    new Claim(ClaimTypes.NameIdentifier, usuario.Id.ToString()),
                    new Claim("oid", usuario.MicrosoftId),
                    new Claim("http://schemas.microsoft.com/identity/claims/objectidentifier", usuario.MicrosoftId),
                    new Claim(ClaimTypes.Role, usuario.Role),
                    new Claim(ClaimTypes.Name, usuario.DisplayName),
                    new Claim("emails", usuario.Email),
                };

                var identity = new ClaimsIdentity(claims, "mock");
                context.User = new ClaimsPrincipal(identity);
            }
        }

        await next(context);
    }
}
