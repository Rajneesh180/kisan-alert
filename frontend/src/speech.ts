// Read advisory answers aloud (critical for low-literacy farmers) and give
// audible cues while recording so the mic feels alive.
//
// Speech uses Google Cloud TTS first — it has production-quality Telugu and
// Hindi voices that browser speechSynthesis lacks on most devices — and falls
// back to the browser's own synth when Cloud TTS is unconfigured or fails.
import { api, type Lang } from "./api";

const BCP47: Record<Lang, string> = { en: "en-IN", te: "te-IN", hi: "hi-IN" };

let currentAudio: HTMLAudioElement | null = null;
let currentUrl: string | null = null;

function clearAudio(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.onended = null;
    currentAudio = null;
  }
  if (currentUrl) {
    URL.revokeObjectURL(currentUrl);
    currentUrl = null;
  }
}

function pickVoice(lang: Lang): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis?.getVoices() ?? [];
  const want = BCP47[lang];
  return (
    voices.find((v) => v.lang === want) ||
    voices.find((v) => v.lang.startsWith(lang)) ||
    voices.find((v) => v.lang.startsWith("en"))
  );
}

// Returns true if browser synthesis started, so callers know whether onEnd
// will fire from here.
function speakBrowser(text: string, lang: Lang, onEnd?: () => void): boolean {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return false;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = BCP47[lang];
  const v = pickVoice(lang);
  if (v) u.voice = v;
  u.rate = 0.95;
  u.onend = () => onEnd?.();
  window.speechSynthesis.speak(u);
  return true;
}

// Voice is always offered in the browser: Cloud TTS is the primary channel and
// browser synth is the fallback, so the feature never depends on one alone.
export function isSpeechSupported(): boolean {
  return typeof window !== "undefined";
}

export async function speak(text: string, lang: Lang, onEnd?: () => void): Promise<void> {
  if (!text) {
    onEnd?.();
    return;
  }
  stopSpeaking();
  try {
    const blob = await api.tts(text, lang);
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    currentAudio = audio;
    currentUrl = url;
    audio.onended = () => {
      clearAudio();
      onEnd?.();
    };
    await audio.play(); // rejects on autoplay block or decode error → fall back
  } catch {
    clearAudio();
    if (!speakBrowser(text, lang, onEnd)) onEnd?.();
  }
}

export function stopSpeaking(): void {
  clearAudio();
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

// Short sine-wave cue via Web Audio — a rising tone to start, falling to stop.
export function cue(kind: "start" | "stop"): void {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    const now = ctx.currentTime;
    osc.frequency.setValueAtTime(kind === "start" ? 660 : 520, now);
    osc.frequency.exponentialRampToValueAtTime(kind === "start" ? 990 : 350, now + 0.15);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.18, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
    osc.start(now);
    osc.stop(now + 0.2);
    osc.onended = () => ctx.close();
  } catch {
    /* audio cues are best-effort */
  }
}
