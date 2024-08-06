/** @type {import('tailwindcss').Config} */
const plugin = require('tailwindcss/plugin')

module.exports = {
  content: [
      './templates/**/*.html' //new
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#003f63',
        'account_info': '#F7FAFC',
        'account_background': '#F3F5F4',
        'form_outline': '#7E92B2',
        'form_input': '#B1BBD3',
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
      plugin(function ({ addVariant }) {
        addVariant('mobile-only', "@media screen and (max-width: theme('screens.sm'))"); // instead of hard-coded 640px use sm breakpoint value from config. Or anything
      }),
      // Add md breakpoint
      plugin(function ({ addVariant }) {
          addVariant('md', "@media screen and (min-width: theme('screens.md'))");
      }),
        // Add lg breakpoint
      plugin(function ({ addVariant }) {
          addVariant('lg', "@media screen and (min-width: theme('screens.lg'))");
      }),

  ],
}
