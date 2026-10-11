'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'

export function SignOutButton() {
  const router = useRouter()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  async function signOut() {
    setPending(true)
    setError('')
    try {
      const response = await fetch('/api/auth/signout', { method: 'POST' })
      if (!response.ok) throw new Error('Sign-out failed')
      router.replace('/auth/signin')
      router.refresh()
    } catch {
      setError('Could not sign out. Please try again.')
    } finally {
      setPending(false)
    }
  }

  return <>{error && <span className="auth-message error" role="alert">{error}</span>}<button className="nav-item" type="button" onClick={signOut} disabled={pending}>{pending ? 'Signing out…' : 'Sign out'}</button></>
}
