import { Suspense } from 'react'
import { AuthForm } from '@/components/auth-form'

export default function SignInPage() {
  return <Suspense fallback={<main className="auth-shell"><section className="auth-card">Loading sign-in…</section></main>}><AuthForm mode="signin" /></Suspense>
}
