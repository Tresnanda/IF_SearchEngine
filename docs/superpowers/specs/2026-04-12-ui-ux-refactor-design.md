# UI/UX Refactor for Information Retrieval System

## Overview
A comprehensive redesign of the Information Retrieval System's Next.js frontend. The goal is to transition the interface from a heavy, colorful "glassmorphism" aesthetic to a hyper-functional, fast, and sleek "Swiss Modernism" (Notion/Linear-inspired) design with a "Command Palette / Raycast" interaction flow.

## Design System & Aesthetic
**Design Pattern:** Marketplace/Directory (Search-focused)
**Style:** Swiss Modernism 2.0 (Clean, grid-based, monochrome, mathematical spacing)

### Typography
*   **Primary Font:** Inter (Sans-Serif)
*   **Hierarchy Strategy:** Rely on varied font weights (e.g., `font-semibold` for titles, `font-regular` for body text) rather than varied colors to establish clear visual hierarchy.

### Color Palette
*   **Backgrounds:** Light gray/off-white (`#fafafa` or `bg-zinc-50`) for the application background, pure white (`#ffffff`) for the central search container.
*   **Borders:** Extremely subtle gray borders (`#e4e4e7` or `border-zinc-200`).
*   **Text:** High-contrast dark grays/blacks (`#09090b` or `text-zinc-950`) for primary text, muted grays (`#71717a` or `text-zinc-500`) for secondary information (metadata, filenames).
*   **Accents:** Minimal use of bright colors. A subtle blue (`#2563eb` or `text-blue-600`) reserved exclusively for active states or primary calls-to-action (CTAs).

### Key Visual Effects
*   **Shadows:** Remove large colorful gradients. Use crisp, soft drop-shadows (`shadow-sm`, `shadow-md`, `shadow-lg`) to create depth, making the central search palette float above the background.
*   **Transitions:** Fast, subtle hover states (150ms-300ms) with minimal scaling (`hover:-translate-y-[1px]`) or background color shifts.

## Architecture & Layout (Interaction Flow)

### 1. The Container (Command Palette Style)
*   The application centers around a single, fixed-width container (`max-w-3xl`) positioned in the top-middle of the viewport (with a top margin/padding to prevent it from hugging the ceiling).
*   This container houses both the search input and the search results.

### 2. The Search Input
*   A large, borderless (or extremely subtle bottom-border) input field occupying the top section of the container.
*   Features a prominent search icon.

### 3. The Results Drawer
*   Appears seamlessly directly below the search input *within* the same floating container (or directly attached to it).
*   Expands downwards dynamically as results arrive from the backend.
*   Includes a subtle scrollbar if the list of results exceeds the viewport height.

## Component Specifications

### Search Result Item
Each document returned from the BM25 backend will be rendered as a focused, scannable block.

1.  **Header (Title):** Document title rendered in dark, semibold text. Removes the large abstract icons to save horizontal space.
2.  **Metadata (Score & Filename):**
    *   BM25 Score displayed in a tiny, minimalist pill (e.g., `bg-blue-50 text-blue-600`).
    *   Filename displayed in small, muted text (`text-zinc-500 text-xs`).
3.  **Contextual Snippet:**
    *   The 200-character search snippet is styled as a "quote block" with a faint left-border (`border-l-2 border-zinc-200`) or a very subtle gray background (`bg-zinc-50/50`) to differentiate it from the title and metadata.
    *   Text is clamped to 2-3 lines (`line-clamp-3`).
4.  **Actions (View/Download):**
    *   Minimalist icon-buttons replacing the current large, brightly colored action buttons.
    *   Positioned neatly to the right side of the result item or inline below the snippet.

## Implementation Steps
1.  **Dependencies:** Ensure `framer-motion` and `lucide-react` are maintained for animations and icons. Verify `globals.css` uses Tailwind's zinc color palette properly.
2.  **`page.tsx` Update:** Refactor the main layout structure to support the centered, floating Command Palette container instead of the current full-page dispersed layout.
3.  **`SearchResults.tsx` Rewrite:** Strip out the `glass-card` styling, colorful gradients, and large icons. Implement the Swiss Modernism grid and tight typography for the result items.
4.  **`SearchFeedback.tsx` Update:** Ensure the feedback component (if retained) matches the new minimal styling, likely placing it discretely at the very bottom of the results drawer.
5.  **Testing:** Verify the UI looks correct across desktop and mobile breakpoints, ensuring the central container remains responsive.