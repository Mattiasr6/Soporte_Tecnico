using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Data;
using SoporteTecnico.API.DTOs;
using SoporteTecnico.API.Models;

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

    private int GetUserId() =>
        int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);

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
        var userId = GetUserId();

        var usuario = await _db.Usuarios
            .Where(u => u.Id == userId)
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

    public record NotasDto(string? Contenido);

    [HttpGet("notas")]
    public async Task<ActionResult<NotasDto>> GetNotas()
    {
        var userId = GetUserId();
        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.Id == userId);
        if (usuario is null) return NotFound();
        return Ok(new NotasDto(usuario.Notas));
    }

    [HttpPut("notas")]
    public async Task<ActionResult> UpdateNotas([FromBody] NotasDto dto)
    {
        var userId = GetUserId();
        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.Id == userId);
        if (usuario is null) return NotFound();
        usuario.Notas = dto.Contenido;
        await _db.SaveChangesAsync();
        return NoContent();
    }

    [HttpPatch("estado")]
    public async Task<ActionResult> ToggleEstado([FromBody] UserStatusUpdateDto dto)
    {
        var userId = GetUserId();

        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.Id == userId);
        if (usuario is null) return NotFound("Usuario no registrado en el sistema.");

        usuario.EstadoActual = dto.EstadoActual;
        usuario.UpdatedAt = DateTime.UtcNow;

        await _db.SaveChangesAsync();

        return NoContent();
    }
}
