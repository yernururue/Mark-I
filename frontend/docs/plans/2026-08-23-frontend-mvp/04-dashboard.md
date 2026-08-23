# Task 4: Dashboard

## Goal
Build the main dashboard view (F11) that displays real-time updates of the user's progress, agent observations, and decision transparency logs (F14).

## Architecture & Data Flow
The dashboard uses a **Real-Time Data Layer** connected directly to Firestore.
- **Hooks:** Custom hooks (e.g., `useFirestoreQuery`) will subscribe to the user's documents via `onSnapshot` for immediate UI updates.
- **State:** No complex global state management (like Redux) is needed since Firestore serves as the single source of truth and realtime state provider.

## Required Components

### 1. Skill Visualization (`SkillRadar.tsx`)
- **Requirement:** Display current skill scores (F6).
- **Design:** Use `recharts` to render a Radar Chart or Horizontal Bar Chart.
- **Data Source:** `users/{uid}/skills` or fields on the main profile document.

### 2. Observation Feed (`ObservationFeed.tsx`)
- **Requirement:** A chronological feed of all meaningful events (GitHub analysis, opportunities, chat insights) (F7).
- **Design:** A scrollable list of cards. Each card displays the source icon (GitHub, Web, Chat), a summary, the concept practiced, and sentiment.
- **Data Source:** Collection `users/{uid}/observations`.

### 3. Decision Transparency Log (`DecisionLog.tsx`)
- **Requirement:** Show recent decisions made by the agent's explicit policy engine (F14).
- **Design:** A sidebar or dedicated section explaining *why* the agent notified or stayed silent (e.g., "Notified because significance 8 > threshold 5").
- **Data Source:** Collection `users/{uid}/decisions`.

### 4. Quick Actions / Overview
- Goal reminder and current intensity setting (Chill / Normal / Brutal).
- A button to quickly jump to the Unified Chat.
