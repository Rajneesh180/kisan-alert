import { CheckCircle2, Droplets, Satellite, Sun, TriangleAlert } from "lucide-react";
import type { ComponentType } from "react";
import { useEffect, useState } from "react";
import { api, type Alert, type AlertsResponse, type Lang, type Plot } from "../api";
import { t } from "../i18n";

type Tone = "ok" | "watch" | "urgent";

const SEV_RANK: Record<string, number> = { severe: 3, urgent: 3, moderate: 2, light: 1 };
// Tie-break toward the concrete action ("irrigate") over the condition ("dry spell").
const ACTION_RANK: Record<string, number> = { irrigation: 3, crop_stress: 2, dry_spell: 1 };

const ICON: Record<string, ComponentType<{ className?: string }>> = {
  dry_spell: Sun,
  irrigation: Droplets,
  crop_stress: Satellite,
};

const TONE: Record<Tone, string> = {
  ok: "border-brand-200 bg-brand-50 text-brand-900",
  watch: "border-yellow-300 bg-yellow-50 text-yellow-900",
  urgent: "border-amber-300 bg-amber-50 text-amber-900",
};
const ICON_TONE: Record<Tone, string> = {
  ok: "text-brand-700",
  watch: "text-yellow-700",
  urgent: "text-amber-700",
};

function verdict(data: AlertsResponse, lang: Lang) {
  if (!data.alerts.length) {
    return { Icon: CheckCircle2, tone: "ok" as Tone, title: t("noAlerts", lang), detail: "" };
  }
  const top = [...data.alerts].sort((a, b) => {
    const bySeverity = (SEV_RANK[b.severity] ?? 0) - (SEV_RANK[a.severity] ?? 0);
    return bySeverity !== 0
      ? bySeverity
      : (ACTION_RANK[b.type] ?? 0) - (ACTION_RANK[a.type] ?? 0);
  })[0];
  const Icon = ICON[top.type] ?? TriangleAlert;
  const detail = alertDetail(top, lang);
  const tone: Tone = (SEV_RANK[top.severity] ?? 0) >= 3 ? "urgent" : "watch";
  return { Icon, tone, title: t(`alert_${top.type}`, lang), detail };
}

function alertDetail(a: Alert, lang: Lang): string {
  if (a.type === "irrigation")
    return `~${Math.round(a.irrigation_mm as number)} ${t("detail_irrigation", lang)}`;
  if (a.type === "dry_spell")
    return `${a.length_days as number} ${t("detail_dry_spell", lang)}`;
  if (a.type === "crop_stress") return t("detail_crop_stress", lang);
  return "";
}

export default function PlotVerdict({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [data, setData] = useState<AlertsResponse | null>(null);

  useEffect(() => {
    setData(null);
    api.alerts(plot.id, "live").then(setData).catch(() => setData(null));
  }, [plot.id]);

  if (!data) return <div className="mb-4 h-[74px] animate-pulse rounded-xl bg-stone-100" />;

  const { Icon, tone, title, detail } = verdict(data, lang);
  return (
    <section className={`mb-4 flex items-center gap-3 rounded-xl border p-3.5 ${TONE[tone]}`}>
      <span
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/70 ${ICON_TONE[tone]}`}
      >
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0">
        <div className="text-[11px] font-medium uppercase tracking-wide opacity-70">
          {t("todayLabel", lang)} · {plot.village}
        </div>
        <div className="font-semibold leading-tight">{title}</div>
        {detail && <div className="text-xs opacity-80">{detail}</div>}
      </div>
    </section>
  );
}
