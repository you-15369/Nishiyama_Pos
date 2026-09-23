"use client";

/**
 * Scanner：カメラでバーコードを読み取る。読み取り方式は startScan で差し替えられる（NFR-007 読取入力の抽象化）。
 * 手入力（ManualCodeInput）と同じ onScan 経路に流す。
 */
import { useCallback, useEffect, useRef, useState } from "react";

export type ScanControls = { stop: () => void };
export type StartScan = (video: HTMLVideoElement, onText: (text: string) => void) => Promise<ScanControls>;

/** 既定の読み取り：ZXing（JAN/EAN-13・EAN-8・CODE128） */
export const zxingStartScan: StartScan = async (video, onText) => {
  const [{ BrowserMultiFormatReader }, { BarcodeFormat, DecodeHintType }] = await Promise.all([
    import("@zxing/browser"),
    import("@zxing/library"),
  ]);
  const hints = new Map();
  hints.set(DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.EAN_13, BarcodeFormat.EAN_8, BarcodeFormat.CODE_128]);
  const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: 150 });
  const controls = await reader.decodeFromConstraints(
    { video: { facingMode: { ideal: "environment" } }, audio: false },
    video,
    (result) => {
      if (result) onText(result.getText());
    },
  );
  return { stop: () => controls.stop() };
};

const COOLDOWN_MS = 1500; // 同じバーコードを連続で拾いすぎないための間隔

interface Props {
  onScan: (code: string) => void;
  startScan?: StartScan;
}

type CamState = "off" | "starting" | "on" | "error";

export default function Scanner({ onScan, startScan = zxingStartScan }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const controlsRef = useRef<ScanControls | null>(null);
  const lastRef = useRef<{ code: string; at: number }>({ code: "", at: 0 });
  const onScanRef = useRef(onScan);
  const [state, setState] = useState<CamState>("off");

  useEffect(() => {
    onScanRef.current = onScan;
  }, [onScan]);

  const handleText = useCallback((raw: string) => {
    const code = raw.trim();
    if (!code) return;
    const now = Date.now();
    if (lastRef.current.code === code && now - lastRef.current.at < COOLDOWN_MS) return;
    lastRef.current = { code, at: now };
    onScanRef.current(code);
  }, []);

  const stop = useCallback(() => {
    controlsRef.current?.stop();
    controlsRef.current = null;
    setState("off");
  }, []);

  const start = useCallback(async () => {
    if (!videoRef.current) return;
    setState("starting");
    try {
      controlsRef.current = await startScan(videoRef.current, handleText);
      setState("on");
    } catch {
      controlsRef.current = null;
      setState("error");
    }
  }, [startScan, handleText]);

  useEffect(() => () => controlsRef.current?.stop(), []);

  const label = { off: "カメラ停止中", starting: "カメラを起動しています…", on: "カメラ起動中", error: "カメラを使えません。商品コードを入力してください" }[state];

  return (
    <div className="pos-block">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="label">スキャン</span>
        {state === "on" && (
          <button type="button" className="btn-link" style={{ height: 32 }} onClick={stop}>
            停止
          </button>
        )}
      </div>
      <div className="camera">
        <video ref={videoRef} muted playsInline aria-label="バーコード読み取り用カメラ映像" hidden={state !== "on"} />
        {state === "on" ? (
          <div className="frame" aria-hidden="true" />
        ) : (
          <button type="button" className="btn start" onClick={start} disabled={state === "starting"}>
            {state === "error" ? "もう一度試す" : "カメラを起動"}
          </button>
        )}
        <span className="state" role="status">
          {label}
        </span>
      </div>
    </div>
  );
}
