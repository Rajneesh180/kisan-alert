import { FlaskConical, Info } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type FertilizerPlan, type Lang, type Plot } from "../api";
import { t } from "../i18n";
import Skeleton from "./Skeleton";

const OC_TINT: Record<string, string> = {
  low: "bg-amber-100 text-amber-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-brand-100 text-brand-700",
};

export default function FertilizerCard({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [plan, setPlan] = useState<FertilizerPlan | null>(null);

  useEffect(() => {
    setPlan(null);
    api.fertilizer(plot.id).then(setPlan).catch(() => setPlan(null));
  }, [plot.id]);

  if (!plan)
    return (
      <div className="card card-hover">
        <h2 className="flex items-center gap-1.5 font-semibold text-stone-900">
          <FlaskConical className="h-4 w-4 text-brand-700" />
          {t("fertilizer", lang)}
        </h2>
        <Skeleton rows={3} />
      </div>
    );

  const ocLabel = plan.oc_status ? t(`oc${plan.oc_status[0].toUpperCase()}${plan.oc_status.slice(1)}`, lang) : "—";
  const bags: [string, number][] = [
    [t("ureaLabel", lang), plan.urea_kg_ha],
    [t("dapLabel", lang), plan.dap_kg_ha],
    [t("mopLabel", lang), plan.mop_kg_ha],
  ];

  return (
    <div className="card card-hover">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-1.5 font-semibold text-stone-900">
          <FlaskConical className="h-4 w-4 text-brand-700" />
          {t("fertilizer", lang)}
        </h2>
        <span className="text-xs text-stone-500">{plan.crop_label[lang]}</span>
      </div>

      {plan.oc_pct != null && (
        <div className="mt-2 flex items-center gap-2 text-xs">
          <span className="text-stone-500">{t("organicCarbon", lang)}</span>
          <span className={`rounded-full px-2 py-0.5 font-medium ${OC_TINT[plan.oc_status ?? ""]}`}>
            {ocLabel} · {plan.oc_pct}%
          </span>
          <span className="text-stone-500">pH {plan.ph ?? "—"}</span>
        </div>
      )}

      <div className="mt-3 grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-stone-200 bg-stone-200 text-center">
        {plan.doses.map((d) => (
          <div key={d.nutrient} className="bg-white px-2 py-2.5">
            <div className="text-base font-semibold text-stone-900">{d.kg_ha}</div>
            <div className="text-[10px] uppercase tracking-wide text-stone-500">
              {d.nutrient} kg/ha
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3">
        <div className="mb-1 text-[10px] uppercase tracking-wide text-stone-500">
          {t("bagsNote", lang)}
        </div>
        <div className="flex flex-wrap gap-2">
          {bags
            .filter(([, v]) => v > 0)
            .map(([label, v]) => (
              <span
                key={label}
                className="rounded-lg bg-brand-50 px-2.5 py-1 text-xs text-brand-900"
              >
                {label} <span className="font-semibold">{v}</span> kg/ha
              </span>
            ))}
        </div>
      </div>

      {plan.amendments.length > 0 && (
        <ul className="mt-3 space-y-1">
          {plan.amendments.map((a, i) => (
            <li key={i} className="flex gap-1.5 rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800">
              <Info className="mt-0.5 h-3 w-3 shrink-0" />
              {a}
            </li>
          ))}
        </ul>
      )}

      {plan.notes.length > 0 && (
        <p className="mt-2 text-[11px] leading-relaxed text-stone-500">{plan.notes.join(" · ")}</p>
      )}
      <p className="mt-2 text-[10px] text-stone-500">{plan.source}</p>
    </div>
  );
}
