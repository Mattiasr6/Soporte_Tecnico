namespace SoporteTecnico.API.DTOs;

public class UserStatusUpdateDto
{
    public string EstadoActual { get; set; } = "disponible";
    public string? Motivo { get; set; }
    public int? ColaboradorId { get; set; }
}
