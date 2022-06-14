import { substr, caps, num, range, random } from '~/utils';

test('substr truncates text with ellipsis', () => {
  expect(substr('nicholas', 0)).toBe('…');
  expect(substr('nicholas', 3)).toBe('nic…');
  expect(substr('nicholas', 8)).toBe('nicholas');
  expect(substr('nicholas', 10)).toBe('nicholas');
});

test('caps capitalizes the first letter of text', () => {
  expect(caps('nicholas chiang')).toBe('Nicholas chiang');
  expect(caps('Nicholas Chiang')).toBe('Nicholas Chiang');
  expect(caps('NICHOLAS CHIANG')).toBe('NICHOLAS CHIANG');
});

test('num truncates large numbers into readable text', () => {
  expect(num(10)).toBe('10');
  expect(num(999)).toBe('999');
  expect(num(1000)).toBe('1K');
  expect(num(1010)).toBe('1K');
  expect(num(1050)).toBe('1.1K');
  expect(num(1200)).toBe('1.2K');
  expect(num(125300)).toBe('125.3K');
  expect(num(999999)).toBe('999.9K');
  expect(num(1000000)).toBe('1M');
  expect(num(1010000)).toBe('1M');
  expect(num(1050000)).toBe('1.1M');
});

test('range initializes empty arrays of specified length', () => {
  expect(range(0, 3)).toMatchObject([null, null, null]);
});

function isInt(int: number): boolean {
  return parseInt(int.toString()) === int;
}

test('random generates random integers within a range', () => {
  const int = random(0, 10);
  expect(int).toBeLessThan(10);
  expect(int).toBeGreaterThanOrEqual(0);
  expect(int).toSatisfy(isInt);
});
