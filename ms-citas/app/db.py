import os
from datetime import UTC, date, datetime, time
from uuid import uuid4

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, Index, Integer, String, Time, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Cita(Base):
    __tablename__ = "citas"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    medico_id: Mapped[str] = mapped_column(String(36))
    fecha: Mapped[date] = mapped_column(Date)
    hora: Mapped[time] = mapped_column(Time)
    estado: Mapped[str] = mapped_column(String(12), default="CONFIRMADA")
    paciente_nombre: Mapped[str] = mapped_column(String(200))
    documento: Mapped[str] = mapped_column(String(8), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(36), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    respuesta_original: Mapped[dict] = mapped_column(JSON)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (
        CheckConstraint("estado IN ('CONFIRMADA', 'CANCELADA')", name="ck_cita_estado"),
        Index(
            "uq_cita_medico_horario",
            "medico_id",
            "fecha",
            "hora",
            unique=True,
            sqlite_where=text("estado = 'CONFIRMADA'"),
            postgresql_where=text("estado = 'CONFIRMADA'"),
        ),
    )


class Usuario(Base):
    __tablename__ = "usuarios"
    documento: Mapped[str] = mapped_column(String(8), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(200))


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    documento: Mapped[str] = mapped_column(String(8), index=True)
    expires: Mapped[int] = mapped_column(Integer)


def make_engine(url=None):
    url = url or os.getenv("DATABASE_URL", "sqlite:///./citas.db")
    args = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=args, pool_pre_ping=True)


if __name__ == "__main__":
    engine = make_engine()
    Base.metadata.create_all(engine)
    engine.dispose()
