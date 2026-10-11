'use client'

import { createBrowserClient } from '@supabase/ssr'
import { getSupabaseConfig } from './config'

let client: ReturnType<typeof createBrowserClient> | undefined

export function createSupabaseBrowserClient() {
  if (!client) {
    const { url, publishableKey } = getSupabaseConfig()
    client = createBrowserClient(url, publishableKey)
  }
  return client
}
