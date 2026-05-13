-- ============================================
-- Esquema Inicial - Sistema de Soporte Técnico
-- ============================================

CREATE TABLE Usuarios (
    Id              INT             IDENTITY(1,1) PRIMARY KEY,
    MicrosoftId     NVARCHAR(255)   NOT NULL,
    Email           NVARCHAR(255)   NOT NULL,
    DisplayName     NVARCHAR(255)   NOT NULL,
    Role            NVARCHAR(50)    NOT NULL DEFAULT 'Tecnico',  -- 'Tecnico' | 'Jefe'
    EstadoActual    BIT             NOT NULL DEFAULT 0,          -- 0 = Disponible, 1 = Ocupado
    CreatedAt       DATETIME2       NOT NULL DEFAULT GETUTCDATE(),
    UpdatedAt       DATETIME2       NOT NULL DEFAULT GETUTCDATE(),

    CONSTRAINT UQ_Usuarios_MicrosoftId UNIQUE (MicrosoftId),
    CONSTRAINT UQ_Usuarios_Email       UNIQUE (Email)
);

CREATE TABLE Atenciones (
    Id              INT             IDENTITY(1,1) PRIMARY KEY,
    UsuarioId       INT             NOT NULL,
    AreaSolicitante NVARCHAR(200)   NOT NULL,
    Categoria       NVARCHAR(200)   NOT NULL,
    Descripcion     NVARCHAR(1000)  NOT NULL,
    Solucion        NVARCHAR(1000)  NOT NULL,
    Observaciones   NVARCHAR(2000)  NULL,
    FechaRegistro   DATE            NOT NULL DEFAULT CAST(GETUTCDATE() AS DATE),
    CreatedAt       DATETIME2       NOT NULL DEFAULT GETUTCDATE(),

    CONSTRAINT FK_Atenciones_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Usuarios(Id)
);

CREATE INDEX IX_Atenciones_UsuarioId   ON Atenciones(UsuarioId);
CREATE INDEX IX_Atenciones_FechaRegistro ON Atenciones(FechaRegistro);
GO
