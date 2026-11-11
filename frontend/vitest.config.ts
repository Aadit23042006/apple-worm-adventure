import { mergeConfig } from 'vite'
import { configDefaults, defineConfig } from 'vitest/config'
import viteConfig from './vite.config.ts'

export default defineConfig((configEnv) =>
  mergeConfig(viteConfig(configEnv), {
    test: {
      exclude: [
        ...configDefaults.exclude,
        '**/e2e/**',
      ],
    },
  }),
)
