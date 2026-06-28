import { useEffect, useState } from "react";
import { api, type HealthLogEntry, type Lang } from "../api";
import { t } from "../i18n";

export default function RskView({ lang }: { lang: Lang }) {
  const [cases, setCases] = useState<HealthLogEntry[]>([]);
  const [drafts, setDrafts] = useState<Record<number, string>>({});

  function refresh() {
    api.rskCases().then(setCases).catch(() => setCases([]));
  }

  useEffect(refresh, []);

  async function reply(id: number) {
    const text = drafts[id]?.trim();
    if (!text) return;
    await api.rskReply(id, text);
    setDrafts((d) => ({ ...d, [id]: "" }));
    refresh();
  }

  return (
    <div className="card card-hover">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-brand-900">{t("rskQueue", lang)}</h2>
        <button onClick={refresh} className="text-xs text-brand-700 underline">
          {t("refresh", lang)}
        </button>
      </div>

      {cases.length === 0 && <p className="mt-3 text-sm text-stone-500">{t("noCases", lang)}</p>}

      <ul className="mt-3 space-y-3">
        {cases.map((c) => (
          <li
            key={c.id}
            className="rounded-lg border border-stone-200 p-3 text-sm transition-shadow hover:shadow-card"
          >
            <div className="flex items-center gap-2 text-xs text-stone-600">
              <span className="font-medium text-stone-900">
                {c.plot?.farmer} — {c.plot?.village}
              </span>
              <span>({c.plot?.crop})</span>
              <span className="ml-auto">{c.created_at.slice(0, 16).replace("T", " ")}</span>
            </div>
            <div className="mt-2 flex items-start gap-2">
              {c.photo_url && (
                <img src={c.photo_url} alt="" className="h-20 w-20 rounded object-cover" />
              )}
              <div className="min-w-0 flex-1">
                {c.transcript && <p>{c.transcript}</p>}
                {c.diagnosis && (
                  <p className="mt-1 text-xs text-stone-600">
                    AI: {c.diagnosis}
                    {c.confidence != null && ` (${Math.round(c.confidence * 100)}%)`}
                    {c.severity && ` · ${c.severity}`}
                  </p>
                )}
              </div>
            </div>
            {c.expert_reply ? (
              <div className="mt-2 rounded bg-brand-50 p-2 text-xs text-brand-900">
                <span className="font-medium">{t("expertReply", lang)}:</span> {c.expert_reply}
              </div>
            ) : (
              <div className="mt-2 flex gap-2">
                <input
                  value={drafts[c.id] ?? ""}
                  onChange={(e) => setDrafts((d) => ({ ...d, [c.id]: e.target.value }))}
                  placeholder={t("replyPlaceholder", lang)}
                  className="flex-1 rounded-lg border border-stone-300 px-3 py-1.5 text-sm"
                />
                <button onClick={() => reply(c.id)} className="btn-primary">
                  {t("sendReply", lang)}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
