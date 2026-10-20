// Migraciones + seed idempotente en caliente (release gate: scripts/migrate.sh)
import { Pool } from "pg";
import { migrarYSeed } from "./repo/pg.js";

if (!process.env.DATABASE_URL) {
  console.error("DATABASE_URL no definida");
  process.exit(1);
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

main().catch((e: unknown) => {
  console.error("[ms-agenda] migrate falló:", e);
  process.exit(1);
});

async function main(): Promise<void> {
  await migrarYSeed(pool);
  console.log("[ms-agenda] migraciones + seed OK");
  await pool.end();
}
