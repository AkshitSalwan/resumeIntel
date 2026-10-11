import type { User } from '@supabase/supabase-js'
import { createSupabaseServerClient } from '@/lib/supabase/server'

export type AuthResult =
  | { user: User; error?: undefined }
  | { user: null; error: 'not_configured' | 'unauthenticated' }

export async function getAuthenticatedUser(): Promise<AuthResult> {
  try {
    const supabase = await createSupabaseServerClient()
    const { data, error } = await supabase.auth.getUser()
    if (error || !data.user) return { user: null, error: 'unauthenticated' }
    return { user: data.user }
  } catch (error) {
    if (error instanceof Error && error.message === 'Supabase authentication is not configured.') {
      return { user: null, error: 'not_configured' }
    }
    console.error('Supabase session verification failed', error)
    return { user: null, error: 'unauthenticated' }
  }
}
