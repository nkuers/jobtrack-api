import { expect, test } from 'vitest'

import { allowedTransitions } from './constants'

test('mirrors the backend application status machine', () => {
  expect(allowedTransitions.saved).toEqual(['applied', 'withdrawn'])
  expect(allowedTransitions.applied).toEqual([
    'screening',
    'rejected',
    'withdrawn',
  ])
  expect(allowedTransitions.screening).toEqual([
    'interview',
    'rejected',
    'withdrawn',
  ])
  expect(allowedTransitions.interview).toEqual([
    'offer',
    'rejected',
    'withdrawn',
  ])
  expect(allowedTransitions.offer).toEqual(['archived'])
  expect(allowedTransitions.rejected).toEqual(['archived'])
  expect(allowedTransitions.withdrawn).toEqual(['archived'])
  expect(allowedTransitions.archived).toEqual([])
})
