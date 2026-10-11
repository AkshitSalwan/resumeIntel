export const MIN_PASSWORD_LENGTH = 8

export function validateEmail(value: string) {
  const email = value.trim()
  if (!email) return 'Email address is required.'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Enter a valid email address.'
  return null
}

export function validatePassword(value: string) {
  if (!value) return 'Password is required.'
  if (value.length < MIN_PASSWORD_LENGTH) return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`
  return null
}

export function validateCredentials(email: string, password: string) {
  return validateEmail(email) ?? validatePassword(password)
}

export function validatePasswordConfirmation(password: string, confirmation: string) {
  return password === confirmation ? null : 'Passwords do not match.'
}

export function authErrorMessage(error: { status?: number; code?: string } | null, mode: 'signin' | 'signup') {
  if (error?.status === 429 || error?.code === 'over_email_send_rate_limit') {
    return 'Too many authentication attempts were made. Please wait a few minutes before trying again.'
  }
  return mode === 'signup'
    ? 'We could not create your account. Check your details and try again.'
    : 'Sign-in failed. Check your email and password and try again.'
}

export function safeReturnPath(value: string | null | undefined, fallback = '/') {
  if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\') || value.includes('\n') || value.includes('\r')) return fallback
  return value
}
