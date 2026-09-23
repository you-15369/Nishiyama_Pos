import LoginForm from "@/components/LoginForm";

export const metadata = { title: "ログイン | 簡易POS" };

export default function LoginPage() {
  return (
    <main className="login">
      <section className="login-visual" aria-hidden="true">
        <div className="brand">POS</div>
        <div className="big">Register</div>
        <div className="caption">レジ担当者専用</div>
      </section>
      <section className="login-panel">
        <h1>ログイン</h1>
        <LoginForm />
      </section>
    </main>
  );
}
