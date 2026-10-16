export type Gym = {
  id: number;
  name: string;
  location: string;
};

export type GymCreateResponse = Gym & {
  created_at: string;
};

export type GymInput = {
  name: string;
  location: string;
};
