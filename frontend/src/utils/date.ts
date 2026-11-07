export type CalendarDay = { date: Date; dateString: string; isCurrentMonth: boolean };

const KST_TIME_ZONE = 'Asia/Seoul';

function getKstParts(value: Date | string): Record<string, string> {
  const date = typeof value === 'string' ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) throw new Error('올바른 날짜/시간 형식이 아닙니다.');
  return Object.fromEntries(
    new Intl.DateTimeFormat('en-CA', {
      timeZone: KST_TIME_ZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(date).filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]),
  );
}

export function formatKstDate(value: Date | string): string {
  const parts = getKstParts(value);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function formatKstDateTime(value: string | null): string {
  if (!value) return '-';
  const parts = getKstParts(value);
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`;
}

export function formatKstDateTimeSeconds(value: string | null): string {
  if (!value) return '-';
  const parts = getKstParts(value);
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
}

export function formatKstDateTimeInput(value: string | null): string {
  if (!value) return '';
  const parts = getKstParts(value);
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

export function formatKstTime(value: Date | string): string {
  const parts = getKstParts(value);
  return `${parts.hour}:${parts.minute}`;
}

export function formatKstTimeSeconds(value: Date | string): string {
  const parts = getKstParts(value);
  return `${parts.hour}:${parts.minute}:${parts.second}`;
}

/** Creates a Date representing a KST wall-clock time for the native time picker. */
export function createKstPickerDate(sessionDate: string, time: string): Date {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})$/.exec(`${sessionDate}T${time}`);
  if (!match) throw new Error('올바른 날짜 또는 시간 형식이 아닙니다.');
  const date = new Date(`${match[1]}T${match[2]}:00+09:00`);
  if (Number.isNaN(date.getTime())) throw new Error('올바른 날짜 또는 시간 형식이 아닙니다.');
  return date;
}

export function combineKstDateAndTime(sessionDate: string, time: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate) || !/^\d{2}:\d{2}$/.test(time)) {
    throw new Error('올바른 날짜 또는 시간 형식이 아닙니다.');
  }
  return `${sessionDate}T${time}`;
}

export function parseKstInputToApi(value: string): string {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::(\d{2}))?$/.exec(value.trim());
  if (!match) throw new Error('시간은 YYYY-MM-DDTHH:mm 형식으로 입력해 주세요.');
  const apiValue = `${match[1]}T${match[2]}:${match[3] ?? '00'}+09:00`;
  if (Number.isNaN(new Date(apiValue).getTime())) throw new Error('올바른 날짜/시간을 입력해 주세요.');
  return apiValue;
}

export function formatLocalDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function parseLocalDate(value: string): Date {
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, month - 1, day);
}

export function createMonthGrid(year: number, monthIndex: number): CalendarDay[] {
  const firstDay = new Date(year, monthIndex, 1);
  const gridStart = new Date(year, monthIndex, 1 - firstDay.getDay());
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + index);
    return { date, dateString: formatLocalDate(date), isCurrentMonth: date.getMonth() === monthIndex };
  });
}

export function formatKoreanDate(value: string): string {
  const date = parseLocalDate(value);
  return `${date.getFullYear()}년 ${date.getMonth() + 1}월 ${date.getDate()}일`;
}
