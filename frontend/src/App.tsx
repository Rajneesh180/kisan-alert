import { Leaf, Radio, Satellite } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Lang, type Plot, type Region } from "./api";
import AdvisoryChat from "./components/AdvisoryChat";
import AlertsCard from "./components/AlertsCard";
import { ForecastChart, HistoryChart } from "./components/Charts";
import FertilizerCard from "./components/FertilizerCard";
import HealthPanel from "./components/HealthPanel";
import NdviForecastCard from "./components/NdviForecastCard";
import PlotMap from "./components/PlotMap";
import PlotVerdict from "./components/PlotVerdict";
import RecommendPanel from "./components/RecommendPanel";
import RskView from "./components/RskView";
import SensorCard from "./components/SensorCard";
import SmsSimulator from "./components/SmsSimulator";
import { t } from "./i18n";

type Tab = "farmer" | "expert" | "sms";

const LANGS: { id: Lang; label: string }[] = [
  { id: "te", label: "తెలుగు" },
  { id: "hi", label: "हिंदी" },
  { id: "en", label: "English" },
];

function initialLang(): Lang {
  const saved = typeof localStorage !== "undefined" ? localStorage.getItem("kisan-lang") : null;
  return saved === "en" || saved === "te" || saved === "hi" ? saved : "en";
}

export default function App() {
  const [lang, setLang] = useState<Lang>(initialLang);
  const [tab, setTab] = useState<Tab>("farmer");
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionId, setRegionId] = useState<string>("");
  const [plots, setPlots] = useState<Plot[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem("kisan-lang", lang);
  }, [lang]);

  useEffect(() => {
    api.regions().then((rs) => {
      setRegions(rs);
      if (rs.length) setRegionId(rs[0].id);
    });
  }, []);

  useEffect(() => {
    if (!regionId) return;
    api.plots(regionId).then((ps) => {
      setPlots(ps);
      setSelectedId(ps[0]?.id ?? null);
    });
  }, [regionId]);

  const region = regions.find((r) => r.id === regionId) ?? null;
  // Guard the brief window after a region switch where `region` has updated but
  // `plots` is still the previous region's set (async refetch).
  const plot = plots.find((p) => p.id === selectedId && p.region === regionId) ?? null;

  return (
    <div className="min-h-screen text-stone-800">
      <header className="bg-gradient-to-r from-brand-900 via-brand-800 to-brand-700 text-white shadow-lg">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3.5">
          <span className="text-3xl leading-none drop-shadow-sm sm:text-4xl">🌾</span>
          <div className="min-w-0">
            <h1 className="font-display text-xl font-bold leading-tight tracking-tight">
              Kisan Alert
            </h1>
            <p className="truncate text-xs text-brand-100/85">{t("tagline", lang)}</p>
          </div>
          <div className="ml-auto flex overflow-hidden rounded-lg border border-white/25 text-xs shadow-sm">
            {LANGS.map((l) => (
              <button
                key={l.id}
                onClick={() => setLang(l.id)}
                className={`px-2 py-1.5 transition-colors sm:px-2.5 ${
                  lang === l.id ? "bg-white font-medium text-brand-900" : "text-brand-50 hover:bg-white/10"
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <nav className="sticky top-0 z-20 border-b border-stone-200 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center gap-1 overflow-x-auto px-4">
          {(
            [
              ["farmer", "tabFarmer"],
              ["expert", "tabExpert"],
              ["sms", "tabSms"],
            ] as [Tab, string][]
          ).map(([id, key]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`-mb-px shrink-0 whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                tab === id
                  ? "border-brand-700 text-brand-900"
                  : "border-transparent text-stone-500 hover:text-stone-800"
              }`}
            >
              {t(key, lang)}
            </button>
          ))}
          {region && (
            <div className="ml-auto flex shrink-0 items-center gap-2 py-1.5 text-sm">
              <select
                value={regionId}
                onChange={(e) => setRegionId(e.target.value)}
                className="rounded-md border border-stone-300 bg-white px-2 py-1 text-sm"
                aria-label={t("region", lang)}
              >
                {regions.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} · {r.district}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </nav>

      {region?.mp && (
        <div className="border-b border-amber-100 bg-amber-50/70">
          <div className="mx-auto max-w-6xl px-4 py-1.5 text-xs text-amber-900">
            {region.name} constituency · MP {region.mp}
          </div>
        </div>
      )}

      <main className="mx-auto max-w-6xl p-4">
        {tab === "farmer" && plot && region && (
          <>
          <PlotVerdict plot={plot} lang={lang} />
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-4">
              <section className="card card-hover">
                <div className="mb-3 flex items-baseline justify-between">
                  <h2 className="font-semibold text-stone-900">{t("selectPlot", lang)}</h2>
                  <span className="text-xs text-stone-500">
                    {plot.farmer} · {plot.village} · {plot.area_ha} ha
                  </span>
                </div>
                <PlotMap
                  plots={plots}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                  center={region.center}
                  zoom={region.zoom}
                />
                <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-lg bg-stone-50 p-2">
                    <div className="font-semibold capitalize text-stone-900">
                      {plot.crop_current}
                    </div>
                    <div className="text-stone-500">{t("currentCrop", lang)}</div>
                  </div>
                  <div className="rounded-lg bg-stone-50 p-2">
                    <div className="font-semibold text-stone-900">
                      pH {plot.soil?.ph ?? "—"} · {plot.soil?.texture ?? "—"}
                    </div>
                    <div className="text-stone-500">{t("soil", lang)} · SoilGrids</div>
                  </div>
                  <div className="rounded-lg bg-stone-50 p-2">
                    <div className="font-semibold capitalize text-stone-900">
                      {plot.groundwater?.category ?? "—"}
                    </div>
                    <div className="text-stone-500">{t("groundwater", lang)} · CGWB</div>
                    <div
                      title={t("representativeNote", lang)}
                      className="mt-0.5 inline-block cursor-help rounded bg-amber-50 px-1 text-[9px] font-medium text-amber-800"
                    >
                      {t("representative", lang)}
                    </div>
                  </div>
                </div>
                <p className="mt-2 text-[10px] leading-relaxed text-stone-500">{t("demoData", lang)}</p>
              </section>
              <RecommendPanel plot={plot} lang={lang} />
              <FertilizerCard plot={plot} lang={lang} />
              <HealthPanel plot={plot} lang={lang} />
            </div>
            <div className="space-y-4">
              <AlertsCard plot={plot} lang={lang} />
              <ForecastChart plot={plot} lang={lang} />
              <HistoryChart plot={plot} lang={lang} />
              <NdviForecastCard plot={plot} lang={lang} />
              <SensorCard plot={plot} lang={lang} />
              <AdvisoryChat plot={plot} lang={lang} />
            </div>
          </div>
          </>
        )}

        {tab === "expert" && <RskView lang={lang} />}

        {tab === "sms" && plot && (
          <SmsSimulator plots={plots} plot={plot} lang={lang} onSelectPlot={setSelectedId} />
        )}
      </main>

      <footer className="mt-6 border-t border-stone-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-4 text-xs text-stone-500 sm:flex-row sm:items-center sm:justify-between">
          <span className="flex items-center gap-1.5">
            <Leaf className="h-3.5 w-3.5 text-brand-700" />
            Kisan Alert — open agricultural advisory for Indian smallholders
          </span>
          <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <span className="inline-flex items-center gap-1">
              <Satellite className="h-3.5 w-3.5" /> Sentinel-2
            </span>
            <span className="text-stone-300">·</span>
            <span>ERA5 / Open-Meteo</span>
            <span className="text-stone-300">·</span>
            <span>SoilGrids</span>
            <span className="text-stone-300">·</span>
            <span className="inline-flex items-center gap-1">
              <Radio className="h-3.5 w-3.5" /> CGWB
            </span>
            <span className="text-stone-300">·</span>
            <span>Gemini</span>
          </span>
        </div>
      </footer>
    </div>
  );
}
