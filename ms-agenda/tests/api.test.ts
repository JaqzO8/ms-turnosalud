import { describe, it, expect, beforeAll } from 'vitest';
import request from 'supertest';
import { Express } from 'express';
import { crearApp } from '../src/app.js';
import { crearRepoMemoria } from '../src/repo/memory.js';

// Fixture fecha fija reproducible (D6): 2026-11-02 es lunes (dia_semana 0)
const LUNES = '2026-11-02';
const DOMINGO = '2026-11-08';
const PEDIATRA = '11111111-1111-4111-8111-111111111111';
const NO_EXISTE = '99999999-9999-4999-8999-999999999999';

let app: Express;

beforeAll(() => {
  app = crearApp(crearRepoMemoria());
});

describe('GET /health', () => {
  it('responde 200 con status ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});

describe('GET /api/v1/medicos', () => {
  it('lista los medicos precargados con el contrato del §4', async () => {
    const res = await request(app).get('/api/v1/medicos');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body).toHaveLength(5);
    const medico = res.body[0];
    expect(medico).toEqual({
      id: expect.any(String),
      nombre: expect.any(String),
      especialidad: expect.stringMatching(/^(PEDIATRIA|MEDICINA_GENERAL|ODONTOLOGIA)$/),
      activo: true,
    });
    expect(res.body.some((m: any) => m.id === PEDIATRA)).toBe(true);
  });
});

describe('GET /api/v1/medicos/:id/disponibilidad', () => {
  it('devuelve franjas de 30 min de 08:00 a 17:00 un lunes (18 slots)', async () => {
    const res = await request(app).get(`/api/v1/medicos/${PEDIATRA}/disponibilidad?fecha=${LUNES}`);
    expect(res.status).toBe(200);
    expect(res.body).toEqual({
      medico_id: PEDIATRA,
      fecha: LUNES,
      franjas: expect.any(Array),
    });
    expect(res.body.franjas).toHaveLength(18); // 9 h * 2 slots/h
    expect(res.body.franjas[0]).toEqual({ inicio: '08:00', fin: '08:30', disponible: true });
    expect(res.body.franjas.at(-1)).toEqual({ inicio: '16:30', fin: '17:00', disponible: true });
  });

  it('devuelve 200 con franjas vacias el domingo (dia sin consultorio)', async () => {
    const res = await request(app).get(`/api/v1/medicos/${PEDIATRA}/disponibilidad?fecha=${DOMINGO}`);
    expect(res.status).toBe(200);
    expect(res.body.franjas).toEqual([]);
  });

  it('rechaza fecha invalida con 400 y envolvente de clase', async () => {
    for (const fecha of ['', '22-10-2026', '2026-13-01', 'abc']) {
      const res = await request(app).get(`/api/v1/medicos/${PEDIATRA}/disponibilidad?fecha=${encodeURIComponent(fecha)}`);
      expect(res.status).toBe(400);
      expect(res.body).toMatchObject({ status: 400, code: 'FECHA_INVALIDA' });
      expect(res.body.correlation_id).toBeDefined();
      expect(res.body.timestamp).toBeDefined();
    }
  });

  it('responde 404 si el medico no existe y envolvente de clase', async () => {
    const res = await request(app).get(`/api/v1/medicos/${NO_EXISTE}/disponibilidad?fecha=${LUNES}`);
    expect(res.status).toBe(404);
    expect(res.body).toMatchObject({ status: 404, code: 'MEDICO_NO_ENCONTRADO' });
    expect(res.headers['x-correlation-id']).toBe(res.body.correlation_id);
  });
});

describe('envelope', () => {
  it('responde 404 JSON para rutas inexistentes', async () => {
    const res = await request(app).get('/no/existe');
    expect(res.status).toBe(404);
    expect(res.body).toMatchObject({ status: 404, code: 'RUTA_NO_ENCONTRADA' });
    expect(res.body.correlation_id).toBeDefined();
  });
});
