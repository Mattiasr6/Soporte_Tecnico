namespace SoporteTecnico.API.DTOs;

public class UsuarioDto
{
    public int Id { get; set; }
    public string DisplayName { get; set; } = string.Empty;
    public string? Especialidad { get; set; }
    public string Role { get; set; } = string.Empty;
    public string EstadoActual { get; set; } = "ausente";
}
