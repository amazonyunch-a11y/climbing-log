export type GradeLog = {
  id: number;
  session_id: number;
  grade_label: string | null;
  attempts: number | null;
  sends: number | null;
};

export type GradeLogInput = {
  grade_label: string;
  attempts: number;
  sends: number;
};
