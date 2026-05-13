namespace SoporteTecnico.API.DTOs;

public class AtencionBulkCreateDto
{
    public List<AtencionCreateDto> Atenciones { get; set; } = new();
}
