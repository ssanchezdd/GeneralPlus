"use client";

import { FormEvent, useMemo, useState } from "react";

import {
  analyzeClinicalQuery,
  buildClinicalNote,
  detectClinicalErrors,
  diseases,
  evidenceChunks,
  getDiseaseName,
  type ClinicalResponse,
  type Confidence,
  type EvidenceChunk
} from "@/lib/clinical-engine";

type Tab = "consulta" | "checklists" | "errores" | "guias";
type IconName =
  | "activity"
  | "arrow"
  | "book"
  | "check"
  | "clipboard"
  | "copy"
  | "error"
  | "external"
  | "heart"
  | "menu"
  | "search"
  | "send"
  | "shield"
  | "spark"
  | "x";

const EXAMPLE_QUERIES = [
  "Mujer de 58 años con cefalea, TA 170/100 y mareo",
  "Dolor torácico opresivo con diaforesis desde hace 20 minutos",
  "Gestante con cefalea severa, fosfenos y epigastralgia",
  "Paciente con depresión que dice que quiere morir"
];

const DEFAULT_QUERY = EXAMPLE_QUERIES[0];
const DEFAULT_ERROR_TEXT =
  "Voy a mandar nitrofurantoína a hombre de 70 años con fiebre y dolor lumbar.";

const NAV_ITEMS: { id: Tab; label: string; icon: IconName; kicker: string }[] = [
  { id: "consulta", label: "Consulta", icon: "spark", kicker: "Evidencia" },
  {
    id: "checklists",
    label: "Checklists",
    icon: "clipboard",
    kicker: "Seguridad"
  },
  { id: "errores", label: "Detector", icon: "error", kicker: "Prevención" },
  { id: "guias", label: "Guías", icon: "book", kicker: "Fuentes" }
];

function Icon({
  name,
  className = "h-5 w-5"
}: {
  name: IconName;
  className?: string;
}) {
  const paths: Record<IconName, React.ReactNode> = {
    activity: <path d="M3 12h4l2-7 4 14 2-7h6" />,
    arrow: <path d="m9 18 6-6-6-6" />,
    book: (
      <>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    clipboard: (
      <>
        <rect width="14" height="18" x="5" y="3" rx="2" />
        <path d="M9 3V1h6v2M9 8h6M9 12h6M9 16h4" />
      </>
    ),
    copy: (
      <>
        <rect width="13" height="13" x="9" y="9" rx="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
      </>
    ),
    error: (
      <>
        <path d="M10.3 2.8 1.9 17a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 2.8a2 2 0 0 0-3.4 0Z" />
        <path d="M12 9v4M12 17h.01" />
      </>
    ),
    external: (
      <>
        <path d="M15 3h6v6M10 14 21 3" />
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      </>
    ),
    heart: (
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z" />
    ),
    menu: <path d="M4 6h16M4 12h16M4 18h16" />,
    search: (
      <>
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
      </>
    ),
    send: (
      <>
        <path d="m22 2-7 20-4-9-9-4Z" />
        <path d="M22 2 11 13" />
      </>
    ),
    shield: <path d="M20 13c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V5l8-3 8 3Z" />,
    spark: (
      <path d="m12 3-1.5 4.5L6 9l4.5 1.5L12 15l1.5-4.5L18 9l-4.5-1.5L12 3ZM5 16l-.8 2.2L2 19l2.2.8L5 22l.8-2.2L8 19l-2.2-.8L5 16Z" />
    ),
    x: <path d="M18 6 6 18M6 6l12 12" />
  };

  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const styles: Record<Confidence, string> = {
    alta: "bg-[#dceae4] text-[#205348]",
    moderada: "bg-[#f3e7be] text-[#73591f]",
    baja: "bg-[#f4dcd4] text-[#8d3d25]"
  };

  return (
    <span
      className={`rounded-full px-3 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] ${styles[confidence]}`}
    >
      Certeza {confidence}
    </span>
  );
}

function SectionList({
  title,
  icon,
  items,
  tone = "default"
}: {
  title: string;
  icon: IconName;
  items: string[];
  tone?: "default" | "danger" | "mint";
}) {
  const tones = {
    default: "border-[#d9ded8] bg-white",
    danger: "border-[#edc9bd] bg-[#fff9f6]",
    mint: "border-[#c9ddd4] bg-[#f7fbf9]"
  };

  return (
    <section className={`rounded-2xl border p-5 ${tones[tone]}`}>
      <div className="flex items-center gap-2.5">
        <span
          className={`grid h-8 w-8 place-items-center rounded-full ${
            tone === "danger"
              ? "bg-[#f4dcd4] text-[#a34227]"
              : "bg-[#e5eee9] text-[#2b6b5f]"
          }`}
        >
          <Icon name={icon} className="h-4 w-4" />
        </span>
        <h3 className="text-sm font-bold text-[#17332d]">{title}</h3>
      </div>
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li
            key={item}
            className="flex gap-3 text-sm leading-6 text-[#4d5d58]"
          >
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#7b948b]" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SourceCard({
  source,
  rank
}: {
  source: { chunk: EvidenceChunk; score: number };
  rank: number;
}) {
  const { chunk, score } = source;
  return (
    <a
      className="group flex items-start gap-3 rounded-xl border border-[#d9ded8] bg-white p-4 transition hover:-translate-y-0.5 hover:border-[#9db7ac] hover:shadow-sm"
      href={chunk.sourceUrl}
      target="_blank"
      rel="noreferrer"
    >
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#10231f] font-mono text-xs font-semibold text-white">
        {rank}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-bold leading-5 text-[#17332d]">
          {chunk.title}
        </span>
        <span className="mt-1 block font-mono text-[10px] uppercase tracking-[0.1em] text-[#74817d]">
          {chunk.sourceType} · {chunk.year} ·{" "}
          {chunk.page ? `p. ${chunk.page}` : "recurso web"} · score {score}
        </span>
        <span className="mt-2 line-clamp-2 block text-xs leading-5 text-[#6b7874]">
          Alcance: {chunk.scope}
        </span>
      </span>
      <Icon
        name="external"
        className="mt-1 h-4 w-4 shrink-0 text-[#789087] transition group-hover:text-[#2b6b5f]"
      />
    </a>
  );
}

function QueryWorkspace() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [response, setResponse] = useState<ClinicalResponse>(() =>
    analyzeClinicalQuery(DEFAULT_QUERY)
  );
  const [copied, setCopied] = useState(false);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (!query.trim()) return;
    setResponse(analyzeClinicalQuery(query));
    setCopied(false);
  };

  const copyNote = async () => {
    await navigator.clipboard.writeText(buildClinicalNote(response));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#2b6b5f]">
            Consulta con trazabilidad
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[#10231f] sm:text-4xl">
            ¿Qué necesita decidir?
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#63716c]">
            El prototipo recupera fragmentos curados y muestra límites de alcance.
            No genera recomendaciones cuando no encuentra una fuente suficiente.
          </p>
        </div>
        <span className="rounded-full border border-[#bed0c8] bg-[#edf5f1] px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[#2b6b5f]">
          Corpus local · 6 fragmentos
        </span>
      </div>

      <form
        onSubmit={submit}
        className="clinical-shadow mt-7 rounded-[1.5rem] border border-[#d8ddd7] bg-[#fbfaf6] p-3"
      >
        <textarea
          aria-label="Pregunta clínica"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          rows={3}
          className="w-full resize-none rounded-xl bg-transparent px-3 py-3 text-[15px] leading-7 text-[#17332d] outline-none placeholder:text-[#98a29f]"
          placeholder="Describa edad, síntomas, tiempo de evolución, signos vitales y contexto..."
        />
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#e3e6e1] px-2 pt-3">
          <div className="flex items-center gap-2 text-xs text-[#75817d]">
            <Icon name="shield" className="h-4 w-4 text-[#2b6b5f]" />
            Sin datos identificables del paciente
          </div>
          <button
            type="submit"
            className="inline-flex items-center gap-2 rounded-full bg-[#10231f] px-5 py-2.5 text-sm font-bold text-white transition hover:bg-[#20453c] focus:outline-none focus:ring-2 focus:ring-[#2b6b5f] focus:ring-offset-2"
          >
            Consultar evidencia
            <Icon name="send" className="h-4 w-4" />
          </button>
        </div>
      </form>

      <div className="mt-3 flex gap-2 overflow-x-auto pb-2 thin-scrollbar">
        {EXAMPLE_QUERIES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => {
              setQuery(example);
              setResponse(analyzeClinicalQuery(example));
            }}
            className="shrink-0 rounded-full border border-[#d7ddd7] bg-white px-3.5 py-2 text-xs font-semibold text-[#576660] transition hover:border-[#9db7ac] hover:text-[#205348]"
          >
            {example.length > 48 ? `${example.slice(0, 48)}…` : example}
          </button>
        ))}
      </div>

      <article className="clinical-shadow mt-6 overflow-hidden rounded-[1.5rem] border border-[#d8ddd7] bg-[#fbfaf6]">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#dde2dc] px-5 py-5 sm:px-7">
          <div className="flex items-start gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#d9ed7f] text-[#17332d]">
              <Icon name="spark" className="h-5 w-5" />
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base font-bold text-[#17332d]">
                  Síntesis de evidencia
                </h2>
                <ConfidenceBadge confidence={response.confidence} />
              </div>
              <p className="mt-1 text-sm leading-6 text-[#60706a]">
                {response.summary}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={copyNote}
            className="inline-flex items-center gap-2 rounded-full border border-[#ccd5d0] bg-white px-3.5 py-2 text-xs font-bold text-[#40544d] transition hover:border-[#8fa99f]"
          >
            <Icon
              name={copied ? "check" : "copy"}
              className="h-3.5 w-3.5"
            />
            {copied ? "Copiado" : "Copiar borrador"}
          </button>
        </div>

        {response.safetyAlert && (
          <div
            className={`mx-5 mt-5 flex gap-3 rounded-2xl border p-4 sm:mx-7 ${
              response.safetyAlert.level === "emergency"
                ? "border-[#e3ad9c] bg-[#fff2ed] text-[#84371f]"
                : "border-[#dfc572] bg-[#fff9df] text-[#725718]"
            }`}
          >
            <Icon name="error" className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="text-sm font-extrabold">
                {response.safetyAlert.title}
              </p>
              <p className="mt-1 text-sm leading-6">
                {response.safetyAlert.message}
              </p>
            </div>
          </div>
        )}

        <div className="grid gap-4 p-5 sm:p-7 lg:grid-cols-2">
          <SectionList
            title="Conducta para revisión"
            icon="activity"
            items={response.conduct}
            tone="mint"
          />
          <SectionList
            title="Signos de alarma"
            icon="error"
            items={response.redFlags}
            tone="danger"
          />
          <SectionList
            title="Qué documentar"
            icon="clipboard"
            items={response.documentation}
          />
          <SectionList
            title="Errores a evitar"
            icon="shield"
            items={response.commonErrors}
          />
        </div>

        <div className="border-t border-[#dde2dc] bg-[#f5f6f1] px-5 py-6 sm:px-7">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-[#17332d]">
              Fuentes recuperadas
            </h3>
            <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-[#75817d]">
              Citas obligatorias · orden por relevancia
            </p>
          </div>
          {response.evidence.length > 0 ? (
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              {response.evidence.map((source, index) => (
                <SourceCard
                  key={source.chunk.id}
                  source={source}
                  rank={index + 1}
                />
              ))}
            </div>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed border-[#c8d0cb] bg-white/70 p-5 text-sm leading-6 text-[#61706b]">
              No se recuperaron fuentes con score suficiente. El sistema se
              abstiene de completar la respuesta.
            </div>
          )}
          {response.limitation && (
            <p className="mt-4 flex gap-2 text-xs leading-5 text-[#6d7874]">
              <span className="font-mono font-bold text-[#9a4d31]">
                LÍMITE
              </span>
              {response.limitation}
            </p>
          )}
        </div>
      </article>
    </div>
  );
}

function ChecklistWorkspace() {
  const [selectedDisease, setSelectedDisease] = useState("hypertension");
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const source =
    evidenceChunks.find((chunk) => chunk.diseaseId === selectedDisease) ??
    evidenceChunks[0];
  const groups = [
    { title: "Preguntar", items: source.tags.slice(0, 5), icon: "search" as const },
    { title: "Signos de alarma", items: source.redFlags, icon: "error" as const },
    {
      title: "Registrar",
      items: source.documentation,
      icon: "clipboard" as const
    },
    {
      title: "Cerrar la consulta",
      items: [
        "Explique la conducta y confirme comprensión.",
        "Entregue signos de alarma y ruta de consulta.",
        "Defina seguimiento, responsable y ventana de control."
      ],
      icon: "check" as const
    }
  ];
  const total = groups.reduce((count, group) => count + group.items.length, 0);

  const toggle = (key: string) => {
    setChecked((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="fade-up">
      <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#2b6b5f]">
        Checklist de consulta
      </p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">
            Que lo importante no se escape.
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#63716c]">
            Plantillas derivadas del corpus demostrativo. Son ayudas de memoria,
            no órdenes clínicas.
          </p>
        </div>
        <div className="rounded-full bg-[#10231f] px-4 py-2 font-mono text-xs text-white">
          {checked.size}/{total} revisados
        </div>
      </div>

      <div className="mt-7 grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="rounded-2xl border border-[#d8ddd7] bg-[#fbfaf6] p-3">
          {evidenceChunks.map((chunk) => (
            <button
              key={chunk.id}
              type="button"
              onClick={() => {
                setSelectedDisease(chunk.diseaseId);
                setChecked(new Set());
              }}
              className={`flex w-full items-center justify-between rounded-xl px-3 py-3 text-left text-sm font-semibold transition ${
                selectedDisease === chunk.diseaseId
                  ? "bg-[#dceae4] text-[#205348]"
                  : "text-[#61706b] hover:bg-[#f0f2ed]"
              }`}
            >
              {getDiseaseName(chunk.diseaseId)}
              <Icon name="arrow" className="h-4 w-4" />
            </button>
          ))}
        </aside>

        <section className="clinical-shadow overflow-hidden rounded-[1.5rem] border border-[#d8ddd7] bg-[#fbfaf6]">
          <div className="border-b border-[#dde2dc] p-6">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-[#d9ed7f] px-3 py-1 font-mono text-[10px] font-bold uppercase tracking-[0.12em]">
                {source.sourceType} · {source.year}
              </span>
              <ConfidenceBadge confidence={source.confidence} />
            </div>
            <h2 className="mt-4 text-2xl font-bold tracking-[-0.03em]">
              {getDiseaseName(source.diseaseId)}
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#63716c]">
              Alcance: {source.scope}
            </p>
          </div>
          <div className="grid gap-px bg-[#dfe3de] md:grid-cols-2">
            {groups.map((group) => (
              <div key={group.title} className="bg-[#fbfaf6] p-6">
                <div className="flex items-center gap-2">
                  <Icon
                    name={group.icon}
                    className="h-4 w-4 text-[#2b6b5f]"
                  />
                  <h3 className="text-sm font-extrabold">{group.title}</h3>
                </div>
                <div className="mt-4 space-y-2">
                  {group.items.map((item, index) => {
                    const key = `${group.title}-${index}`;
                    const isChecked = checked.has(key);
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => toggle(key)}
                        className={`flex w-full gap-3 rounded-xl border p-3 text-left text-sm leading-5 transition ${
                          isChecked
                            ? "border-[#a9c8ba] bg-[#eaf4ef] text-[#36544a]"
                            : "border-[#e0e4df] bg-white text-[#5d6a66] hover:border-[#b9c9c1]"
                        }`}
                      >
                        <span
                          className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md border ${
                            isChecked
                              ? "border-[#2b6b5f] bg-[#2b6b5f] text-white"
                              : "border-[#bdc7c2]"
                          }`}
                        >
                          {isChecked && (
                            <Icon name="check" className="h-3 w-3" />
                          )}
                        </span>
                        <span>{item}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function ErrorWorkspace() {
  const [text, setText] = useState(DEFAULT_ERROR_TEXT);
  const [analysis, setAnalysis] = useState(() =>
    detectClinicalErrors(DEFAULT_ERROR_TEXT)
  );

  return (
    <div className="fade-up">
      <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#2b6b5f]">
        Detector de errores
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">
        Una segunda mirada antes de firmar.
      </h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-[#63716c]">
        Describe una conducta en lenguaje libre. El motor identifica patrones
        de riesgo, omisiones frecuentes y puntos para reevaluar.
      </p>

      <div className="mt-7 grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <section className="clinical-shadow rounded-[1.5rem] border border-[#d8ddd7] bg-[#fbfaf6] p-5 sm:p-6">
          <label
            htmlFor="error-statement"
            className="text-sm font-extrabold text-[#17332d]"
          >
            Conducta que desea revisar
          </label>
          <textarea
            id="error-statement"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={9}
            className="mt-3 w-full resize-none rounded-2xl border border-[#d9ded8] bg-white p-4 text-sm leading-7 text-[#334942] outline-none transition focus:border-[#6f9989] focus:ring-2 focus:ring-[#dceae4]"
          />
          <button
            type="button"
            onClick={() => setAnalysis(detectClinicalErrors(text))}
            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#10231f] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#20453c]"
          >
            <Icon name="shield" className="h-4 w-4" />
            Revisar conducta
          </button>
          <p className="mt-4 text-xs leading-5 text-[#78837f]">
            El detector usa reglas transparentes. Un resultado vacío no
            demuestra que la conducta sea segura.
          </p>
        </section>

        <section className="space-y-4">
          {analysis.length > 0 ? (
            analysis.map((error, index) => (
              <article
                key={error.id}
                className="clinical-shadow overflow-hidden rounded-[1.5rem] border border-[#e5c6bb] bg-[#fff9f6]"
              >
                <div className="flex gap-4 p-5 sm:p-6">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#bc4d2b] font-mono text-sm font-bold text-white">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-extrabold text-[#632b1b]">
                        {error.title}
                      </h2>
                      <span className="rounded-full bg-[#f2d8cf] px-2 py-1 font-mono text-[9px] font-bold uppercase tracking-[0.14em] text-[#8d3d25]">
                        {error.severity}
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-[#754c40]">
                      {error.warning}
                    </p>
                    <div className="mt-4 rounded-xl border border-[#edcfc4] bg-white/70 p-3 text-sm font-semibold leading-6 text-[#643c31]">
                      <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[#a05037]">
                        Acción
                      </span>
                      <p className="mt-1">{error.action}</p>
                    </div>
                  </div>
                </div>
              </article>
            ))
          ) : (
            <div className="grid min-h-80 place-items-center rounded-[1.5rem] border border-dashed border-[#c8d0cb] bg-white/50 p-8 text-center">
              <div>
                <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-[#e5eee9] text-[#2b6b5f]">
                  <Icon name="search" />
                </span>
                <h2 className="mt-4 font-bold">Sin patrón conocido</h2>
                <p className="mt-2 max-w-sm text-sm leading-6 text-[#6a7772]">
                  No hubo coincidencia con la taxonomía local. Esto no equivale
                  a una validación clínica.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function GuidesWorkspace() {
  const [search, setSearch] = useState("");
  const [type, setType] = useState("Todas");
  const filtered = useMemo(() => {
    const normalized = search.toLocaleLowerCase("es");
    return evidenceChunks.filter((chunk) => {
      const matchesType = type === "Todas" || chunk.sourceType === type;
      const matchesSearch = [
        chunk.title,
        chunk.institution,
        chunk.scope,
        getDiseaseName(chunk.diseaseId)
      ]
        .join(" ")
        .toLocaleLowerCase("es")
        .includes(normalized);
      return matchesType && matchesSearch;
    });
  }, [search, type]);

  return (
    <div className="fade-up">
      <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#2b6b5f]">
        Biblioteca clínica
      </p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">
            La fuente antes que la respuesta.
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#63716c]">
            Cada fragmento registra institución, año, página, alcance y enlace
            oficial. El corpus actual es demostrativo y deliberadamente pequeño.
          </p>
        </div>
        <a
          href="https://www.sispro.gov.co/observatorios/oncalidadsalud/Paginas/Linea-Tematicas.aspx"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-full border border-[#bccbc4] bg-white px-4 py-2.5 text-xs font-bold text-[#40544d] transition hover:border-[#7d9b8f]"
        >
          Repositorio oficial SISPRO
          <Icon name="external" className="h-3.5 w-3.5" />
        </a>
      </div>

      <div className="mt-7 flex flex-col gap-3 rounded-2xl border border-[#d8ddd7] bg-[#fbfaf6] p-3 sm:flex-row">
        <label className="flex flex-1 items-center gap-3 rounded-xl border border-[#dfe3de] bg-white px-4">
          <Icon name="search" className="h-4 w-4 text-[#74817d]" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar enfermedad, institución o alcance..."
            className="min-w-0 flex-1 bg-transparent py-3 text-sm outline-none"
          />
          {search && (
            <button
              type="button"
              aria-label="Limpiar búsqueda"
              onClick={() => setSearch("")}
              className="text-[#77837f]"
            >
              <Icon name="x" className="h-4 w-4" />
            </button>
          )}
        </label>
        <div className="flex gap-2">
          {["Todas", "GPC", "RIAS"].map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setType(item)}
              className={`rounded-xl px-4 py-2 text-xs font-bold transition ${
                type === item
                  ? "bg-[#10231f] text-white"
                  : "bg-[#edf0ec] text-[#62716c] hover:bg-[#e2e8e4]"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((chunk, index) => (
          <a
            key={chunk.id}
            href={chunk.sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="clinical-shadow group flex min-h-72 flex-col rounded-[1.4rem] border border-[#d8ddd7] bg-[#fbfaf6] p-5 transition hover:-translate-y-1 hover:border-[#9fb8ae]"
          >
            <div className="flex items-start justify-between">
              <span className="font-mono text-xs font-semibold text-[#82908b]">
                {String(index + 1).padStart(2, "0")} /{" "}
                {chunk.sourceType.toUpperCase()}
              </span>
              <Icon
                name="external"
                className="h-4 w-4 text-[#8b9893] transition group-hover:text-[#2b6b5f]"
              />
            </div>
            <p className="mt-7 font-mono text-[10px] font-bold uppercase tracking-[0.15em] text-[#2b6b5f]">
              {getDiseaseName(chunk.diseaseId)}
            </p>
            <h2 className="mt-2 text-lg font-extrabold leading-6 tracking-[-0.02em]">
              {chunk.title}
            </h2>
            <p className="mt-3 line-clamp-3 text-sm leading-6 text-[#64716d]">
              {chunk.scope}
            </p>
            <div className="mt-auto border-t border-[#e0e4df] pt-4">
              <p className="text-xs font-semibold text-[#4d5e58]">
                {chunk.institution}
              </p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.1em] text-[#87938f]">
                {chunk.year} · {chunk.page ? `página ${chunk.page}` : "web"} ·
                certeza {chunk.confidence}
              </p>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

function Sidebar({
  activeTab,
  setActiveTab
}: {
  activeTab: Tab;
  setActiveTab: (tab: Tab) => void;
}) {
  const priorities = diseases.slice(0, 6);

  return (
    <aside className="border-r border-[#d7ddd7] bg-[#ebece6]/80 px-4 py-6 backdrop-blur-sm max-[900px]:border-b max-[900px]:border-r-0 max-[900px]:py-3">
      <nav
        aria-label="Navegación principal"
        className="space-y-1 max-[900px]:flex max-[900px]:gap-2 max-[900px]:overflow-x-auto max-[900px]:space-y-0 max-[900px]:pb-1 thin-scrollbar"
      >
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setActiveTab(item.id)}
            className={`group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition max-[900px]:w-auto max-[900px]:shrink-0 ${
              activeTab === item.id
                ? "bg-[#10231f] text-white shadow-sm"
                : "text-[#5f6d68] hover:bg-white/70 hover:text-[#17332d]"
            }`}
          >
            <Icon name={item.icon} className="h-4 w-4" />
            <span>
              <span className="block text-sm font-bold">{item.label}</span>
              <span
                className={`block font-mono text-[9px] uppercase tracking-[0.14em] max-[900px]:hidden ${
                  activeTab === item.id ? "text-[#b9cdc5]" : "text-[#8b9692]"
                }`}
              >
                {item.kicker}
              </span>
            </span>
          </button>
        ))}
      </nav>

      <div className="mt-8 max-[900px]:hidden">
        <div className="flex items-center justify-between px-2">
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-[#798580]">
            Mapa de prioridad
          </p>
          <span className="h-2 w-2 rounded-full bg-[#d9ed7f] ring-4 ring-[#d9ed7f]/25" />
        </div>
        <div className="mt-3 space-y-1">
          {priorities.map((disease) => (
            <div
              key={disease.id}
              className="flex items-center justify-between rounded-lg px-2 py-2.5 text-xs"
            >
              <span className="font-semibold text-[#53625d]">
                {disease.name}
              </span>
              <span
                className={`h-1.5 w-8 rounded-full ${
                  disease.priority === "critica"
                    ? "bg-[#bc4d2b]"
                    : disease.priority === "alta"
                      ? "bg-[#d7a33f]"
                      : "bg-[#739b8c]"
                }`}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8 rounded-2xl bg-[#dceae4] p-4 max-[900px]:hidden">
        <div className="flex items-center gap-2 text-[#205348]">
          <Icon name="shield" className="h-4 w-4" />
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.12em]">
            Entorno demo
          </span>
        </div>
        <p className="mt-3 text-xs leading-5 text-[#46665b]">
          Sin historia clínica, sin autenticación y sin datos de pacientes.
        </p>
      </div>
    </aside>
  );
}

export function ClinicalCopilot() {
  const [activeTab, setActiveTab] = useState<Tab>("consulta");

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 flex h-[4.5rem] items-center justify-between border-b border-[#d5dbd5] bg-[#f3f1ea]/90 px-4 backdrop-blur-xl sm:px-6">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#10231f] text-[#d9ed7f]">
            <Icon name="heart" className="h-5 w-5" />
          </span>
          <div>
            <p className="text-base font-extrabold tracking-[-0.03em]">
              Criterio
            </p>
            <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[#6c7974]">
              Copiloto clínico colombiano
            </p>
          </div>
        </div>

        <div className="hidden items-center gap-3 sm:flex">
          <div className="flex items-center gap-2 rounded-full border border-[#ccd6d1] bg-white/70 px-3 py-2">
            <span className="h-2 w-2 rounded-full bg-[#5da979]" />
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.1em] text-[#5d6c66]">
              Fuentes verificables
            </span>
          </div>
          <span className="rounded-full bg-[#e2e5df] px-3 py-2 font-mono text-[10px] font-bold text-[#5f6d68]">
            MVP 0.1
          </span>
        </div>
        <button
          type="button"
          aria-label="Abrir navegación"
          className="grid h-10 w-10 place-items-center rounded-xl border border-[#d2d8d3] sm:hidden"
        >
          <Icon name="menu" className="h-5 w-5" />
        </button>
      </header>

      <div className="app-grid">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <main className="min-w-0 px-4 py-7 sm:px-7 sm:py-9 xl:px-10">
          <div className="mx-auto max-w-[92rem]">
            {activeTab === "consulta" && <QueryWorkspace />}
            {activeTab === "checklists" && <ChecklistWorkspace />}
            {activeTab === "errores" && <ErrorWorkspace />}
            {activeTab === "guias" && <GuidesWorkspace />}
          </div>
        </main>
      </div>

      <footer className="border-t border-[#d6dcd6] bg-[#10231f] px-5 py-5 text-[#b9c8c3]">
        <div className="mx-auto flex max-w-[92rem] flex-col gap-2 text-xs leading-5 sm:flex-row sm:items-center sm:justify-between">
          <p>
            <strong className="text-white">No reemplaza el juicio clínico.</strong>{" "}
            Prototipo para evaluación técnica y médica, no para uso asistencial.
          </p>
          <p className="font-mono text-[10px] uppercase tracking-[0.12em]">
            Colombia · fuentes oficiales enlazadas
          </p>
        </div>
      </footer>
    </div>
  );
}

