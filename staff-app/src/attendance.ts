export type Attendance = {
  employee: { name: string; employee_id: string };
  username: string;
  checked_in: boolean;
  action: string | null;
  notification_id: number | null;
  sessions: { id: number; login_at: string; logout_at: string | null }[];
  verification: { office_configured: boolean };
  evidence: { id: number; session_id: number; action: string; mode: 'office' | 'outdoor'; place_name: string; work_description: string; latitude: number; longitude: number; accuracy_meters: number }[];
};

export function attendanceMessage(action: string | null) {
  switch (action) {
    case 'login': return 'You’re checked in. Have a good day!';
    case 'logout': return 'You’re checked out. See you next time.';
    case 'already_logged_in': return 'Please wait five minutes after checking in before checking out.';
    case 'already_done': return 'Please wait five minutes after checking out before checking in again.';
    default: return '';
  }
}
