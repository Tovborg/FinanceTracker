/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
      './templates/**/*.html' //new
  ],
  theme: {
    extend: {
      colors: {
      'navbar': 'rgb(62,195,213)',
      'expense': 'rgb(255,84,96)',
      'income': 'rgb(65,220,101)',
      'date': 'rgb(225,224,230)',
      'background': 'rgb(247,247,250)',
      'table_row': 'rgb(255,255,255)',
      'navigation_mobile': '#CFE8F3',
    }
    },
  },
  plugins: [],
}
