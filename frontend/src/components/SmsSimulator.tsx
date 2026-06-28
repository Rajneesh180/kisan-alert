import { CheckCheck, Send, Smartphone } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type Lang, type Plot } from "../api";
import { t } from "../i18n";

interface Bubble {
  dir: "out" | "in";
  text: string;
  segments?: number;
  time: string;
}

const KEYWORDS = ["PANI", "FASAL", "HELP"];

function now(): string {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function SmsSimulator({
  plots,
  plot,
  lang,
  onSelectPlot,
}: {
  plots: Plot[];
  plot: Plot;
  lang: Lang;
  onSelectPlot: (id: string) => void;
}) {
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [bubbles, busy]);

  async function send(msg: string) {
    if (!msg.trim() || busy) return;
    setBubbles((b) => [...b, { dir: "out", text: msg, time: now() }]);
    setText("");
    setBusy(true);
    try {
      const res = await api.smsInbound({ plot_id: plot.id, text: msg, lang });
      // brief delay so the "typing" indicator reads like a real gateway round-trip
      await new Promise((r) => setTimeout(r, 650));
      setBubbles((b) => [
        ...b,
        { dir: "in", text: res.reply, segments: res.segments, time: now() },
      ]);
    } catch {
      setBubbles((b) => [...b, { dir: "in", text: "Message failed", time: now() }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <p className="mb-2 text-center text-sm text-stone-500">{t("smsSim", lang)}</p>
      <div className="overflow-hidden rounded-[2rem] border-[6px] border-stone-800 bg-stone-800 shadow-xl">
        {/* phone header bar */}
        <div className="flex items-center justify-between bg-brand-800 px-3 py-2 text-white">
          <span className="flex items-center gap-2 text-sm font-medium">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/20">
              <Smartphone className="h-3.5 w-3.5" />
            </span>
            Kisan Alert · 51969
          </span>
          <select
            value={plot.id}
            onChange={(e) => onSelectPlot(e.target.value)}
            className="rounded border border-white/30 bg-brand-700 px-1 py-0.5 text-xs text-white"
          >
            {plots.map((p) => (
              <option key={p.id} value={p.id}>
                {p.village}
              </option>
            ))}
          </select>
        </div>

        {/* thread */}
        <div
          ref={threadRef}
          className="h-80 space-y-1.5 overflow-y-auto bg-[#e7ded3] p-3"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 30%, rgba(255,255,255,0.35) 0, transparent 40%)",
          }}
        >
          {bubbles.length === 0 && (
            <p className="mt-6 text-center text-xs text-stone-500">
              {plot.farmer} · {plot.village}
            </p>
          )}
          {bubbles.map((b, i) => (
            <div key={i} className={`msg-in ${b.dir === "out" ? "text-right" : "text-left"}`}>
              <div
                className={`inline-block max-w-[85%] rounded-2xl px-3 py-1.5 text-left text-sm shadow-sm ${
                  b.dir === "out"
                    ? "rounded-br-sm bg-[#d9fdd3] text-stone-900"
                    : "rounded-bl-sm bg-white text-stone-900"
                }`}
              >
                {b.text}
                <span className="ml-1 inline-flex items-center gap-0.5 align-bottom text-[9px] text-stone-500">
                  {b.time}
                  {b.dir === "out" && <CheckCheck className="h-3 w-3 text-sky-500" />}
                  {b.dir === "in" && b.segments != null && (
                    <span>
                      · {b.segments} {t("segLabel", lang)}
                    </span>
                  )}
                </span>
              </div>
            </div>
          ))}
          {busy && (
            <div className="text-left">
              <div className="inline-flex items-center gap-1 rounded-2xl rounded-bl-sm bg-white px-3 py-2 shadow-sm">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400"
                    style={{ animationDelay: `${i * 200}ms` }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* composer */}
        <div className="bg-stone-100 p-2">
          <div className="mb-1.5 flex gap-1">
            {KEYWORDS.map((k) => (
              <button
                key={k}
                onClick={() => send(k)}
                disabled={busy}
                className="rounded-full bg-brand-100 px-3 py-1 text-xs font-medium text-brand-900 transition active:scale-95 disabled:opacity-50"
              >
                {k}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send(text)}
              placeholder={t("typeSms", lang)}
              className="flex-1 rounded-full border border-stone-300 bg-white px-3 py-1.5 text-sm"
            />
            <button
              onClick={() => send(text)}
              disabled={busy}
              className="flex items-center rounded-full bg-brand-700 px-4 py-1.5 text-white transition hover:bg-brand-800 active:scale-95 disabled:opacity-50"
              aria-label="Send SMS"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
