/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        "wa-dark": "#075E54",
        "wa-green": "#25D366",
        "wa-user": "#DCF8C6",
        "wa-bg": "#F0F2F5",
      },
    },
  },
  plugins: [],
};
