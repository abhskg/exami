# ⚛️ ExamI — Frontend

This is the client-side user interface for **ExamI**, built using **React (Vite + TypeScript)** and styled using **Modern Vanilla CSS**. It provides a fully responsive layout with clean glassmorphic components, active states, dynamic progress trackers, and real-time exam simulations.

---

## 🎨 Design Foundations & Premium Aesthetics

The frontend is built with high-quality design principles, eschewing generic templates in favor of a customized aesthetic:

- **HSL Palette**: Rich HSL gradients using slates, deep indigos, and vibrant violets to create an executive, calming dark-mode layout.
- **Glassmorphism**: Backdrop blurs (`backdrop-filter`), thin semi-transparent borders, and micro-shadows to present premium floating cards.
- **Micro-Animations**: Hover animations on cards and active transitions on buttons, navigation tabs, and state selectors.
- **Visual Indicators**: Live client-side database connectivity indicators, real-time timer counters, dynamic radial scoring charts, and upload progress status tags.

---

## 📁 Directory Structure

```
frontend/
├── public/           # Static public assets (icons, images)
├── src/
│   ├── components/   # Reusable UI widgets
│   │   └── KnowledgeCatalog.tsx # Catalog administration dashboard widget
│   │
│   ├── pages/        # View pages and gateway components
│   │   ├── AuthPage.tsx       # Dual-column responsive authentication gateway
│   │   ├── LoginForm.tsx      # Validation-enabled login component
│   │   └── SignupForm.tsx     # Registration form with status feedback
│   │
│   ├── hooks/        # Shared custom React hooks for global/local states
│   ├── services/     # API request communications layer
│   │
│   ├── App.tsx       # Main router, navigation sidebar, and application layout
│   ├── index.css     # Global design tokens, HSL variables, utility styles
│   ├── main.tsx      # Application bootstrapper
│   └── vite-env.d.ts # TypeScript compiler variables definitions
│
├── index.html        # Main HTML body container (importing Outfit & Inter Google Fonts)
├── package.json      # Node.js build configurations & package version requirements
├── tsconfig.json     # TypeScript environment rule settings
├── .prettierrc       # Prettier code style rules [NEW]
└── vite.config.ts    # Vite bundler parameters (configured to run on port 3000)
```

---

## ⚙️ Environment Configuration

Copy `frontend/.env.example` to `frontend/.env`:

```ini
# Address pointing to the active FastAPI backend service
VITE_API_URL=http://127.0.0.1:8000

# Client-side validation limit for document uploads (in MB)
VITE_MAX_FILE_SIZE_MB=15
```

---

## 🚀 Setup & Execution

### Prerequisites

- Node.js (v18 or higher)
- npm (v9 or higher)

### Setup Commands

1.  **Install Packages**:
    Navigate to the `frontend/` directory and install node modules:
    ```bash
    npm install
    ```
2.  **Start Development Server**:
    Run Vite server on port `3000` (auto-opened or accessible on `http://localhost:3000`):
    ```bash
    npm run dev
    ```
3.  **Build Production Assets**:
    Compile and bundle production code into `dist/`:
    ```bash
    npm run build
    ```
4.  **Preview Production Build**:
    Preview the production output locally:
    ```bash
    npm run preview
    ```

---

## 📄 Key Components & UI Modules

### 1. Global Navigation & Sidebar

Maintained in [App.tsx](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/frontend/src/App.tsx), providing a layout with a profile footer, active page routing, and a real-time health indicator check verifying the FastAPI backend's availability status.

### 2. Authentication Gateway (`AuthPage.tsx`)

A secure split-layout containing the [LoginForm](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/frontend/src/pages/LoginForm.tsx) and [SignupForm](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/frontend/src/pages/SignupForm.tsx). Handles JWT token caching and redirects to the internal app workspace.

### 3. Document Ingestion Zone

Allows selecting/creating topics, dragging and dropping files (PDFs, Markdown, text files under the configured limit, default 15MB), and tracking parsing pipelines via a polling job status component.

### 4. Knowledge Catalog Dashboard (`KnowledgeCatalog.tsx`)

Located at [KnowledgeCatalog.tsx](file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/frontend/src/components/KnowledgeCatalog.tsx), this sub-view allows administrators to manage ingested Documents, search Content Chunks/Embeddings, edit Questions and options, and manage/merge tags. It includes an integrated visual analytics panel at the top.

### 5. Exam Configuration & Simulator (`ExamConfigPanel`)

Provides topic dropdowns, slider ranges for question count limits, difficulty level toggles (`Easy`, `Medium`, `Hard`, `Mixed`), and tag chips for filtered generations. Launches practice or timed simulations with integrated timers.
