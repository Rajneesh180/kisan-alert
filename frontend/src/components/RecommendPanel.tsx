import { useEffect, useState } from "react";
import { api, type Lang, type Plot, type RecommendResponse } from "../api";
import { t } from "../i18n";
import Skeleton from "./Skeleton";

export default function RecommendPanel({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [data, setData] = useState<RecommendResponse | null>(null);

  useEffect(() => {
    setData(null);
    api.recommend(plot.id).then(setData).catch(() => setData(null));
  }, [plot.id]);

  if (!data)
    return (
      <div className="card card-hover">
        <h2 className="font-semibold text-stone-900">{t("recommendations", lang)}</h2>
        <Skeleton rows={4} />
      </div>
    );

  return (
    <div className="card card-hover">
      <div className="flex items-baseline justify-between">
        <h2 className="font-semibold text-stone-900">{t("recommendations", lang)}</h2>
        <span className="text-xs text-stone-600">
          {data.season} · {t("seasonRain", lang)}: {Math.round(data.season_rain_mm)} mm
        </span>
      </div>
      <ul className="mt-3 space-y-2">
        {data.recommendations.slice(0, 6).map((r) => (
          <li
            key={r.crop}
            className="rounded-lg border border-stone-100 p-2 transition-colors hover:bg-stone-50"
          >
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                {r.labels[lang]}
                {r.is_current && (
                  <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] text-blue-800">
                    {t("currentCrop", lang)}
                  </span>
                )}
              </span>
              <span className="font-mono text-brand-800">{(r.score * 100).toFixed(0)}</span>
            </div>
            <div className="mt-1 h-1.5 w-full rounded bg-stone-100">
              <div
                className="h-1.5 rounded bg-brand-600"
                style={{ width: `${Math.round(r.score * 100)}%` }}
              />
            </div>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-stone-500">
              <span>water {r.breakdown.water}</span>
              <span>groundwater {r.breakdown.groundwater}</span>
              <span>pH {r.breakdown.ph}</span>
              <span>soil {r.breakdown.texture}</span>
              <span className="text-stone-500">
                {t("needs", lang)} {Math.round(r.water_need_mm)} mm · {t("available", lang)} ~
                {Math.round(r.water_available_mm)} mm
              </span>
            </div>
            {r.reasons.length > 0 && (
              <p className="mt-1 text-[11px] text-red-700">{r.reasons.join("; ")}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
