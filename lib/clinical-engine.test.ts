import { describe, expect, it } from "vitest";

import {
  analyzeClinicalQuery,
  detectClinicalErrors,
  detectSafetyAlert,
  normalizeText,
  retrieveEvidence
} from "./clinical-engine";

describe("clinical retrieval", () => {
  it("normalizes Spanish accents", () => {
    expect(normalizeText("Hipertensión y cefalea")).toBe(
      "hipertension y cefalea"
    );
  });

  it("retrieves the HTA scope for the reference case", () => {
    const results = retrieveEvidence(
      "Paciente mujer 58 años con cefalea, TA 170/100 y mareo"
    );

    expect(results[0]?.chunk.id).toBe("hta-scope-2017-p11");
    expect(results[0]?.score).toBeGreaterThanOrEqual(3);
  });

  it("flags chest pain as time-dependent", () => {
    expect(
      detectSafetyAlert("Dolor torácico opresivo con diaforesis")?.level
    ).toBe("emergency");
  });

  it("detects a complicated UTI prescribing risk", () => {
    const errors = detectClinicalErrors(
      "Nitrofurantoína para hombre de 70 años con fiebre y dolor lumbar"
    );

    expect(errors[0]?.id).toBe("uti-complicated");
  });

  it("refuses unsupported clinical questions", () => {
    const response = analyzeClinicalQuery(
      "¿Cuál es el manejo de una mordedura de serpiente?"
    );

    expect(response.confidence).toBe("baja");
    expect(response.evidence).toHaveLength(0);
    expect(response.limitation).toContain("Sin coincidencia");
  });

  it("surfaces the HTA scope limitation", () => {
    const response = analyzeClinicalQuery(
      "Paciente con TA 180/110, cefalea y mareo"
    );

    expect(response.limitation).toContain("excluye urgencias hipertensivas");
    expect(response.safetyAlert?.level).toBe("priority");
  });
});

