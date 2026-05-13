using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Data;
using SoporteTecnico.API.DTOs;

namespace SoporteTecnico.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class UsuariosController : ControllerBase
{
    private readonly AppDbContext _db;

    public UsuariosController(AppDbContext db)
    {
        _db = db;
    }

    private string? GetMicrosoftId() =>
        User.FindFirstValue("http://schemas.microsoft.com/identity/claims/objectidentifier")
        ?? User.FindFirstValue("oid");

    [HttpGet]
    public async Task<ActionResult<List<UsuarioDto>>> GetAll()
    {
        var usuarios = await _db.Usuarios
            .Where(u => u.Role == "Tecnico")
            .Select(u => new UsuarioDto
            {
                Id = u.Id,
                DisplayName = u.DisplayName,
                Role = u.Role,
                EstadoActual = u.EstadoActual
            })
            .ToListAsync();

        return Ok(usuarios);
    }

    [HttpGet("me")]
    public async Task<ActionResult<UsuarioDto>> GetMe()
    {
        var msId = GetMicrosoftId();
        if (msId is null) return Unauthorized();

        var usuario = await _db.Usuarios
            .Where(u => u.MicrosoftId == msId)
            .Select(u => new UsuarioDto
            {
                Id = u.Id,
                DisplayName = u.DisplayName,
                Role = u.Role,
                EstadoActual = u.EstadoActual
            })
            .FirstOrDefaultAsync();

        if (usuario is null) return NotFound("Usuario no registrado en el sistema.");

        return Ok(usuario);
    }

    [HttpPatch("estado")]
    public async Task<ActionResult> ToggleEstado([FromBody] UserStatusUpdateDto dto)
    {
        var msId = GetMicrosoftId();
        if (msId is null) return Unauthorized();

        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.MicrosoftId == msId);
        if (usuario is null) return NotFound("Usuario no registrado en el sistema.");

        usuario.EstadoActual = dto.EstadoActual;
        usuario.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync();

        return NoContent();
    }
}
