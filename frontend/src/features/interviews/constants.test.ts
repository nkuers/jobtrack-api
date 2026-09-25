import { expect, test } from 'vitest'

import { toLocalInput } from './constants'

test('round-trips an API UTC datetime through a browser local datetime input', () => {
  const utc = '2026-10-01T02:30:00.000Z'
  expect(new Date(toLocalInput(utc)).toISOString()).toBe(utc)
})
