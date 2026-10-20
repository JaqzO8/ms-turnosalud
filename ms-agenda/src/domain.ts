export type Especialidad = 'PEDIATRIA' | 'MEDICINA_GENERAL' | 'ODONTOLOGIA';

export interface Medico {
  id: string;
  nombre: string;
  especialidad: Especialidad;
  activo: boolean;
}

export interface FranjaBase {
  medicoId: string;
  diaSemana: number; // 0 = lunes ... 6 = domingo
  horaInicio: string; // "08:00"
  horaFin: string; // "17:00"
}

export interface Slot {
  inicio: string;
  fin: string;
  disponible: boolean;
}

/** Semana de 0=lunes a 6=domingo. diaSemana del medico desde 'YYYY-MM-DD' (UTC, sin TZ drift). */
export function diaSemanaDeFecha(fecha: string): number {
  const [y, m, d] = fecha.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const iso = dt.getUTCDay(); // 0=domingo ... 6=sabado
  return (iso + 6) % 7; // 0=lunes ... 6=domingo
}

/** Convierte "HH:MM" a minutos desde 00:00. */
export function horaAMinutos(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
}

/** Convierte minutos a "HH:MM". */
export function minutosAHora(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/**
 * Genera slots de 30 min dentro de cada franja base [horaInicio, horaFin).
 * Decision D2: los slots son franjas base informativas; "disponible" es
 * siempre true aqui - la autoridad de ocupacion es ms-citas.
 */
export function slotsDeFranjas(franjas: FranjaBase[], medicoId: string, fecha: string): Slot[] {
  const dia = diaSemanaDeFecha(fecha);
  const propias = franjas.filter((f) => f.medicoId === medicoId && f.diaSemana === dia);
  const slots: Slot[] = [];
  for (const f of propias) {
    const ini = horaAMinutos(f.horaInicio);
    const fin = horaAMinutos(f.horaFin);
    for (let t = ini; t < fin; t += 30) {
      slots.push({ inicio: minutosAHora(t), fin: minutosAHora(t + 30), disponible: true });
    }
  }
  return slots;
}

export function hhmmValida(hhmm: string): boolean {
  return /^([01]\d|2[0-3]):[0-5]\d$/.test(hhmm);
}
