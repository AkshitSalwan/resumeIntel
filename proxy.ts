import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'
import { getSupabaseConfig } from '@/lib/supabase/config'

export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request })
  try {
    const { url, publishableKey } = getSupabaseConfig()
    const supabase = createServerClient(url, publishableKey, {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          for (const { name, value, options } of cookiesToSet) {
            request.cookies.set(name, value)
            response = NextResponse.next({ request })
            response.cookies.set(name, value, options)
          }
        },
      },
    })
    const { data } = await supabase.auth.getUser()
    if (request.nextUrl.pathname === '/' && !data.user) {
      const url = request.nextUrl.clone()
      url.pathname = '/auth/signin'
      url.searchParams.set('next', '/')
      return NextResponse.redirect(url)
    }
  } catch (error) {
    if (error instanceof Error && error.message !== 'Supabase authentication is not configured.') {
      console.error('Supabase proxy session refresh failed', error)
    }
  }
  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
}
