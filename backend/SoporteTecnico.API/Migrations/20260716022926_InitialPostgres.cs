using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace SoporteTecnico.API.Migrations
{
    /// <inheritdoc />
    public partial class InitialPostgres : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Usuarios",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Email = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    PasswordHash = table.Column<string>(type: "text", nullable: true),
                    DisplayName = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    Notas = table.Column<string>(type: "text", nullable: true),
                    Especialidad = table.Column<string>(type: "text", nullable: true),
                    Role = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false, defaultValue: "Tecnico"),
                    EstadoActual = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false, defaultValue: "Ausente"),
                    CanViewDashboard = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Usuarios", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Atenciones",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    UsuarioId = table.Column<int>(type: "integer", nullable: false),
                    AreaSolicitante = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    MedioSolicitud = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    UsuarioSolicitante = table.Column<string>(type: "character varying(10)", maxLength: 10, nullable: false),
                    Categoria = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    Descripcion = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: false),
                    Solucion = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: false),
                    Observaciones = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true),
                    EnlaceApoyo = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    ColaboradorId = table.Column<int>(type: "integer", nullable: true),
                    FueraDeTurno = table.Column<bool>(type: "boolean", nullable: false),
                    FechaRegistro = table.Column<DateOnly>(type: "date", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Atenciones", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Atenciones_Usuarios_ColaboradorId",
                        column: x => x.ColaboradorId,
                        principalTable: "Usuarios",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_Atenciones_Usuarios_UsuarioId",
                        column: x => x.UsuarioId,
                        principalTable: "Usuarios",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Horarios",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    UsuarioId = table.Column<int>(type: "integer", nullable: false),
                    Label = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    HoraInicio1 = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: true),
                    HoraFin1 = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: true),
                    HoraInicio2 = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: true),
                    HoraFin2 = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: true),
                    Mes = table.Column<int>(type: "integer", nullable: false),
                    Anio = table.Column<int>(type: "integer", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Horarios", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Horarios_Usuarios_UsuarioId",
                        column: x => x.UsuarioId,
                        principalTable: "Usuarios",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.InsertData(
                table: "Usuarios",
                columns: new[] { "Id", "CanViewDashboard", "CreatedAt", "DisplayName", "Email", "Especialidad", "EstadoActual", "Notas", "PasswordHash", "Role", "UpdatedAt" },
                values: new object[] { 1, true, new DateTime(2025, 1, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Mattias Ribera Rojas", "mattias.ribera@upds.edu.bo", null, "Ausente", null, null, "Tecnico", new DateTime(2025, 1, 1, 0, 0, 0, 0, DateTimeKind.Utc) });

            migrationBuilder.InsertData(
                table: "Usuarios",
                columns: new[] { "Id", "CreatedAt", "DisplayName", "Email", "Especialidad", "EstadoActual", "Notas", "PasswordHash", "Role", "UpdatedAt" },
                values: new object[,]
                {
                    { 2, new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Diego Orihuela Herrera", "diego.orihuela@upds.edu.bo", null, "Ausente", null, "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.", "Tecnico", new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc) },
                    { 3, new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Paul Manuel Quispe Choque", "paul.quispe@upds.edu.bo", null, "Ausente", null, "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.", "Tecnico", new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc) },
                    { 4, new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Jose Maria Orihuela Herrera", "jose.orihuela@upds.edu.bo", null, "Ausente", null, "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.", "Tecnico", new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc) },
                    { 5, new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Sally Aparicio", "sally.aparicio@upds.edu.bo", null, "Ausente", null, "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.", "Tecnico", new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc) },
                    { 6, new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Ana Carolina Ataides", "carolina.ataides@upds.edu.bo", null, "Ausente", null, "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.", "Tecnico", new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc) },
                    { 7, new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Samira Barrientos", "samira.barrientos@upds.edu.bo", null, "Ausente", null, "$2b$10$f.27ehfd5OYSj5fgfDqPDe0kmUkblxmpG4sM0LUotzOSDfaJNf6b.", "Tecnico", new DateTime(2025, 6, 1, 0, 0, 0, 0, DateTimeKind.Utc) },
                    { 8, new DateTime(2025, 7, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Josue Huayllas", "josue.huayllas@upds.edu.bo", null, "Ausente", null, null, "Jefe", new DateTime(2025, 7, 1, 0, 0, 0, 0, DateTimeKind.Utc) },
                    { 9, new DateTime(2025, 7, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Wilmer Cerruto", "wilmer.cerruto@upds.edu.bo", null, "Ausente", null, null, "Jefe", new DateTime(2025, 7, 1, 0, 0, 0, 0, DateTimeKind.Utc) }
                });

            migrationBuilder.CreateIndex(
                name: "IX_Atenciones_ColaboradorId",
                table: "Atenciones",
                column: "ColaboradorId");

            migrationBuilder.CreateIndex(
                name: "IX_Atenciones_FechaRegistro",
                table: "Atenciones",
                column: "FechaRegistro");

            migrationBuilder.CreateIndex(
                name: "IX_Atenciones_UsuarioId",
                table: "Atenciones",
                column: "UsuarioId");

            migrationBuilder.CreateIndex(
                name: "IX_Horarios_UsuarioId_Mes_Anio",
                table: "Horarios",
                columns: new[] { "UsuarioId", "Mes", "Anio" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Usuarios_Email",
                table: "Usuarios",
                column: "Email",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Atenciones");

            migrationBuilder.DropTable(
                name: "Horarios");

            migrationBuilder.DropTable(
                name: "Usuarios");
        }
    }
}
