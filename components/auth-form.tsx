'use client'

import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { FormEvent, useState } from 'react'
import { createSupabaseBrowserClient } from '@/lib/supabase/browser'
import { authErrorMessage, safeReturnPath, validateCredentials, validatePasswordConfirmation } from '@/lib/auth-validation'

type AuthMode = 'signin' | 'signup'

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [pending, setPending] = useState(false)
  const isSignUp = mode === 'signup'
  const returnPath = safeReturnPath(searchParams.get('next'))

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')
    const validationError = validateCredentials(email, password) ?? (isSignUp ? validatePasswordConfirmation(password, confirmation) : null)
    if (validationError) {
      setError(validationError)
      return
    }
    setPending(true)
    try {
      const supabase = createSupabaseBrowserClient()
      const result = isSignUp
        ? await supabase.auth.signUp({ email: email.trim(), password, options: { emailRedirectTo: `${window.location.origin}/auth/signin` } })
        : await supabase.auth.signInWithPassword({ email: email.trim(), password })
      if (result.error) {
        setError(authErrorMessage(result.error, mode))
        return
      }
      if (isSignUp && !result.data.session) {
        setNotice('Account created. Check your email to confirm your address before signing in.')
        return
      }
      router.replace(returnPath)
      router.refresh()
    } catch {
      setError('Authentication is temporarily unavailable. Please try again.')
    } finally {
      setPending(false)
    }
  }

  return <main className="auth-shell"><section className="auth-card" aria-labelledby="auth-title"><div className="brand auth-brand"><div className="brand-mark" aria-hidden="true">✦</div><span>resume<span className="brand-accent">intel</span></span></div><p className="eyebrow">{isSignUp ? 'CREATE YOUR WORKSPACE' : 'WELCOME BACK'}</p><h1 id="auth-title">{isSignUp ? 'Build your evidence-grounded workspace.' : 'Sign in to your workspace.'}</h1><p className="auth-subtitle">{isSignUp ? 'Save private resume analyses and return to them anytime.' : 'Review your saved resume-to-role comparisons securely.'}</p><form onSubmit={submit} noValidate><label className="field-label" htmlFor="email">Email address<input id="email" name="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><label className="field-label" htmlFor="password">Password<input id="password" name="password" type="password" autoComplete={isSignUp ? 'new-password' : 'current-password'} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>{isSignUp && <label className="field-label" htmlFor="confirm-password">Confirm password<input id="confirm-password" name="confirm-password" type="password" autoComplete="new-password" required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>}{error && <p className="auth-message error" role="alert">{error}</p>}{notice && <p className="auth-message notice" role="status">{notice}</p>}<button className="primary-button full" type="submit" disabled={pending}>{pending ? 'Please wait…' : isSignUp ? 'Create account' : 'Sign in'}</button></form><p className="auth-switch">{isSignUp ? 'Already have an account?' : 'New to resumeintel?'} <Link href={isSignUp ? `/auth/signin${returnPath !== '/' ? `?next=${encodeURIComponent(returnPath)}` : ''}` : `/auth/signup${returnPath !== '/' ? `?next=${encodeURIComponent(returnPath)}` : ''}`}>{isSignUp ? 'Sign in' : 'Create an account'}</Link></p></section></main>
}
