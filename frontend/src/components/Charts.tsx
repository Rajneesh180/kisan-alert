import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type ForecastDay, type Indicator, type Lang, type Plot } from "../api";
import { t } from "../i18n";

// Validated series hues (dataviz palette script; CVD-safe for the pairs that
// co-occur in a chart). Text stays in ink tokens, colour rides only the marks.
const VEG = "#2f855a"; // NDVI — vegetation
const WATER = "#2563eb"; // rainfall / soil moisture
const ET0 = "#d97706"; // reference evapotranspiration

const GRID = "#eceae7";
const AXIS = { fontSize: 10, stroke: "#d6d3d1", tick: { fill: "#78716c" } };

const tooltipStyle = {
  contentStyle: {
    borderRadius: 10,
    border: "1px solid #e7e5e4",
    fontSize: 12,
    boxShadow: "0 6px 20px -8px rgba(16,24,20,0.25)",
  },
};

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-stone-500">
      <span className="h-2 w-2 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

export function ForecastChart({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [days, setDays] = useState<ForecastDay[]>([]);

  useEffect(() => {
    api
      .alerts(plot.id, "live")
      .then((r) => setDays(r.days))
      .catch(() => setDays([]));
  }, [plot.id]);

  return (
    <div className="card card-hover">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="card-title text-base">{t("forecast", lang)}</h2>
        <div className="flex gap-3">
          <LegendDot color={WATER} label="rain mm" />
          <LegendDot color={ET0} label="ET₀ mm" />
        </div>
      </div>
      <ResponsiveContainer width="100%" height={190}>
        <ComposedChart data={days.map((d) => ({ ...d, day: d.date.slice(5) }))} margin={{ left: 0, right: 6, top: 4 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="day" {...AXIS} tickLine={false} axisLine={false} minTickGap={20} />
          <YAxis {...AXIS} tickLine={false} axisLine={false} width={34} />
          <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(37,99,235,0.06)" }} />
          <Bar dataKey="rain_mm" name="rain mm" fill={WATER} radius={[3, 3, 0, 0]} maxBarSize={14} />
          <Line dataKey="et0_mm" name="ET0 mm" stroke={ET0} strokeWidth={2} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HistoryChart({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [rows, setRows] = useState<Indicator[]>([]);

  useEffect(() => {
    api.indicators(plot.id).then(setRows).catch(() => setRows([]));
  }, [plot.id]);

  const hasNdvi = rows.some((r) => r.ndvi !== null);
  const data = rows.map((r) => ({ ...r, day: r.date.slice(2, 7) }));
  // Recorded Dec 2025-Apr 2026 dry spell (same window the alert replay uses).
  const droughtFrom = data.find((r) => r.date >= "2025-12-01")?.day;
  const droughtTo = [...data].reverse().find((r) => r.date <= "2026-04-30")?.day;
  const drought =
    droughtFrom && droughtTo ? (
      <ReferenceArea x1={droughtFrom} x2={droughtTo} fill="#f59e0b" fillOpacity={0.1} />
    ) : null;

  return (
    <div className="card card-hover">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="card-title text-base">{t("history", lang)}</h2>
        <div className="flex flex-wrap justify-end gap-x-3 gap-y-0.5">
          {hasNdvi && <LegendDot color={VEG} label="NDVI" />}
          <LegendDot color={WATER} label="soil moisture" />
          <LegendDot color="#fbbf24" label="dry spell" />
        </div>
      </div>

      {/* Vegetation & soil-moisture indices (both 0–1) — one shared axis. */}
      <ResponsiveContainer width="100%" height={130}>
        <ComposedChart data={data} margin={{ left: 0, right: 6, top: 4 }} syncId="history">
          <CartesianGrid stroke={GRID} vertical={false} />
          {drought}
          <XAxis dataKey="day" hide />
          <YAxis
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={(v) => v.toFixed(2)}
            {...AXIS}
            tickLine={false}
            axisLine={false}
            width={38}
          />
          <Tooltip {...tooltipStyle} />
          {hasNdvi && (
            <Line dataKey="ndvi" name="NDVI" stroke={VEG} strokeWidth={2} dot={false} connectNulls />
          )}
          <Line
            dataKey="soil_moisture"
            name="soil moisture"
            stroke={WATER}
            strokeWidth={1.75}
            strokeDasharray="4 2"
            dot={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Rainfall (mm / 10-day) — its own scale, so no dual axis. */}
      <ResponsiveContainer width="100%" height={82}>
        <BarChart data={data} margin={{ left: 0, right: 6, bottom: 2 }} syncId="history">
          <CartesianGrid stroke={GRID} vertical={false} />
          {drought}
          <XAxis dataKey="day" {...AXIS} tickLine={false} axisLine={false} minTickGap={28} />
          <YAxis {...AXIS} tickLine={false} axisLine={false} width={38} />
          <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(37,99,235,0.06)" }} />
          <Bar dataKey="rain_mm" name="rain mm/10d" fill={WATER} radius={[2, 2, 0, 0]} maxBarSize={9} />
        </BarChart>
      </ResponsiveContainer>

      {!hasNdvi && (
        <p className="mt-1 text-xs text-stone-500">
          NDVI joins once the Sentinel-2 pipeline runs (Earth Engine registration).
        </p>
      )}
    </div>
  );
}
