import { Pool } from "pg";
import { crearApp } from "./app.js";
import { crearRepoMemoria, Repo } from "./repo/memory.js";
import { crearRepoPg, migrarYSeed } from "./repo/pg.js";

async function elegirRepo(): Promise<Repo> {
  const driver = process.env.DRIVER ?? (process.env.DATABASE_URL ? "pg" : "memory");
  if (driver === "pg" && process.env.DATABASE_URL) {
    const pool = new Pool({ connectionString: process.env.DATABASE_URL });
    await migrarYSeed(pool);
    console.log("[ms-agenda] repositorio PG + seed idempotente listo");
    return crearRepoPg(pool);
  }
  console.log("[ms-agenda] repositorio en memoria (DRIVER=memory, útil para dev)");
  return crearRepoMemoria();
}

const PORT = Number(process.env.PORT ?? 3001);

async function main() {
  const repo = await elegirRepo();
  const app = crearApp(repo);
  const server = app.listen(PORT, process.env.HOST ?? "127.0.0.1", () => {
    console.log(`[ms-agenda] escuchando en :${PORT}`);
  });
  // apagado limpio
  for (const sig of ["SIGINT", "SIGTERM"] as const) {
    process.on(sig, () => server.close(() => process.exit(0)));
  }
}

main().catch((e) => {
  console.error("[ms-agenda] arranque falló:", e);
  process.exit(1);
});
