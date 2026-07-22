import type { Dynasty } from '@/types';
import { TIME_START, TIME_END } from '@/data/dynasties';

const TOTAL_SPAN = TIME_END - TIME_START;

/** 将年份映射到时间轴像素坐标 */
export function timeToX(year: number, trackWidth: number): number {
  return ((year - TIME_START) / TOTAL_SPAN) * trackWidth;
}

/** 将像素坐标映射到年份 */
export function xToTime(x: number, trackWidth: number): number {
  return (x / trackWidth) * TOTAL_SPAN + TIME_START;
}

/** 获取朝代中点年份 */
export function dynastyMidYear(d: Dynasty): number {
  return (d.startYear + d.endYear) / 2;
}

/** 格式化年份显示 */
export function formatYear(year: number): string {
  if (year < 0) return `前${Math.abs(year)}`;
  return `${year}`;
}

/** 根据朝代 ID 找到朝代 */
export function findDynasty(dynasties: Dynasty[], id: string): Dynasty | undefined {
  return dynasties.find((d) => d.id === id);
}

/** 找到某年份所属的朝代 */
export function findDynastyByYear(dynasties: Dynasty[], year: number): Dynasty | undefined {
  return dynasties.find((d) => year >= d.startYear && year <= d.endYear);
}

/** 获取当前朝代在列表中的索引 */
export function dynastyIndex(dynasties: Dynasty[], id: string): number {
  return dynasties.findIndex((d) => d.id === id);
}

/** 获取朝代持续时间（年） */
export function dynastyDuration(d: Dynasty): number {
  return d.endYear - d.startYear;
}

/** 颜色工具：hex 转 rgba */
export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
