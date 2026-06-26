# Design System Document: The Agrarian High-End Narrative

## 1. Overview & Creative North Star: "The Digital Agronomist"
This design system moves away from the "industrial utility" of traditional agricultural software and embraces a **"Digital Agronomist"** aesthetic—an editorial, high-fidelity experience that treats data as a premium asset. 

The North Star is the intersection of **organic growth and precision engineering**. We achieve this by rejecting the rigid, "boxed-in" grids of standard SaaS apps. Instead, we use intentional asymmetry, expansive breathing room, and overlapping "glass" layers to create a UI that feels alive and premium. Every interface should feel like a curated report from a world-class consultant, not a spreadsheet.

---

### 2. Colors: Tonal Depth & Organic Transitions
We utilize a sophisticated palette rooted in deep forest tones and vibrant bio-luminescent accents.

*   **Primary Hierarchy:** `primary` (#003527) and `primary_container` (#064E3B) provide an authoritative, grounding base. 
*   **The Accent Pulse:** `secondary` (#416900) and `secondary_fixed` (#acf847) are used sparingly to draw the eye to growth metrics and critical "ready-to-harvest" actions.

#### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders to section content. Traditional borders create visual noise that breaks the premium "editorial" flow. 
*   **The Alternative:** Define boundaries through background color shifts. Place a `surface_container_low` card atop a `surface` background. The shift in tone is the boundary.

#### Surface Hierarchy & Nesting
Treat the UI as a physical stack of semi-translucent materials:
1.  **Base:** `surface` (#f9f9f8) for the main canvas.
2.  **Sectioning:** `surface_container_low` for large content areas.
3.  **Emphasis:** `surface_container_lowest` (#ffffff) for the most prominent cards to create a "lifted" effect.

#### The "Glass & Gradient" Rule
To avoid a flat, "templated" feel, use **Signature Textures**. 
*   **Hero Headers:** Use a linear gradient from `primary` (#003527) to `primary_container` (#064E3B) at a 135-degree angle. 
*   **Glassmorphism:** For floating navigation or weather widgets, use `surface_container_lowest` with 80% opacity and a `24px` backdrop-blur.

---

### 3. Typography: Editorial Authority
We pair **Manrope** (Display/Headlines) with **Inter** (Body/Labels) to balance character with high-efficiency readability.

*   **Display-LG (Manrope, 3.5rem):** Reserved for high-level "Hero" data points (e.g., Total Yield Percentage). Use `-0.02em` letter spacing for a tighter, premium feel.
*   **Headline-MD (Manrope, 1.75rem):** Used for module titles like "Soil Health" or "Market Trends."
*   **Title-SM (Inter, 1rem):** The standard for card headers. Bold weight.
*   **Body-MD (Inter, 0.875rem):** Used for all descriptive text. Line height should be a generous `1.5` to ensure legibility in field conditions.

---

### 4. Elevation & Depth: Tonal Layering
In this system, "Elevation" is a measure of light and density, not just shadows.

*   **The Layering Principle:** Depth is achieved by stacking. A `surface_container_lowest` card placed on a `surface_container_low` background creates a natural, soft lift.
*   **Ambient Shadows:** For "Active" cards or floating action buttons, use an extra-diffused shadow: `0px 12px 32px rgba(0, 33, 23, 0.06)`. Note the use of a deep green tint in the shadow rather than pure black.
*   **The "Ghost Border" Fallback:** If a border is required for accessibility, use the `outline_variant` token at **15% opacity**. It should be felt, not seen.

---

### 5. Components: Stylistic Directives

#### Cards & Modules
*   **The Roundedness Scale:** Apply `xl` (1.5rem) to all primary cards. This softness mimics organic shapes found in nature.
*   **Internal Padding:** Use spacing `8` (2rem) for card internals. Never crowd agricultural data; it needs room to "breathe."
*   **Visual Separation:** Forbid the use of divider lines. Use vertical white space (`spacing 6` or `8`) to separate list items within a card.

#### Buttons (The Call-to-Action)
*   **Primary:** A gradient fill using `primary` to `primary_container`. `rounded-full` (9999px) for a modern, sleek profile.
*   **Secondary:** `surface_container_high` background with `on_primary_fixed_variant` text. No border.

#### Data Visualization (Agri-Specific)
*   **Soil & Weather Chips:** Use `secondary_container` (#acf847) for positive growth states and `tertiary_fixed_dim` (#ffb77d) for warning/dry states.
*   **The "Pulse" Indicator:** Use a soft, breathing animation on a small `secondary` dot to indicate real-time sensor connectivity.

#### Input Fields
*   **Style:** Minimalist. No bottom line. Use `surface_container_highest` as a subtle fill with `rounded-md` (0.75rem). Labels should use `label-md` in `on_surface_variant` color, positioned above the field.

---

### 6. Do's and Don'ts

#### Do:
*   **Use Asymmetry:** Align high-level weather data to the left and offset the corresponding soil map slightly to the right to create a "composed" editorial layout.
*   **Embrace Negative Space:** If a screen feels "empty," don't fill it. Premium design is defined by what you leave out.
*   **Use Tonal Transitions:** Transition backgrounds from `surface` to `surface_container_low` to signal a change in content context (e.g., moving from "Dashboard" to "Settings").

#### Don't:
*   **Don't use pure black (#000000):** Use `on_background` (#1a1c1c) for text to maintain a softer, high-end feel.
*   **Don't use 100% opaque borders:** They look "cheap" and interrupt the organic flow of the farming data.
*   **Don't crowd the margins:** Ensure a minimum of `spacing 10` (2.5rem) on the outer edges of the screen layout to maintain a "high-end gallery" feel.