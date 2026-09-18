using System.Text.Json.Serialization;

namespace SoporteTecnico.API.Models;

public class GrupoPadre
{
    public int Id { get; set; }
    public string Nombre { get; set; } = string.Empty;
    public string? Descripcion { get; set; }
    public int Orden { get; set; }

    [JsonIgnore]
    public ICollection<Grupo> Grupos { get; set; } = new List<Grupo>();

    [JsonIgnore]
    public ICollection<Area> Areas { get; set; } = new List<Area>();
}
