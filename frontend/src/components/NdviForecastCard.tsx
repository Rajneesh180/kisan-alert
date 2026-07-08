import { Activity, TrendingDown, TrendingUp, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Lang, type NdviEval, type NdviForecast, type Plot } from "../api";
import { t } from "../i18n";
import ModelCard from "./ModelCard";
import Skeleton from "./Skeleton";

const REASON_KEY: Record<string, string> = {
  drop: "stressReasonDrop",
  seasonal: "stressReasonSeasonal",
  both: "stressReasonBoth",
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Parse the ISO date by hand so the label never drifts a day across timezones.
function fmtDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]}`;
}

function Bar({ value, stress }: { value: number; stress?: boolean }) {
  return (
    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-stone-100">
      <div
        className={`h-full rounded-full ${stress ? "bg-amber-500" : "bg-brand-600"}`}
        style={{ width: `${Math.max(4, Math.min(100, value * 100))}%` }}
      />
    </div>
  );
}

export default function NdviForecastCard({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [data, setData] = useState<NdviForecast | null>(null);
  const [metrics, setMetrics] = useState<NdviEval | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [cardOpen, setCardOpen] = useState(false);

  useEffect(() => {
    setData(null);
    setUnavailable(false);
    api.ndviForecast(plot.id).then(setData).catch(() => setUnavailable(true));
  }, [plot.id]);

  useEffect(() => {
    api.ndviEval().then(setMetrics).catch(() => setMetrics(null));
  }, []);

  // Model untrained or too little history for this plot — hide rather than error.
  if (unavailable) return null;

  const up = data ? data.delta >= 0 : false;

  return (
    <div className="card card-hover">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-1.5 font-semibold text-stone-900">
          <Activity className="h-4 w-4 text-brand-700" />
          {t("ndviTitle", lang)}
        </h2>
        {data?.stress_warning && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
            {t("ndviStress", lang)}
          </span>
        )}
      </div>
      <p className="mt-0.5 text-xs text-stone-500">{t("ndviSub", lang)}</p>

      {!data && <Skeleton rows={2} />}

      {data && (
        <>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <div className="rounded-lg border border-stone-200 p-2.5">
              <div className="text-xs text-stone-500">
                {t("ndviLatest", lang)} · {fmtDate(data.current_date)}
              </div>
              <div className="mt-0.5 font-semibold text-stone-900">NDVI {data.current_ndvi.toFixed(2)}</div>
              <Bar value={data.current_ndvi} />
            </div>
            <div className="rounded-lg border border-stone-200 p-2.5">
              <div className="text-xs text-stone-500">
                {t("ndviProjected", lang)} · {fmtDate(data.predicted_date)}
              </div>
              <div className="mt-0.5 flex items-center gap-1 font-semibold text-stone-900">
                NDVI {data.predicted_ndvi.toFixed(2)}
                <span className={`inline-flex items-center text-xs ${up ? "text-brand-600" : "text-amber-600"}`}>
                  {up ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                  {data.delta >= 0 ? "+" : ""}
                  {data.delta.toFixed(2)}
                </span>
              </div>
              <Bar value={data.predicted_ndvi} stress={data.stress_warning} />
            </div>
          </div>

          {data.baseline_ndvi !== null && (
            <p className="mt-2 text-xs text-stone-500">
              {t("ndviVsSeason", lang)} {data.baseline_ndvi.toFixed(2)}
              {" ("}
              {data.predicted_ndvi - data.baseline_ndvi >= 0 ? "+" : ""}
              {(data.predicted_ndvi - data.baseline_ndvi).toFixed(2)}
              {")"}
            </p>
          )}

          {data.stress_warning && data.stress_reason && (
            <div className="mt-2.5 flex items-start gap-1.5 rounded-lg bg-amber-50 p-2 text-xs text-amber-800">
              <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{t(REASON_KEY[data.stress_reason], lang)}</span>
            </div>
          )}

          {data.drivers.length > 0 && (
            <div className="mt-2.5 rounded-lg bg-stone-50 p-2.5">
              <div className="text-xs font-medium text-stone-700">{t("ndviWhy", lang)}</div>
              <div className="mt-1.5 space-y-1">
                {data.drivers.map((dr) => {
                  const down = dr.effect < 0;
                  return (
                    <div
                      key={dr.feature}
                      className="flex items-center justify-between gap-2 text-xs"
                      title={`${dr.value.toFixed(2)} · ${t(dr.direction, lang)} (${dr.typical.toFixed(2)})`}
                    >
                      <span className="text-stone-600">{dr.label}</span>
                      <span
                        className={`inline-flex items-center gap-0.5 font-medium tabular-nums ${
                          down ? "text-amber-700" : "text-brand-700"
                        }`}
                      >
                        {down ? (
                          <TrendingDown className="h-3.5 w-3.5" />
                        ) : (
                          <TrendingUp className="h-3.5 w-3.5" />
                        )}
                        {dr.effect >= 0 ? "+" : ""}
                        {dr.effect.toFixed(2)}
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="mt-1.5 text-[10px] leading-relaxed text-stone-500">
                {t("ndviWhyNote", lang)}
              </div>
            </div>
          )}

          {metrics && (
            <div className="mt-2.5 flex items-center justify-between gap-2 border-t border-stone-100 pt-2">
              <p className="text-[11px] leading-relaxed text-stone-500">
                {metrics.model} · +{metrics.skill_vs_persistence_pct}% {t("ndviSkill", lang)} (
                {metrics.n_plots} {t("ndviPlots", lang)})
              </p>
              <button
                onClick={() => setCardOpen(true)}
                className="shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-medium text-brand-700 underline-offset-2 hover:underline"
              >
                {t("modelCard", lang)}
              </button>
            </div>
          )}
        </>
      )}

      {cardOpen && metrics && (
        <ModelCard metrics={metrics} lang={lang} onClose={() => setCardOpen(false)} />
      )}
    </div>
  );
}
