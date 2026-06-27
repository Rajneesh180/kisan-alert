import { Mic, Send, Square, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, type Lang, type Plot } from "../api";
import { t } from "../i18n";
import { cue, isSpeechSupported, speak, stopSpeaking } from "../speech";

interface Msg {
  id: number;
  role: "farmer" | "assistant";
  text: string;
  degraded?: boolean;
}

export default function AdvisoryChat({ plot, lang }: { plot: Plot; lang: Lang }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [speakingId, setSpeakingId] = useState<number | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(0);

  const canSpeak = isSpeechSupported();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  // Stop any speech when leaving the plot or unmounting.
  useEffect(() => stopSpeaking, [plot.id]);

  function say(text: string, id: number) {
    if (!canSpeak) return;
    setSpeakingId(id);
    speak(text, lang, () => setSpeakingId(null));
  }

  function toggleSpeak(text: string, id: number) {
    if (speakingId === id) {
      stopSpeaking();
      setSpeakingId(null);
    } else {
      say(text, id);
    }
  }

  function push(role: Msg["role"], text: string, degraded = false): number {
    const id = nextId.current++;
    setMessages((m) => [...m, { id, role, text, degraded }]);
    return id;
  }

  // Speak is a side effect, so it is invoked here — never inside a state updater
  // (React StrictMode runs updaters twice, which would double the speech).
  function pushAssistant(text: string, degraded: boolean, autoplay: boolean) {
    const id = push("assistant", text, degraded);
    if (autoplay && autoSpeak) say(text, id);
  }

  async function ask(question: string) {
    if (!question.trim() || busy) return;
    push("farmer", question);
    setInput("");
    setBusy(true);
    try {
      const res = await api.advisory({ plot_id: plot.id, question, lang });
      pushAssistant(res.answer, res.degraded, true);
    } catch {
      pushAssistant(t("requestFailed", lang), true, false);
    } finally {
      setBusy(false);
    }
  }

  async function toggleRecording() {
    if (recording) {
      recorder.current?.stop();
      return;
    }
    stopSpeaking();
    setSpeakingId(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunks.current = [];
      mr.ondataavailable = (e) => chunks.current.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop());
        setRecording(false);
        cue("stop");
        const blob = new Blob(chunks.current, { type: mr.mimeType || "audio/webm" });
        const form = new FormData();
        form.append("plot_id", plot.id);
        form.append("lang", lang);
        form.append("audio", blob, "question.webm");
        setBusy(true);
        try {
          const res = await api.advisoryVoice(form);
          push("farmer", res.transcript ?? t("voiceNote", lang));
          pushAssistant(res.answer, res.degraded, true);
        } catch {
          pushAssistant(t("voiceFailed", lang), true, false);
        } finally {
          setBusy(false);
        }
      };
      mr.start();
      recorder.current = mr;
      setRecording(true);
      cue("start");
    } catch {
      pushAssistant(t("micUnavailable", lang), true, false);
    }
  }

  return (
    <div className="card card-hover">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-stone-900">{t("advisory", lang)}</h2>
        {canSpeak && (
          <button
            onClick={() => {
              if (autoSpeak) stopSpeaking();
              setAutoSpeak((v) => !v);
            }}
            className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs ${
              autoSpeak ? "bg-brand-100 text-brand-800" : "bg-stone-100 text-stone-500"
            }`}
            aria-label={autoSpeak ? t("voiceOn", lang) : t("voiceOff", lang)}
          >
            {autoSpeak ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
            {autoSpeak ? t("voiceOn", lang) : t("voiceOff", lang)}
          </button>
        )}
      </div>

      <div ref={scrollRef} className="mt-2 max-h-64 space-y-2 overflow-y-auto">
        {messages.map((m) =>
          m.role === "farmer" ? (
            <div
              key={m.id}
              className="msg-in ml-auto max-w-[85%] rounded-lg bg-brand-700 p-2 text-sm text-white"
            >
              {m.text}
            </div>
          ) : (
            <div
              key={m.id}
              className="msg-in max-w-[90%] rounded-lg bg-stone-100 p-2 text-sm text-stone-900"
            >
              <div className="flex items-start gap-1.5">
                <span className="flex-1">{m.text}</span>
                {canSpeak && (
                  <button
                    onClick={() => toggleSpeak(m.text, m.id)}
                    className={`mt-0.5 shrink-0 rounded p-0.5 ${
                      speakingId === m.id ? "text-brand-700" : "text-stone-500 hover:text-stone-600"
                    }`}
                    aria-label={t("playAloud", lang)}
                  >
                    <Volume2 className={`h-3.5 w-3.5 ${speakingId === m.id ? "animate-pulse" : ""}`} />
                  </button>
                )}
              </div>
              {m.degraded && (
                <div className="mt-1 text-[10px] text-amber-700">{t("offlineAdvice", lang)}</div>
              )}
            </div>
          ),
        )}
        {busy && <p className="px-1 text-xs text-stone-500">…</p>}
      </div>

      {recording && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          <span className="flex h-4 items-end gap-0.5">
            {[0, 1, 2, 3, 4].map((i) => (
              <span
                key={i}
                className="eq-bar w-1 rounded-full bg-red-500"
                style={{ height: "100%", animationDelay: `${i * 110}ms` }}
              />
            ))}
          </span>
          <span className="font-medium">{t("listening", lang)}</span>
          <span className="ml-auto text-xs text-red-500">{t("tapToStop", lang)}</span>
        </div>
      )}

      <div className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(input)}
          placeholder={t("askPlaceholder", lang)}
          className="flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm"
        />
        <button
          onClick={() => ask(input)}
          className="flex items-center rounded-lg bg-brand-700 px-3 py-2 text-sm text-white transition hover:bg-brand-800 active:scale-95"
          aria-label={t("send", lang)}
        >
          <Send className="h-4 w-4" />
        </button>
        <button
          onClick={toggleRecording}
          className={`flex items-center gap-1 rounded-lg px-3 py-2 text-sm transition active:scale-95 ${
            recording
              ? "bg-red-600 text-white"
              : "bg-brand-100 text-brand-900 hover:bg-brand-200"
          }`}
        >
          {recording ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          {recording ? t("stop", lang) : t("record", lang)}
        </button>
      </div>
      <button onClick={() => ask(t("sampleQ", lang))} className="mt-2 text-xs text-brand-700 underline">
        {t("sample", lang)}
      </button>
    </div>
  );
}
