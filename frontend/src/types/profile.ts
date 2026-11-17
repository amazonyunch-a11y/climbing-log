export type Profile = {
  user_id: number;
  nickname: string | null;
  birth_date: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  arm_length_cm: number | null;
};

export type ProfileUpdate = Partial<Pick<Profile, 'nickname' | 'birth_date' | 'height_cm' | 'weight_kg' | 'arm_length_cm'>>;
