import { build } from "esbuild";

await build({
  entryPoints: ["component_frontend/src/towers.js"],
  outfile: "nivesh/components/assets/towers.js",
  bundle: true,
  format: "esm",
  platform: "browser",
  target: ["es2022"],
  minify: true,
  legalComments: "none",
  charset: "utf8",
});
