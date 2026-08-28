using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace SoporteTecnico.API.Migrations
{
    /// <inheritdoc />
    public partial class V2_JerarquiaAreas : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "AreaId",
                table: "Atenciones",
                type: "integer",
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "GrupoId",
                table: "Atenciones",
                type: "integer",
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "GrupoPadreId",
                table: "Atenciones",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "GruposPadres",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Nombre = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    Descripcion = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    Orden = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_GruposPadres", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Grupos",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    GrupoPadreId = table.Column<int>(type: "integer", nullable: false),
                    Nombre = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    Activo = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Grupos", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Grupos_GruposPadres_GrupoPadreId",
                        column: x => x.GrupoPadreId,
                        principalTable: "GruposPadres",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Areas",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    GrupoPadreId = table.Column<int>(type: "integer", nullable: false),
                    GrupoId = table.Column<int>(type: "integer", nullable: true),
                    Nombre = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    Activo = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Areas", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Areas_GruposPadres_GrupoPadreId",
                        column: x => x.GrupoPadreId,
                        principalTable: "GruposPadres",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_Areas_Grupos_GrupoId",
                        column: x => x.GrupoId,
                        principalTable: "Grupos",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.InsertData(
                table: "GruposPadres",
                columns: new[] { "Id", "Descripcion", "Nombre", "Orden" },
                values: new object[,]
                {
                    { 1, null, "Administrativos", 1 },
                    { 2, null, "Académicos", 2 },
                    { 3, null, "Extras", 3 }
                });

            migrationBuilder.CreateIndex(
                name: "IX_Atenciones_AreaId",
                table: "Atenciones",
                column: "AreaId");

            migrationBuilder.CreateIndex(
                name: "IX_Atenciones_GrupoId",
                table: "Atenciones",
                column: "GrupoId");

            migrationBuilder.CreateIndex(
                name: "IX_Atenciones_GrupoPadreId",
                table: "Atenciones",
                column: "GrupoPadreId");

            migrationBuilder.CreateIndex(
                name: "IX_Areas_GrupoId",
                table: "Areas",
                column: "GrupoId");

            migrationBuilder.CreateIndex(
                name: "IX_Areas_GrupoPadreId_GrupoId_Nombre",
                table: "Areas",
                columns: new[] { "GrupoPadreId", "GrupoId", "Nombre" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Grupos_GrupoPadreId_Nombre",
                table: "Grupos",
                columns: new[] { "GrupoPadreId", "Nombre" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_GruposPadres_Nombre",
                table: "GruposPadres",
                column: "Nombre",
                unique: true);

            migrationBuilder.AddForeignKey(
                name: "FK_Atenciones_Areas_AreaId",
                table: "Atenciones",
                column: "AreaId",
                principalTable: "Areas",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);

            migrationBuilder.AddForeignKey(
                name: "FK_Atenciones_GruposPadres_GrupoPadreId",
                table: "Atenciones",
                column: "GrupoPadreId",
                principalTable: "GruposPadres",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);

            migrationBuilder.AddForeignKey(
                name: "FK_Atenciones_Grupos_GrupoId",
                table: "Atenciones",
                column: "GrupoId",
                principalTable: "Grupos",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Atenciones_Areas_AreaId",
                table: "Atenciones");

            migrationBuilder.DropForeignKey(
                name: "FK_Atenciones_GruposPadres_GrupoPadreId",
                table: "Atenciones");

            migrationBuilder.DropForeignKey(
                name: "FK_Atenciones_Grupos_GrupoId",
                table: "Atenciones");

            migrationBuilder.DropTable(
                name: "Areas");

            migrationBuilder.DropTable(
                name: "Grupos");

            migrationBuilder.DropTable(
                name: "GruposPadres");

            migrationBuilder.DropIndex(
                name: "IX_Atenciones_AreaId",
                table: "Atenciones");

            migrationBuilder.DropIndex(
                name: "IX_Atenciones_GrupoId",
                table: "Atenciones");

            migrationBuilder.DropIndex(
                name: "IX_Atenciones_GrupoPadreId",
                table: "Atenciones");

            migrationBuilder.DropColumn(
                name: "AreaId",
                table: "Atenciones");

            migrationBuilder.DropColumn(
                name: "GrupoId",
                table: "Atenciones");

            migrationBuilder.DropColumn(
                name: "GrupoPadreId",
                table: "Atenciones");
        }
    }
}
