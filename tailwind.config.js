/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './gestion/templates/**/*.html',
    './login/templates/**/*.html',
    './carga_alumnos/templates/**/*.html',
    './gestion/**/*.py',
    './carga_alumnos/**/*.py',
  ],
  theme: {
    extend: {
      colors: {
        brand: '#4f46e5'
      }
    },
  },
  plugins: [],
}
