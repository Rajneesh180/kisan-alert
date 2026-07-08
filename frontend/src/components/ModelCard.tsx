import { X } from "lucide-react";
import { useEffect } from "react";
import type { Lang, NdviEval } from "../api";
import { t } from "../i18n";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-stone-100 px-5 py-4">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">{title}</div>
      {children}
    </div>
  );
}

export default function ModelCard({
  metrics,
  lang,
  onClose,
}: {
  metrics: NdviEval;
  lang: Lang;
  onClose: () => void;
}) {
  // Escape closes; lock body scroll while the dialog is open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const topFeatures = new Set(metrics.top_drivers.map((d) => d.feature));
  const stats = [
    { k: `+${metrics.skill_vs_persistence_pct}%`, l: t("ndviSkill", lang), hi: true },
    { k: metrics.model_rmse.toFixed(3), l: t("mcRmseModel", lang) },
    { k: metrics.persistence_rmse.toFixed(3), l: t("mcRmseBase", lang) },
    { k: String(metrics.n_samples), l: t("mcWindows", lang) },
    { k: String(metrics.n_plots), l: t("ndviPlots", lang) },
    { k: String(metrics.horizon_days), l: t("mcHorizon", lang) },
  ];
  const limits = [t("mcLimit1", lang), t("mcLimit2", lang), t("mcLimit3", lang)];

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label={t("mcTitle", lang)}
      onClick={onClose}
    >
      <div
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 flex items-start justify-between gap-3 border-b border-stone-100 bg-white px-5 py-4">
          <div>
            <h2 className="font-display text-lg font-bold text-stone-900">{t("mcTitle", lang)}</h2>
            <p className="mt-0.5 text-xs text-stone-500">
              {metrics.model} · {metrics.cv}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label={t("close", lang)}
            className="rounded-lg p-1.5 text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-5 py-4 text-sm leading-relaxed text-stone-600">{t("mcTask", lang)}</div>

        <Section title={t("mcPerf", lang)}>
          <div className="grid grid-cols-3 gap-2">
            {stats.map((s) => (
              <div
                key={s.l}
                className={`rounded-lg border p-2.5 text-center ${
                  s.hi ? "border-brand-200 bg-brand-50" : "border-stone-200"
                }`}
              >
                <div
                  className={`text-lg font-bold tabular-nums ${s.hi ? "text-brand-800" : "text-stone-900"}`}
                >
                  {s.k}
                </div>
                <div className="mt-0.5 text-[10.5px] leading-tight text-stone-500">{s.l}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs leading-relaxed text-stone-500">{t("mcTestBody", lang)}</p>
        </Section>

        <Section title={t("mcInputs", lang)}>
          <div className="flex flex-wrap gap-1.5">
            {metrics.features.map((f) => {
              const top = topFeatures.has(f.feature);
              return (
                <span
                  key={f.feature}
                  className={`rounded-full px-2.5 py-1 text-xs ${
                    top
                      ? "bg-brand-100 font-medium text-brand-800"
                      : "bg-stone-100 text-stone-600"
                  }`}
                >
                  {f.label}
                </span>
              );
            })}
          </div>
          <p className="mt-2 text-[11px] text-stone-500">{t("mcInputsNote", lang)}</p>
        </Section>

        <Section title={t("mcLimits", lang)}>
          <ul className="space-y-1.5">
            {limits.map((l) => (
              <li key={l} className="flex gap-2 text-xs leading-relaxed text-stone-600">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-stone-400" />
                {l}
              </li>
            ))}
          </ul>
        </Section>

        <Section title={t("mcData", lang)}>
          <p className="text-xs leading-relaxed text-stone-600">{t("mcDataBody", lang)}</p>
        </Section>
      </div>
    </div>
  );
}
