import { useEffect, useRef, useState } from "react";
import { api, type HealthLogEntry, type Lang, type Plot } from "../api";
import { t } from "../i18n";

export default function HealthPanel({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [logs, setLogs] = useState<HealthLogEntry[]>([]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function refresh() {
    api.healthLogs(plot.id).then(setLogs).catch(() => setLogs([]));
  }

  useEffect(refresh, [plot.id]);

  async function submit(sampleNote?: string) {
    const photo = fileRef.current?.files?.[0];
    const text = (sampleNote ?? note).trim();
    if (!text && !photo) return;
    setBusy(true);
    const form = new FormData();
    form.append("plot_id", plot.id);
    form.append("lang", lang);
    if (text) form.append("note", text);
    if (photo && !sampleNote) form.append("photo", photo);
    try {
      await api.createHealthLog(form);
      setNote("");
      if (fileRef.current) fileRef.current.value = "";
      refresh();
    } finally {
      setBusy(false);
    }
  }

  const SAMPLES = ["sampleLeafSpots", "samplePest", "sampleWilt"];

  return (
    <div className="card card-hover">
      <h2 className="font-semibold text-brand-900">{t("healthLog", lang)}</h2>
      <div className="mt-2 space-y-2">
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={t("describeProblem", lang)}
          rows={2}
          className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
        />
        <div className="flex items-center gap-2">
          <input ref={fileRef} type="file" accept="image/*" className="text-xs" />
          <button onClick={() => submit()} disabled={busy} className="btn-primary ml-auto">
            {t("submitLog", lang)}
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
          <span className="text-[11px] text-stone-500">{t("trySample", lang)}</span>
          {SAMPLES.map((key) => (
            <button
              key={key}
              onClick={() => submit(t(key, lang))}
              disabled={busy}
              className="rounded-full border border-stone-200 bg-stone-50 px-2.5 py-0.5 text-[11px] text-stone-600 hover:bg-stone-100 disabled:opacity-50"
            >
              {t(key, lang)}
            </button>
          ))}
        </div>
      </div>
      {busy && <p className="mt-2 text-xs text-stone-500">{t("diagnosing", lang)}</p>}

      <ul className="mt-3 space-y-2">
        {logs.map((l) => (
          <li key={l.id} className="rounded-lg border border-stone-100 p-2 text-sm">
            <div className="flex items-start gap-2">
              {l.photo_url && (
                <img src={l.photo_url} alt="" className="h-14 w-14 rounded object-cover" />
              )}
              <div className="min-w-0 flex-1">
                {l.transcript && <p className="text-stone-800">{l.transcript}</p>}
                {l.diagnosis ? (
                  <p className="mt-1">
                    <span className="font-medium">{l.diagnosis}</span>
                    {l.confidence != null && (
                      <span className="ml-1 text-xs text-stone-500">
                        ({Math.round(l.confidence * 100)}% {t("confidence", lang)})
                      </span>
                    )}
                    {l.severity && (
                      <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-800">
                        {l.severity}
                      </span>
                    )}
                  </p>
                ) : (
                  <p className="mt-1 text-xs text-stone-500">—</p>
                )}
                {l.treatment && (
                  <p className="mt-1 whitespace-pre-line text-xs text-stone-600">{l.treatment}</p>
                )}
                {l.escalated && (
                  <span className="mt-1 inline-block rounded-full bg-blue-100 px-2 py-0.5 text-[10px] text-blue-800">
                    {t("escalatedBadge", lang)}
                  </span>
                )}
                {l.expert_reply && (
                  <div className="mt-1 rounded bg-brand-50 p-2 text-xs text-brand-900">
                    <span className="font-medium">{t("expertReply", lang)}:</span> {l.expert_reply}
                  </div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
