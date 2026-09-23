"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/apiClient";

export default function LoginForm() {
  const router = useRouter();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.login(loginId.trim(), password);
      router.replace("/pos");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "ログインできませんでした");
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="login-form" onSubmit={onSubmit} noValidate>
      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}
      <div className="row">
        <label className="label" htmlFor="login-id">
          担当ID
        </label>
        <input
          id="login-id"
          className="field"
          autoComplete="username"
          value={loginId}
          maxLength={20}
          onChange={(e) => setLoginId(e.target.value)}
          required
          autoFocus
        />
      </div>
      <div className="row">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <label className="label" htmlFor="login-pw">
            パスワード
          </label>
          <button type="button" className="btn-link" style={{ height: 28 }} onClick={() => setShowPw((v) => !v)} aria-pressed={showPw}>
            {showPw ? "隠す" : "表示"}
          </button>
        </div>
        <input
          id="login-pw"
          className="field"
          type={showPw ? "text" : "password"}
          autoComplete="current-password"
          value={password}
          maxLength={128}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <span className="hint">15文字以上</span>
      </div>
      <button type="submit" className="btn btn-dark" disabled={busy || !loginId || !password}>
        {busy ? "確認中…" : "ログイン"}
      </button>
    </form>
  );
}
