import { redirect } from 'next/navigation'
import { getAuthenticatedUser } from '@/lib/auth'
import { FutureSkillForecast } from '@/components/future-skill-forecast'

export const dynamic = 'force-dynamic'

export default async function ForecastPage() {
  const auth = await getAuthenticatedUser()
  if (!auth.user) redirect('/auth/signin?next=/dashboard/forecast')
  return <FutureSkillForecast />
}
