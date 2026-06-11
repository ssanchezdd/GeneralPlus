import Link from "next/link";

export default function NotFound() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#f3f1ea] px-6">
      <section className="max-w-lg text-center">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-[#2b6b5f]">
          404 / Ruta no encontrada
        </p>
        <h1 className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-[#10231f]">
          Esta página no está en la ruta clínica.
        </h1>
        <p className="mt-4 text-[#63716c]">
          Regresa al tablero para consultar el corpus demostrativo.
        </p>
        <Link
          href="/"
          className="mt-7 inline-flex rounded-full bg-[#10231f] px-5 py-3 text-sm font-semibold text-white"
        >
          Volver al inicio
        </Link>
      </section>
    </main>
  );
}

