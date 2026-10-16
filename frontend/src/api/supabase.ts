import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
const anonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

// Video upload is intentionally deferred. Keeping this client ready prevents future
// upload code from depending on backend-only Supabase credentials.
export const supabase: SupabaseClient | undefined =
  url && anonKey ? createClient(url, anonKey) : undefined;

export const storageBucket = process.env.EXPO_PUBLIC_SUPABASE_STORAGE_BUCKET;
