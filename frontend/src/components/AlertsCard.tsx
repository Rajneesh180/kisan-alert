import { Droplets, MessageSquareText, Satellite, Sun, TriangleAlert } from "lucide-react";
import type { ComponentType } from "react";
import { useEffect, useState } from "react";
import { api, type Alert, type AlertsResponse, type Lang, type Plot } from "../api";
import { t } from "../i18n";
import Skeleton from "./Skeleton";

// Per-severity accent kept within the app's green-yellow palette: green = clear,
// yellow = watch, amber = act now (no clashing red).
const SEVERITY = {
  severe: { stripe: "border-l-amber-500", chip: "bg-amber-100 text-amber-700", label: "text-amber-700" },
  urgent: { stripe: "border-l-amber-500", chip: "bg-amber-100 text-amber-700", label: "text-amber-700" },
  moderate: {
    stripe: "border-l-yellow-400",
    chip: "bg-yellow-100 text-yellow-700",
    label: "text-yellow-700",
  },
  light: {
    stripe: "border-l-yellow-400",
    chip: "bg-yellow-100 text-yellow-700",
    label: "text-yellow-700",
  },
} as const;

const ALERT_ICONS: Record<string, ComponentType<{ className?: string }>> = {
  dry_spell: Sun,
  irrigation: Droplets,
  crop_stress: Satellite,
};

function smsSegments(text: string): number {
  const per = /^[\x00-\x7F]*$/.test(text) ? 160 : 70;
  return Math.max(1, Math.ceil(text.length / per));
}

function alertDetail(a: Alert, lang: Lang): string {
  if (a.type === "dry_spell") return `${a.length_days as number} ${t("detail_dry_spell", lang)}`;
  if (a.type === "irrigation")
    return `~${Math.round(a.irrigation_mm as number)} ${t("detail_irrigation", lang)}`;
  if (a.type === "crop_stress") return t("detail_crop_stress", lang);
  return "";
}

export default function AlertsCard({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [mode, setMode] = useState<"live" | "replay">("live");
  const [data, setData] = useState<AlertsResponse | null>(null);

  useEffect(() => {
    setData(null);
    api.alerts(plot.id, mode).then(setData).catch(() => setData(null));
  }, [plot.id, mode]);

  return (
    <div className="card card-hover">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-stone-900">{t("alerts", lang)}</h2>
        <div className="inline-flex overflow-hidden rounded-md border border-stone-200 text-xs">
          {(["live", "replay"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-2.5 py-1 transition-colors ${
                mode === m ? "bg-brand-700 text-white" : "text-stone-600 hover:bg-stone-50"
              }`}
            >
              {t(m === "live" ? "live" : "replay", lang)}
            </button>
          ))}
        </div>
      </div>

      {data?.replay_note && (
        <p className="mt-2 rounded-md bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800">
          {data.replay_note}
        </p>
      )}

      {!data && <Skeleton rows={3} />}

      {data && data.alerts.length === 0 && (
        <div className="mt-3 rounded-lg bg-brand-50 px-3 py-2.5 text-sm text-brand-800">
          {t("noAlerts", lang)}
        </div>
      )}

      <div className="mt-3 space-y-2.5">
        {data?.alerts.map((a, i) => {
          const Icon = ALERT_ICONS[a.type] ?? TriangleAlert;
          const s = SEVERITY[a.severity as keyof typeof SEVERITY] ?? SEVERITY.moderate;
          const sms = a.sms[lang];
          return (
            <div
              key={i}
              className={`msg-in rounded-lg border border-stone-200 border-l-4 ${s.stripe} bg-white p-3`}
            >
              <div className="flex items-center gap-2.5">
                <span className={`flex h-8 w-8 items-center justify-center rounded-full ${s.chip}`}>
                  <Icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-sm font-semibold text-stone-900">
                      {t(`alert_${a.type}`, lang)}
                    </span>
                    <span className={`text-xs font-medium ${s.label}`}>
                      {t(`sev_${a.severity}`, lang)}
                    </span>
                  </div>
                  <p className="text-xs text-stone-500">{alertDetail(a, lang)}</p>
                </div>
              </div>
              <div className="mt-2.5 flex items-start gap-2 pl-0.5">
                <MessageSquareText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-500" />
                <div className="min-w-0 flex-1">
                  <div className="rounded-2xl rounded-tl-sm bg-stone-100 px-3 py-2 text-sm leading-snug text-stone-800">
                    {sms}
                  </div>
                  <div className="mt-1 flex items-center gap-1.5 pl-1 text-[10px] text-stone-500">
                    <span>{t("smsToFarmer", lang)}</span>
                    <span>·</span>
                    <span>
                      {smsSegments(sms)} {t("segLabel", lang)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {data && (
        <div className="mt-3 grid grid-cols-4 gap-px overflow-hidden rounded-lg border border-stone-200 bg-stone-200 text-center text-xs">
          {[
            [data.water_balance.etc_mm, t("cropNeed", lang)],
            [data.water_balance.rain_eff_mm, t("expectedRain", lang)],
            [data.water_balance.soil_buffer_mm, t("soilBuffer", lang)],
            [data.water_balance.irrigation_mm, t("irrigate", lang)],
          ].map(([val, label], i) => (
            <div key={i} className="bg-white px-1 py-2">
              <div className="font-semibold text-stone-900">{val}</div>
              <div className="text-[10px] text-stone-500">{label} mm</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
