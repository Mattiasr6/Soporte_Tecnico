namespace SoporteTecnico.API.Models;

public class Horario
{
    public int Id { get; set; }
    public int UsuarioId { get; set; }
    public string Label { get; set; } = "08:00 - 16:00";
    public string? HoraInicio1 { get; set; } = "08:00";
    public string? HoraFin1 { get; set; } = "16:00";
    public string? HoraInicio2 { get; set; }
    public string? HoraFin2 { get; set; }
    public int Mes { get; set; }
    public int Anio { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public Usuario Usuario { get; set; } = null!;
}
