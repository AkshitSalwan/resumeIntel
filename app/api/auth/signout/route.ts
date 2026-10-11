import { NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase/server'

export const runtime = 'nodejs'

export async function POST() {
  try {
    const supabase = await createSupabaseServerClient()
    const { error } = await supabase.auth.signOut()
    if (error) {
      console.error('Supabase sign-out failed', error)
      return NextResponse.json({ error: 'Could not sign out.' }, { status: 503 })
    }
    return NextResponse.json({ signedOut: true })
  } catch (error) {
    console.error('Supabase sign-out configuration failed', error)
    return NextResponse.json({ error: 'Authentication is not configured.' }, { status: 503 })
  }
}
