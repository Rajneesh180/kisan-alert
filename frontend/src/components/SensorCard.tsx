import { Radio } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Lang, type Plot } from "../api";
import { t } from "../i18n";

interface Reading {
  ts: string;
  metric: string;
  value: number;
}

export default function SensorCard({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [readings, setReadings] = useState<Reading[]>([]);
  const [busy, setBusy] = useState(false);

  function refresh() {
    api.sensors(plot.id).then(setReadings).catch(() => setReadings([]));
  }

  useEffect(refresh, [plot.id]);

  async function sendReading() {
    setBusy(true);
    // Simulated probe: soil moisture jittered around a plausible field value.
    const value = Math.round((0.15 + Math.random() * 0.2) * 1000) / 1000;
    try {
      await api.addSensorReading({ plot_id: plot.id, metric: "soil_moisture", value });
      refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card card-hover">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-1.5 font-semibold text-stone-900">
          <Radio className="h-4 w-4 text-brand-700" />
          {t("iotProbe", lang)}
        </h2>
        <button
          onClick={sendReading}
          disabled={busy}
          className="rounded-lg bg-brand-700 px-3 py-1.5 text-xs text-white disabled:opacity-50"
        >
          {t("sendReading", lang)}
        </button>
      </div>
      <p className="mt-1 text-[11px] text-stone-500">{t("iotNote", lang)}</p>
      {readings.length === 0 ? (
        <p className="mt-2 text-sm text-stone-500">{t("noReadings", lang)}</p>
      ) : (
        <ul className="mt-2 space-y-1 text-xs">
          {readings.slice(0, 5).map((r, i) => (
            <li key={i} className="flex justify-between rounded bg-brand-50 px-2 py-1">
              <span className="text-stone-600">
                {t("soilMoisture", lang)} · {r.ts.slice(0, 16).replace("T", " ")}
              </span>
              <span className="font-mono font-semibold">{r.value} m³/m³</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
