import { Medico, FranjaBase } from "../domain.js";

export interface Repo {
  listarMedicos(): Promise<Medico[]>;
  obtenerMedico(id: string): Promise<Medico | null>;
  listarFranjas(): Promise<FranjaBase[]>;
}

/** Repositorio en memoria (decisión D6: dev rápido sin BD). Seed igual al pg. */
export function crearRepoMemoria(): Repo {
  const medicos: Medico[] = [...SEED_MEDICOS];
  const franjas: FranjaBase[] = SEED_FRANJAS.map((f) => ({ ...f }));
  return {
    async listarMedicos() {
      return [...medicos];
    },
    async obtenerMedico(id: string) {
      return medicos.find((m) => m.id === id) ?? null;
    },
    async listarFranjas() {
      return [...franjas];
    },
  };
}

export const SEED_MEDICOS: Medico[] = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    nombre: "Dra. Quispe",
    especialidad: "PEDIATRIA",
    activo: true,
  },
  {
    id: "22222222-2222-4222-8222-222222222222",
    nombre: "Dr. Ramos",
    especialidad: "MEDICINA_GENERAL",
    activo: true,
  },
  {
    id: "33333333-3333-4333-8333-333333333333",
    nombre: "Dra. Ayala",
    especialidad: "MEDICINA_GENERAL",
    activo: true,
  },
  {
    id: "44444444-4444-4444-8444-444444444444",
    nombre: "Dr. Huamán",
    especialidad: "ODONTOLOGIA",
    activo: true,
  },
  {
    id: "55555555-5555-4555-8555-555555555555",
    nombre: "Dra. Solano",
    especialidad: "ODONTOLOGIA",
    activo: true,
  },
];

/** D6: lunes a viernes (0-4), 08:00-17:00, slots de 30 min generados en runtime. */
export const SEED_FRANJAS: FranjaBase[] = SEED_MEDICOS.flatMap((m) =>
  [0, 1, 2, 3, 4].map((diaSemana) => ({
    medicoId: m.id,
    diaSemana,
    horaInicio: "08:00",
    horaFin: "17:00",
  })),
);
