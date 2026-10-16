export type SessionVideo = {
  id: number;
  session_id: number;
  storage_path: string;
  file_url: string;
  uploaded_at: string;
};

export type VideoCreateInput = {
  storage_path: string;
};
