import { Pool } from "pg";
import { Medico, FranjaBase } from "../domain.js";
import { SEED_MEDICOS, SEED_FRANJAS, Repo } from "./memory.js";

export function crearRepoPg(pool: Pool): Repo {
  return {
    async listarMedicos(): Promise<Medico[]> {
      const { rows } = await pool.query(
        `SELECT id, nombre, especialidad, activo FROM medicos WHERE activo = true ORDER BY nombre`,
      );
      return rows.map(rToMedico);
    },
    async obtenerMedico(id: string): Promise<Medico | null> {
      const { rows } = await pool.query(
        `SELECT id, nombre, especialidad, activo FROM medicos WHERE id = $1`,
        [id],
      );
      return rows[0] ? rToMedico(rows[0]) : null;
    },
    async listarFranjas(): Promise<FranjaBase[]> {
      const { rows } = await pool.query(
        `SELECT medico_id, dia_semana, hora_inicio, hora_fin FROM franjas_horarias`,
      );
      return rows.map((r) => ({
        medicoId: r.medico_id,
        diaSemana: r.dia_semana,
        horaInicio: aHHMM(r.hora_inicio),
        horaFin: aHHMM(r.hora_fin),
      }));
    },
  };
}

interface Row {
  id: string;
  nombre: string;
  especialidad: string;
  activo: boolean;
}

function rToMedico(r: Row): Medico {
  return {
    id: r.id,
    nombre: r.nombre,
    especialidad: r.especialidad as Medico["especialidad"],
    activo: r.activo,
  };
}

/** El driver devuelve TIME con formatos distintos según la versión: normaliza a "HH:MM". */
function aHHMM(v: unknown): string {
  if (typeof v === "object" && v !== null && "hours" in v) {
    const t = v as { hours: number; minutes: number };
    const h = String(t.hours).padStart(2, "0");
    const m = String(t.minutes).padStart(2, "0");
    return `${h}:${m}`;
  }
  const s = String(v);
  if (/^\d{1,2}:\d{2}$/.test(s)) {
    const [h, m] = s.split(":");
    return `${h.padStart(2, "0")}:${m}`;
  }
  return s.slice(0, 5);
}

/** DDL + seed idempotente; se ejecuta en el arranque del servicio. */
export async function migrarYSeed(pool: Pool): Promise<void> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS medicos (
      id UUID PRIMARY KEY,
      nombre TEXT NOT NULL,
      especialidad TEXT NOT NULL CHECK (especialidad IN ('PEDIATRIA','MEDICINA_GENERAL','ODONTOLOGIA')),
      activo BOOLEAN NOT NULL DEFAULT true
    );
  `);
  await pool.query(`
    CREATE TABLE IF NOT EXISTS franjas_horarias (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      medico_id UUID NOT NULL REFERENCES medicos(id),
      dia_semana SMALLINT NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
      hora_inicio TIME NOT NULL,
      hora_fin TIME NOT NULL
    );
  `);
  for (const m of SEED_MEDICOS) {
    await pool.query(
      `INSERT INTO medicos (id, nombre, especialidad, activo)
       VALUES ($1, $2, $3, true) ON CONFLICT (id) DO NOTHING`,
      [m.id, m.nombre, m.especialidad],
    );
  }
  for (const f of SEED_FRANJAS) {
    await pool.query(
      `INSERT INTO franjas_horarias (medico_id, dia_semana, hora_inicio, hora_fin)
       SELECT $1, $2, $3, $4
       WHERE NOT EXISTS (
         SELECT 1 FROM franjas_horarias
         WHERE medico_id = $1 AND dia_semana = $2 AND hora_inicio = $3 AND hora_fin = $4
       )`,
      [f.medicoId, f.diaSemana, f.horaInicio, f.horaFin],
    );
  }
}
