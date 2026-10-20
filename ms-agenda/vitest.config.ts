import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      include: ["src/**"],
      // Entrypoints exercised by deployment smoke; repository logic included.
      exclude: ["src/server.ts", "src/migrate.ts"],
    },
  },
});
