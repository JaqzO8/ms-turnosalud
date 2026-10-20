import { describe, it, expect, vi } from "vitest";
import { Pool } from "pg";
import { crearRepoPg, migrarYSeed } from "../src/repo/pg.js";

describe("PostgreSQL repository", () => {
  it("maps doctors and handles unknown doctors", async () => {
    const row = { id: "id", nombre: "Test", especialidad: "PEDIATRIA", activo: true };
    const query = vi
      .fn()
      .mockResolvedValueOnce({ rows: [row] })
      .mockResolvedValueOnce({ rows: [row] })
      .mockResolvedValueOnce({ rows: [] });
    const repo = crearRepoPg({ query } as unknown as Pool);
    expect(await repo.listarMedicos()).toEqual([row]);
    expect(await repo.obtenerMedico("id")).toEqual(row);
    expect(await repo.obtenerMedico("missing")).toBeNull();
    expect(query.mock.calls[1][1]).toEqual(["id"]);
  });
  it("normalizes PostgreSQL time representations", async () => {
    const query = vi.fn().mockResolvedValue({
      rows: [
        { medico_id: "id", dia_semana: 0, hora_inicio: "8:00", hora_fin: "08:30:00" },
        {
          medico_id: "id",
          dia_semana: 1,
          hora_inicio: { hours: 9, minutes: 0 },
          hora_fin: "09:30",
        },
      ],
    });
    const slots = await crearRepoPg({ query } as unknown as Pool).listarFranjas();
    expect(slots[0]).toEqual({
      medicoId: "id",
      diaSemana: 0,
      horaInicio: "08:00",
      horaFin: "08:30",
    });
    expect(slots[1].horaInicio).toBe("09:00");
  });
  it("creates schema and idempotent seed using parameterized queries", async () => {
    const query = vi.fn().mockResolvedValue({ rows: [] });
    await migrarYSeed({ query } as unknown as Pool);
    expect(query.mock.calls[0][0]).toContain("CREATE TABLE IF NOT EXISTS medicos");
    expect(query.mock.calls.some(([sql]) => sql.includes("ON CONFLICT (id) DO NOTHING"))).toBe(
      true,
    );
    expect(
      query.mock.calls.some(
        ([sql, values]) => sql.includes("WHERE NOT EXISTS") && values.length === 4,
      ),
    ).toBe(true);
  });
});
