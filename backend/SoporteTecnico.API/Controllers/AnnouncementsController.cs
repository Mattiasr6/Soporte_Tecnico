using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using SoporteTecnico.API.Data;
using SoporteTecnico.API.DTOs;
using SoporteTecnico.API.Hubs;

namespace SoporteTecnico.API.Controllers;

[ApiController]
[Route("api/announcements")]
[Authorize]
public class AnnouncementsController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly IHubContext<AppHub> _hubContext;

    public AnnouncementsController(AppDbContext db, IHubContext<AppHub> hubContext)
    {
        _db = db;
        _hubContext = hubContext;
    }

    private int GetUserId() =>
        int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);

    [AllowAnonymous]
    [HttpGet]
    public IActionResult Get()
    {
        return Ok(new AnnouncementDto { Message = AppHub.CurrentAnnouncement });
    }

    [HttpPost]
    public async Task<IActionResult> Post([FromBody] AnnouncementDto dto)
    {
        var userId = GetUserId();
        var user = await _db.Usuarios.FindAsync(userId);
        if (user is null || (user.Role != "Jefe" && !user.CanViewDashboard))
            return Forbid();

        var message = string.IsNullOrWhiteSpace(dto.Message) ? null : dto.Message.Trim();
        AppHub.CurrentAnnouncement = message;
        await _hubContext.Clients.Group("all").SendAsync("ReceiveAnnouncement", message);
        return Ok(new AnnouncementDto { Message = message });
    }
}
