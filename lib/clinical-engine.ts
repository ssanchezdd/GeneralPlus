import administrativeErrorsData from "@/data/administrative_errors.json";
import clinicalErrorsData from "@/data/clinical_errors.json";
import diseaseTaxonomyData from "@/data/disease_taxonomy.json";
import evidenceChunksData from "@/data/evidence_chunks.json";

export type Confidence = "alta" | "moderada" | "baja";

export interface Disease {
  id: string;
  name: string;
  priority: string;
  criticality: string;
  aliases: string[];
  color: string;
}

export interface EvidenceChunk {
  id: string;
  diseaseId: string;
  title: string;
  institution: string;
  year: number;
  page: number | null;
  sourceUrl: string;
  sourceType: string;
  scope: string;
  summary: string;
  recommendations: string[];
  redFlags: string[];
  documentation: string[];
  commonErrors: string[];
  tags: string[];
  confidence: Confidence;
}

export interface ClinicalError {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium";
  patterns: string[];
  warning: string;
  action: string;
}

export interface AdministrativeError {
  id: string;
  title: string;
  severity: string;
  check: string;
}

export interface RetrievedEvidence {
  chunk: EvidenceChunk;
  score: number;
}

export interface SafetyAlert {
  level: "emergency" | "priority" | "routine";
  title: string;
  message: string;
}

export interface ClinicalResponse {
  query: string;
  summary: string;
  safetyAlert: SafetyAlert | null;
  evidence: RetrievedEvidence[];
  conduct: string[];
  redFlags: string[];
  documentation: string[];
  commonErrors: string[];
  administrativeChecks: AdministrativeError[];
  confidence: Confidence;
  limitation: string | null;
}

export const diseases = diseaseTaxonomyData as Disease[];
export const evidenceChunks = evidenceChunksData as EvidenceChunk[];
export const clinicalErrors = clinicalErrorsData as ClinicalError[];
export const administrativeErrors =
  administrativeErrorsData as AdministrativeError[];

const STOP_WORDS = new Set([
  "a",
  "al",
  "ante",
  "con",
  "como",
  "cuando",
  "de",
  "del",
  "el",
  "en",
  "es",
  "esta",
  "este",
  "la",
  "las",
  "lo",
  "los",
  "me",
  "para",
  "por",
  "que",
  "se",
  "segun",
  "sin",
  "su",
  "un",
  "una",
  "y"
]);

export function normalizeText(value: string): string {
  return value
    .toLocaleLowerCase("es")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9/ ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function tokenize(value: string): string[] {
  return normalizeText(value)
    .split(" ")
    .filter((token) => token.length > 2 && !STOP_WORDS.has(token));
}

function unique<T>(items: T[]): T[] {
  return [...new Set(items)];
}

function scoreChunk(query: string, chunk: EvidenceChunk): number {
  const normalizedQuery = normalizeText(query);
  const queryTokens = tokenize(query);
  const corpus = normalizeText(
    [
      chunk.title,
      chunk.scope,
      chunk.summary,
      ...chunk.tags,
      ...chunk.redFlags
    ].join(" ")
  );
  const corpusTokens = new Set(tokenize(corpus));
  let score = queryTokens.reduce(
    (total, token) => total + (corpusTokens.has(token) ? 2 : 0),
    0
  );

  for (const tag of chunk.tags) {
    if (normalizedQuery.includes(normalizeText(tag))) {
      score += tag.includes(" ") ? 6 : 3;
    }
  }

  const disease = diseases.find((item) => item.id === chunk.diseaseId);
  for (const alias of disease?.aliases ?? []) {
    if (normalizedQuery.includes(normalizeText(alias))) {
      score += alias.includes(" ") ? 7 : 4;
    }
  }

  return score;
}

export function retrieveEvidence(
  query: string,
  limit = 3
): RetrievedEvidence[] {
  if (!query.trim()) {
    return [];
  }

  return evidenceChunks
    .map((chunk) => ({ chunk, score: scoreChunk(query, chunk) }))
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

export function detectSafetyAlert(query: string): SafetyAlert | null {
  const value = normalizeText(query);
  const containsAny = (patterns: string[]) =>
    patterns.some((pattern) => value.includes(normalizeText(pattern)));

  if (
    containsAny([
      "dolor toracico",
      "dolor precordial",
      "opresion en el pecho",
      "angina"
    ])
  ) {
    return {
      level: "emergency",
      title: "Posible evento tiempo-dependiente",
      message:
        "La sospecha de síndrome coronario agudo requiere una ruta de urgencias. No retrase la activación institucional por usar este prototipo."
    };
  }

  if (
    containsAny([
      "ideacion suicida",
      "plan suicida",
      "quiere morir",
      "hacerse dano",
      "suicidio"
    ])
  ) {
    return {
      level: "emergency",
      title: "Riesgo de autolesión",
      message:
        "Mantenga acompañamiento, limite acceso a medios y active evaluación inmediata según la red local."
    };
  }

  const pregnancy = containsAny(["embarazo", "gestante", "puerperio"]);
  const obstetricAlarm = containsAny([
    "cefalea severa",
    "fosfenos",
    "vision borrosa",
    "epigastralgia",
    "sangrado"
  ]);
  if (pregnancy && obstetricAlarm) {
    return {
      level: "emergency",
      title: "Signos de alarma obstétrica",
      message:
        "La combinación descrita requiere valoración urgente en una ruta materno-perinatal."
    };
  }

  const highBloodPressure = /\b(1[7-9]\d|2\d\d)\/(1[0-9]\d|[89]\d)\b/.test(
    value
  );
  const acuteSymptoms = containsAny([
    "cefalea",
    "mareo",
    "deficit",
    "disnea",
    "dolor toracico",
    "confusion"
  ]);
  if (highBloodPressure && acuteSymptoms) {
    return {
      level: "priority",
      title: "Descartar daño agudo de órgano blanco",
      message:
        "Confirme la medición y haga evaluación clínica dirigida. La GPC de HTA primaria recuperada excluye urgencias hipertensivas."
    };
  }

  return null;
}

export function detectClinicalErrors(statement: string): ClinicalError[] {
  const value = normalizeText(statement);

  return clinicalErrors
    .map((error) => ({
      error,
      matches: error.patterns.filter((pattern) =>
        value.includes(normalizeText(pattern))
      ).length
    }))
    .filter(({ matches }) => matches > 0)
    .sort((a, b) => b.matches - a.matches)
    .map(({ error }) => error);
}

export function analyzeClinicalQuery(query: string): ClinicalResponse {
  const evidence = retrieveEvidence(query);
  const safetyAlert = detectSafetyAlert(query);
  const relevant = evidence.filter((item) => item.score >= 3);

  if (relevant.length === 0) {
    return {
      query,
      summary:
        "La base demostrativa no contiene evidencia suficiente para responder esta pregunta con citas verificables.",
      safetyAlert,
      evidence: [],
      conduct: [
        "No genere una recomendación clínica a partir de esta respuesta.",
        "Consulte la GPC, RIAS o protocolo institucional aplicable.",
        "Si existen signos de alarma, priorice la ruta de urgencias."
      ],
      redFlags: safetyAlert ? [safetyAlert.message] : [],
      documentation: [
        "Motivo de consulta y contexto clínico completo.",
        "Hallazgos que justifican la conducta y la fuente consultada."
      ],
      commonErrors: [
        "Completar vacíos de evidencia con una recomendación no sustentada."
      ],
      administrativeChecks: administrativeErrors.slice(0, 2),
      confidence: "baja",
      limitation:
        "Sin coincidencia suficiente en el corpus local. Este prototipo no consulta internet ni una base vectorial."
    };
  }

  const primary = relevant[0].chunk;
  const supporting = relevant.slice(0, 2).map((item) => item.chunk);
  const confidence: Confidence =
    relevant[0].score >= 12 && primary.confidence === "alta"
      ? "alta"
      : primary.confidence === "baja"
        ? "baja"
        : "moderada";

  return {
    query,
    summary: primary.summary,
    safetyAlert,
    evidence: relevant,
    conduct: unique(supporting.flatMap((chunk) => chunk.recommendations)).slice(
      0,
      6
    ),
    redFlags: unique(supporting.flatMap((chunk) => chunk.redFlags)).slice(0, 6),
    documentation: unique(
      supporting.flatMap((chunk) => chunk.documentation)
    ).slice(0, 6),
    commonErrors: unique(
      supporting.flatMap((chunk) => chunk.commonErrors)
    ).slice(0, 5),
    administrativeChecks: administrativeErrors.slice(0, 3),
    confidence,
    limitation:
      primary.diseaseId === "hypertension"
        ? "La fuente principal recuperada excluye urgencias hipertensivas; la conducta aguda exige un protocolo específico."
        : "Respuesta demostrativa basada en un corpus curado y reducido; requiere validación clínica antes de uso asistencial."
  };
}

export function buildClinicalNote(response: ClinicalResponse): string {
  const lines = [
    "APOYO A LA DECISIÓN - BORRADOR NO CLÍNICO",
    "",
    `Consulta: ${response.query}`,
    `Resumen: ${response.summary}`,
    "",
    "Conducta sugerida para revisión:",
    ...response.conduct.map((item) => `- ${item}`),
    "",
    "Signos de alarma:",
    ...response.redFlags.map((item) => `- ${item}`),
    "",
    "Documentar:",
    ...response.documentation.map((item) => `- ${item}`),
    "",
    "Fuentes:",
    ...response.evidence.map(
      ({ chunk }) =>
        `- ${chunk.title} (${chunk.year}), p. ${chunk.page ?? "web"}: ${chunk.sourceUrl}`
    ),
    "",
    `Certeza del prototipo: ${response.confidence}`,
    "No reemplaza el juicio clínico ni los protocolos institucionales."
  ];

  return lines.join("\n");
}

export function getDiseaseName(id: string): string {
  return diseases.find((disease) => disease.id === id)?.name ?? id;
}
