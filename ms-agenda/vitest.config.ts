import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      include: ["src/**"],
      // Infra de arranque/BD: validada en integración (T-06) y por el job de
      // PostgreSQL del CI de citas; la cobertura aquí mide la lógica de contratos.
      exclude: ["src/server.ts", "src/migrate.ts", "src/repo/pg.ts"],
    },
  },
});
