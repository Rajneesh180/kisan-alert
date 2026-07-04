import { Activity, TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Lang, type NdviEval, type NdviForecast, type Plot } from "../api";
import { t } from "../i18n";
import Skeleton from "./Skeleton";

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

          {metrics && (
            <p className="mt-2.5 border-t border-stone-100 pt-2 text-[11px] leading-relaxed text-stone-500">
              {metrics.model} · +{metrics.skill_vs_persistence_pct}% {t("ndviSkill", lang)} ({metrics.cv},{" "}
              {metrics.n_plots} {t("ndviPlots", lang)})
              {metrics.top_drivers[0] && (
                <>
                  {" · "}
                  {t("ndviDriver", lang)}: {metrics.top_drivers[0].label}
                </>
              )}
            </p>
          )}
        </>
      )}
    </div>
  );
}
