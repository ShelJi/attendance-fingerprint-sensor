import type { Session } from './types';
export type Attendance = {
  employee: { name: string; employee_id: string };
  username: string;
  checked_in: boolean;
  action: string | null;
  notification_id: number | null;
  sessions: Session[];
  verification: { office_configured: boolean };
  evidence: { id: number; session_id: number; action: string; mode: 'office' | 'outdoor'; place_name: string; work_description: string; latitude: number; longitude: number; accuracy_meters: number }[];
};

export function attendanceMessage(action: string | null) {
  switch (action) {
    case 'login': return 'Checked in.';
    case 'logout': return 'Checked out.';
    case 'already_logged_in': return 'Wait five minutes.';
    case 'already_done': return 'Wait five minutes.';
    default: return '';
  }
}
