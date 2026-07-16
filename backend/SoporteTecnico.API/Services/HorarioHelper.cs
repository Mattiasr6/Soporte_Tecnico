using SoporteTecnico.API.Models;

namespace SoporteTecnico.API.Services;

public static class HorarioHelper
{
    private static readonly TimeZoneInfo BoliviaTz = TimeZoneInfo.FindSystemTimeZoneById("America/La_Paz");

    /// <summary>
    /// Devuelve el estado efectivo considerando si el usuario está dentro de su horario.
    /// Si está Disponible u Ocupado pero fuera de su horario registrado → Extraturno.
    /// </summary>
    public static string EstadoEfectivo(EstadoUsuario estadoActual, Horario? horario)
    {
        // Ausente se queda igual (desconectado)
        if (estadoActual == EstadoUsuario.Ausente)
            return "ausente";

        // Extraturno se queda igual
        if (estadoActual == EstadoUsuario.Extraturno)
            return "extraturno";

        // Si está disponible/ocupado, verificar horario
        if (estadoActual is EstadoUsuario.Disponible or EstadoUsuario.Ocupado)
        {
            if (!EstaEnHorario(horario))
                return "extraturno";
        }

        return estadoActual.ToString().ToLower();
    }
    /// <summary>
    /// Indica si una fecha/hora específica está fuera del horario registrado.
    /// </summary>
    public static bool EstaFueraDeHorario(Horario? horario, DateTime fechaUtc)
    {
        if (horario is null) return false;
        var horaLocal = TimeZoneInfo.ConvertTimeFromUtc(fechaUtc, BoliviaTz).TimeOfDay;
        return !DentroDeBloques(horario, horaLocal);
    }

    private static bool EstaEnHorario(Horario? horario)
    {
        if (horario is null) return true;
        var now = TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, BoliviaTz).TimeOfDay;
        return DentroDeBloques(horario, now);
    }

    private static bool DentroDeBloques(Horario horario, TimeSpan hora)
    {
        if (TimeSpan.TryParse(horario.HoraInicio1, out var ini1) &&
            TimeSpan.TryParse(horario.HoraFin1, out var fin1) &&
            hora >= ini1 && hora <= fin1)
            return true;

        if (TimeSpan.TryParse(horario.HoraInicio2, out var ini2) &&
            TimeSpan.TryParse(horario.HoraFin2, out var fin2) &&
            hora >= ini2 && hora <= fin2)
            return true;

        return false;
    }

}