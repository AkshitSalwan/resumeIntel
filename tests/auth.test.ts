import { describe, expect, it } from 'vitest'
import { authErrorMessage, safeReturnPath, validateCredentials, validateEmail, validatePassword, validatePasswordConfirmation } from '../lib/auth-validation'

describe('authentication validation', () => {
  it('validates email and password inputs', () => {
    expect(validateEmail('')).toBe('Email address is required.')
    expect(validateEmail('not-an-email')).toBe('Enter a valid email address.')
    expect(validateEmail('person@example.com')).toBeNull()
    expect(validatePassword('short')).toContain('at least')
    expect(validatePassword('long-enough-password')).toBeNull()
    expect(validateCredentials('person@example.com', 'short')).toContain('at least')
  })

  it('requires matching sign-up passwords', () => {
    expect(validatePasswordConfirmation('password-one', 'password-two')).toBe('Passwords do not match.')
    expect(validatePasswordConfirmation('password-one', 'password-one')).toBeNull()
  })

  it('explains authentication rate limits without exposing provider details', () => {
    expect(authErrorMessage({ status: 429 }, 'signup')).toContain('Too many authentication attempts')
    expect(authErrorMessage({ code: 'over_email_send_rate_limit' }, 'signup')).toContain('wait a few minutes')
    expect(authErrorMessage({ status: 400 }, 'signup')).toBe('We could not create your account. Check your details and try again.')
    expect(authErrorMessage({ status: 429 }, 'signin')).toContain('Too many authentication attempts')
  })

  it('allows only safe local return paths', () => {
    expect(safeReturnPath('/')).toBe('/')
    expect(safeReturnPath('/reports/123')).toBe('/reports/123')
    expect(safeReturnPath('https://evil.example')).toBe('/')
    expect(safeReturnPath('//evil.example')).toBe('/')
    expect(safeReturnPath('/\\evil.example')).toBe('/')
    expect(safeReturnPath(null, '/auth/signin')).toBe('/auth/signin')
  })
})
