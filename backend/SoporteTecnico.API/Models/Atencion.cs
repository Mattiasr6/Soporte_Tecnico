namespace SoporteTecnico.API.Models;

public class Atencion
{
    public int Id { get; set; }
    public int UsuarioId { get; set; }
    public string AreaSolicitante { get; set; } = string.Empty;
    public string Categoria { get; set; } = string.Empty;
    public string Descripcion { get; set; } = string.Empty;
    public string Solucion { get; set; } = string.Empty;
    public string? Observaciones { get; set; }
    public DateOnly FechaRegistro { get; set; } = DateOnly.FromDateTime(DateTime.UtcNow);
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public Usuario Usuario { get; set; } = null!;
}
