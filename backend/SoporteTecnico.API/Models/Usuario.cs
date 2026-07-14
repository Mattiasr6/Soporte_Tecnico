namespace SoporteTecnico.API.Models;

public class Usuario
{
    public int Id { get; set; }
    public string Email { get; set; } = string.Empty;
    public string? PasswordHash { get; set; }
    public string DisplayName { get; set; } = string.Empty;
    public string? Notas { get; set; }
    public string? Especialidad { get; set; }
    public string Role { get; set; } = "Tecnico";
    public EstadoUsuario EstadoActual { get; set; } = EstadoUsuario.Ausente;
    public bool CanViewDashboard { get; set; } = false;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    public ICollection<Atencion> Atenciones { get; set; } = new List<Atencion>();
}
