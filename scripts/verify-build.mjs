import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";

const requiredFiles = ["out/index.html", "out/404.html"];

for (const file of requiredFiles) {
  await access(file, constants.R_OK);
}

const index = await readFile("out/index.html", "utf8");
const requiredMarkers = [
  "Criterio",
  "Copiloto clínico colombiano",
  "No reemplaza el juicio clínico"
];

for (const marker of requiredMarkers) {
  if (!index.includes(marker)) {
    throw new Error(`Static export is missing expected marker: ${marker}`);
  }
}

console.log(`Static export verified: ${requiredFiles.join(", ")}`);

