using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Models;

namespace SoporteTecnico.API.Data;

public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<Usuario> Usuarios => Set<Usuario>();
    public DbSet<Atencion> Atenciones => Set<Atencion>();
    public DbSet<Horario> Horarios => Set<Horario>();
    public DbSet<GrupoPadre> GruposPadres => Set<GrupoPadre>();
    public DbSet<Grupo> Grupos => Set<Grupo>();
    public DbSet<Area> Areas => Set<Area>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Usuario>(entity =>
        {
            entity.ToTable("Usuarios");

            entity.Property(u => u.Email)
                  .IsRequired()
                  .HasMaxLength(255);

            entity.Property(u => u.PasswordHash)
                  .IsRequired(false);

            entity.Property(u => u.DisplayName)
                  .IsRequired()
                  .HasMaxLength(255);

            entity.Property(u => u.Role)
                  .IsRequired()
                  .HasMaxLength(50)
                  .HasDefaultValue("Tecnico");

            entity.Property(u => u.EstadoActual)
                  .IsRequired()
                  .HasConversion<string>()
                  .HasMaxLength(20)
                  .HasDefaultValue(EstadoUsuario.Ausente);

            entity.Property(u => u.CanViewDashboard)
                  .HasDefaultValue(false);

            entity.HasIndex(u => u.Email).IsUnique();

            entity.HasData(
                new Usuario
                {
                    Id = 1,
                    Email = "mattias.ribera@upds.edu.bo",
                    DisplayName = "Mattias Ribera Rojas",
                    Role = "Tecnico",
                    CanViewDashboard = true,
                    PasswordHash = "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.",
                    EstadoActual = EstadoUsuario.Ausente,
                    CreatedAt = new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 2,
                    Email = "diego.orihuela@upds.edu.bo",
                    DisplayName = "Diego Orihuela Herrera",
                    PasswordHash = "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.",
                    Role = "Tecnico",
                    EstadoActual = EstadoUsuario.Ausente,
                    CreatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 3,
                    Email = "paul.quispe@upds.edu.bo",
                    DisplayName = "Paul Manuel Quispe Choque",
                    PasswordHash = "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.",
                    Role = "Tecnico",
                    EstadoActual = EstadoUsuario.Ausente,
                    CreatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 4,
                    Email = "jose.orihuela@upds.edu.bo",
                    DisplayName = "Jose Maria Orihuela Herrera",
                    PasswordHash = "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.",
                    Role = "Tecnico",
                    EstadoActual = EstadoUsuario.Ausente,
                    CreatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 5,
                    Email = "sally.aparicio@upds.edu.bo",
                    DisplayName = "Sally Aparicio",
                    PasswordHash = "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.",
                    Role = "Tecnico",
                    EstadoActual = EstadoUsuario.Ausente,
                    CreatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 6,
                    Email = "carolina.ataides@upds.edu.bo",
                    DisplayName = "Ana Carolina Ataides",
                    PasswordHash = "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.",
                    Role = "Tecnico",
                    EstadoActual = EstadoUsuario.Ausente,
                    CreatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 7,
                    Email = "samira.barrientos@upds.edu.bo",
                    DisplayName = "Samira Barrientos",
                    PasswordHash = "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.",
                    Role = "Tecnico",
                    EstadoActual = EstadoUsuario.Ausente,
                    CreatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 6, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 8,
                    Email = "josue.huayllas@upds.edu.bo",
                    DisplayName = "Josue Huayllas",
                    Role = "Jefe",
                    PasswordHash = "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.",
                    EstadoActual = EstadoUsuario.Ausente,
                    CreatedAt = new DateTime(2025, 7, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 7, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 9,
                    Email = "wilmer.cerruto@upds.edu.bo",
                    DisplayName = "Wilmer Cerruto",
                    Role = "Jefe",
                    PasswordHash = "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.",
                    EstadoActual = EstadoUsuario.Ausente,
                    CreatedAt = new DateTime(2025, 7, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 7, 1, 0, 0, 0, DateTimeKind.Utc)
                }
            );
        });

        modelBuilder.Entity<Atencion>(entity =>
        {
            entity.ToTable("Atenciones");

            entity.Property(a => a.AreaSolicitante)
                  .IsRequired()
                  .HasMaxLength(200);

            entity.Property(a => a.MedioSolicitud)
                  .IsRequired()
                  .HasMaxLength(50);

            entity.Property(a => a.UsuarioSolicitante)
                  .IsRequired()
                  .HasMaxLength(10);

            entity.Property(a => a.Categoria)
                  .IsRequired()
                  .HasMaxLength(200);

            entity.Property(a => a.Descripcion)
                  .IsRequired()
                  .HasMaxLength(1000);

            entity.Property(a => a.Solucion)
                  .IsRequired()
                  .HasMaxLength(1000);

            entity.Property(a => a.Observaciones)
                  .HasMaxLength(2000);

            entity.Property(a => a.EnlaceApoyo)
                  .HasMaxLength(500);

            entity.Property(a => a.FechaRegistro)
                  .IsRequired();

            entity.Property(a => a.CreatedAt);

            entity.HasOne(a => a.Usuario)
                  .WithMany(u => u.Atenciones)
                  .HasForeignKey(a => a.UsuarioId)
                  .OnDelete(DeleteBehavior.Restrict);

            entity.HasOne(a => a.Colaborador)
                  .WithMany()
                  .HasForeignKey(a => a.ColaboradorId)
                  .OnDelete(DeleteBehavior.SetNull);

            entity.HasOne(a => a.GrupoPadre)
                  .WithMany()
                  .HasForeignKey(a => a.GrupoPadreId)
                  .OnDelete(DeleteBehavior.SetNull);

            entity.HasOne(a => a.Grupo)
                  .WithMany()
                  .HasForeignKey(a => a.GrupoId)
                  .OnDelete(DeleteBehavior.SetNull);

            entity.HasOne(a => a.Area)
                  .WithMany()
                  .HasForeignKey(a => a.AreaId)
                  .OnDelete(DeleteBehavior.SetNull);

            entity.HasIndex(a => a.UsuarioId);
            entity.HasIndex(a => a.FechaRegistro);
            entity.HasIndex(a => a.GrupoPadreId);
            entity.HasIndex(a => a.GrupoId);
            entity.HasIndex(a => a.AreaId);
        });

        modelBuilder.Entity<Horario>(entity =>
        {
            entity.ToTable("Horarios");

            entity.Property(h => h.Label)
                  .IsRequired()
                  .HasMaxLength(100);

            entity.Property(h => h.HoraInicio1).HasMaxLength(5);
            entity.Property(h => h.HoraFin1).HasMaxLength(5);
            entity.Property(h => h.HoraInicio2).HasMaxLength(5);
            entity.Property(h => h.HoraFin2).HasMaxLength(5);

            entity.HasOne(h => h.Usuario)
                  .WithMany()
                  .HasForeignKey(h => h.UsuarioId)
                  .OnDelete(DeleteBehavior.Restrict);

            entity.HasIndex(h => new { h.UsuarioId, h.Mes, h.Anio }).IsUnique();
        });

        modelBuilder.Entity<GrupoPadre>(entity =>
        {
            entity.ToTable("GruposPadres");
            entity.HasKey(g => g.Id);
            entity.Property(g => g.Nombre).IsRequired().HasMaxLength(50);
            entity.Property(g => g.Descripcion).HasMaxLength(200);
            entity.HasIndex(g => g.Nombre).IsUnique();
            entity.HasData(
                new GrupoPadre { Id = 1, Nombre = "Administrativos", Orden = 1 },
                new GrupoPadre { Id = 2, Nombre = "Académicos", Orden = 2 },
                new GrupoPadre { Id = 3, Nombre = "Extras", Orden = 3 }
            );
        });

        modelBuilder.Entity<Grupo>(entity =>
        {
            entity.ToTable("Grupos");
            entity.HasKey(g => g.Id);
            entity.Property(g => g.Nombre).IsRequired().HasMaxLength(100);
            entity.HasOne(g => g.GrupoPadre).WithMany(p => p.Grupos).HasForeignKey(g => g.GrupoPadreId).OnDelete(DeleteBehavior.Restrict);
            entity.HasIndex(g => new { g.GrupoPadreId, g.Nombre }).IsUnique();
        });

        modelBuilder.Entity<Area>(entity =>
        {
            entity.ToTable("Areas");
            entity.HasKey(a => a.Id);
            entity.Property(a => a.Nombre).IsRequired().HasMaxLength(200);
            entity.HasOne(a => a.GrupoPadre).WithMany(p => p.Areas).HasForeignKey(a => a.GrupoPadreId).OnDelete(DeleteBehavior.Restrict);
            entity.HasOne(a => a.Grupo).WithMany(g => g.Areas).HasForeignKey(a => a.GrupoId).OnDelete(DeleteBehavior.SetNull);
            entity.HasIndex(a => new { a.GrupoPadreId, a.GrupoId, a.Nombre }).IsUnique();
        });
    }
}
