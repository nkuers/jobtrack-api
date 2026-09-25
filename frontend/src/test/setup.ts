import '@testing-library/jest-dom/vitest'
import 'temporal-polyfill/global'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => cleanup())
