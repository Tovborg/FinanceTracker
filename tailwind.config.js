/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
      './templates/**/*.html' //new
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#003f63',
        'account-cards': '#002337',
        'secondary': '#3498DB',
        'accent': '#27AE60',
        'warning': '#E74C3C',
        'text': '#2C3E50',
        'button': '#077DC8',
        'button_hover': '#106097',
        'registration_text': '#027BC7',
        'cards': '#C3E0EB',
      'navbar': 'rgb(62,195,213)',
      'expense': 'rgb(255,84,96)',
      'income': 'rgb(65,220,101)',
      'date': 'rgb(225,224,230)',
      'background': '#ECF0F1',
      'table_row': 'rgb(255,255,255)',
      'navigation_mobile': '#D6E8F1',
      'sidebar': 'rgb(35,29,60)',
    },
      fontFamily: {
        'dansketext': ['Danske Text v2 Regular'],
      }
    },
  },
  plugins: [
      require('@tailwindcss/forms'),
  ],
}
