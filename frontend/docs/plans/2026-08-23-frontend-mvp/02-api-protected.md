# Task 2: API Client & Protected Routes
- Create the authenticated API client (`lib/api.ts`).
- Implement route protection so unauthenticated users cannot access `/dashboard`, `/chat`, etc.
- When logged in, Header should display the user's name/email and a link to the dashboard.
- Upon successful login via the modal, the user should be immediately redirected to the blank `/dashboard` page.
