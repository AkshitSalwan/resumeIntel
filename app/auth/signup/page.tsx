import { Suspense } from 'react'
import { AuthForm } from '@/components/auth-form'

export default function SignUpPage() {
  return <Suspense fallback={<main className="auth-shell"><section className="auth-card">Loading sign-up…</section></main>}><AuthForm mode="signup" /></Suspense>
}
