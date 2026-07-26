// Strict flat ESLint config (ESLint 9+). Copy to project root as
// eslint.config.mjs, then:
//   npm i -D eslint typescript-eslint eslint-plugin-unicorn
//
// Keep the .mjs extension. This file uses ESM `import`, and naming it
// eslint.config.js only works when package.json declares "type": "module" —
// otherwise Node parses it as CommonJS and ESLint dies with
// "SyntaxError: Cannot use import statement outside a module". .mjs is
// unambiguous and works in both kinds of project.
//
// Uses the *TypeChecked* variants, which require a real tsconfig and are
// substantially stricter than the syntactic-only presets — they can see types,
// so they catch floating promises, unsafe `any` flow, and bad awaits.

import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import unicorn from 'eslint-plugin-unicorn'

export default tseslint.config(
  js.configs.recommended,

  // strictTypeChecked > strict > recommended. Includes no-unsafe-* rules that
  // stop `any` from silently propagating through the codebase.
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,

  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: { unicorn },
    rules: {
      ...unicorn.configs.recommended.rules,

      // --- dead code ---
      'no-unused-private-class-members': 'error',
      '@typescript-eslint/no-unused-vars': [
        'error',
        // Underscore prefix is the documented opt-out, e.g. (_req, res).
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'all' },
      ],

      // --- async correctness: the most common real bug class in TS ---
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/await-thenable': 'error',
      '@typescript-eslint/require-await': 'error',
      '@typescript-eslint/return-await': ['error', 'always'],

      // --- escape hatches must be justified in writing ---
      '@typescript-eslint/ban-ts-comment': [
        'error',
        { 'ts-expect-error': 'allow-with-description', 'ts-ignore': true },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',

      // --- consistency ---
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { fixStyle: 'inline-type-imports' },
      ],
      'eqeqeq': ['error', 'always', { null: 'ignore' }],
      'no-console': ['warn', { allow: ['warn', 'error'] }],

      // unicorn defaults that fight normal code more than they help
      'unicorn/prevent-abbreviations': 'off',
      'unicorn/no-null': 'off',
    },
  },

  {
    // Test files: assertions and non-null access are idiomatic there.
    files: ['**/*.test.ts', '**/*.spec.ts', '**/tests/**'],
    rules: {
      '@typescript-eslint/no-non-null-assertion': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
    },
  },

  { ignores: ['dist/**', 'build/**', 'coverage/**', 'node_modules/**'] },
)
