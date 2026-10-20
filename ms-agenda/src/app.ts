import express, { Express, NextFunction, Request, Response } from "express";
import { z } from "zod";
import { Repo } from "./repo/memory.js";
import { slotsDeFranjas } from "./domain.js";

/** Express 4 no captura rechazos async: tradicional wrap -> next(e). */
const wrap =
  (fn: (req: Request, res: Response) => Promise<void>) =>
  (req: Request, res: Response, next: NextFunction) => {
    fn(req, res).catch(next);
  };

/** Envolvente de errores de clase. */
export interface ApiError extends Error {
  status: number;
  code: string;
}

export function err(status: number, code: string, message: string): ApiError {
  return Object.assign(new Error(message), { status, code, expose: true });
}

const QueryDisponibilidad = z.object({ fecha: z.string() });
const FECHA_RE = /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;

export function crearApp(repo: Repo): Express {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.get(
    "/api/v1/medicos",
    wrap(async (_req, res) => {
      res.json(await repo.listarMedicos());
    }),
  );

  const parseFecha = (raw: string) => {
    const parsed = QueryDisponibilidad.safeParse({ fecha: raw });
    if (!parsed.success || !FECHA_RE.test(raw)) {
      throw err(400, "FECHA_INVALIDA", "Parámetro 'fecha' requerido con formato YYYY-MM-DD");
    }
    return raw;
  };

  app.get(
    "/api/v1/medicos/:id/disponibilidad",
    wrap(async (req, res) => {
      const fecha = parseFecha(String(req.query.fecha ?? ""));
      const medico = await repo.obtenerMedico(req.params.id);
      if (!medico) {
        throw err(404, "MEDICO_NO_ENCONTRADO", "Médico inexistente");
      }
      const franjas = await repo.listarFranjas();
      res.json({
        medico_id: medico.id,
        fecha,
        franjas: slotsDeFranjas(franjas, medico.id, fecha),
      });
    }),
  );

  // 404 JSON con envolvente (rutas no existentes)
  app.use((_req, res) => {
    res.status(404).json(envelope(404, "RUTA_NO_ENCONTRADA", "Ruta no existente", res));
  });

  // Envolvente de errores de clase: {status, code, message, correlation_id, timestamp}
  app.use((e: unknown, _req: Request, res: Response, _next: NextFunction) => {
    const pe = e as { status?: unknown; code?: unknown; expose?: unknown; message?: unknown };
    const expose = pe.expose === true;
    const status = expose && typeof pe.status === "number" ? pe.status : 500;
    const code = expose && typeof pe.code === "string" ? pe.code : "ERROR_INTERNO";
    const message =
      expose && typeof pe.message === "string" ? pe.message : "Error interno del servicio";
    const body = envelope(status, code, message, res);
    res.status(status).json(body);
  });

  return app;
}

function envelope(status: number, code: string, message: string, res: express.Response) {
  const correlation_id = (res.getHeader("X-Correlation-Id") as string) || crypto.randomUUID();
  res.setHeader("X-Correlation-Id", correlation_id);
  return {
    status,
    code,
    message,
    correlation_id,
    timestamp: new Date().toISOString(),
  };
}
