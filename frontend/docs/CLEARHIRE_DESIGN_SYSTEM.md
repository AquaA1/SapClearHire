# ClearHire UI Design System Specification
**Adapted from `design.md` for ClearHire Evidence Transparency Platform**

---

## 1. Vision & Core Principles

ClearHire is an **AI-Assisted Hiring Evidence Transparency Platform**. Every visual and functional element must reinforce trust, mathematical verifiability, and factual grounding.

### Core Tenets
1. **Evidence First, Zero Hallucination**:
   - We **never** display arbitrary percentage circles, fake AI confidence gauges, or ungrounded match percentages.
   - Every metric represents real counted units: Requisitions, Verified Criteria, Discrepancies, or Cryptographic Ledger Blocks.
2. **Deterministic Hierarchy**:
   - Spacing, typography, and borders follow a strict mathematical 4px scale.
   - Clear contrast separation between Canvas (`#090A0C`), Surface (`#121519`), Card (`#181B21`), and Elevated Popovers (`#262A34`).
3. **Dual Atmosphere Paradigm**:
   - **Public Landing Page**: Minimalist, cinematic black-and-white experience with moving fluid light field, constellation nodes, and prompt pills.
   - **Authenticated Application**: High-density charcoal SaaS environment with mint (`#10B981`) and cyan (`#38BDF8`) verification accents.

---

## 2. Token Dictionary

### 2.1 Spacing Scale (4px Base Grid)

| Token Name | Value | Rem | Primary Usage |
| :--- | :--- | :--- | :--- |
| `spacing.xxs` | 4px | 0.25rem | Micro gaps, badge inner padding, inline icon offsets |
| `spacing.xs` | 8px | 0.5rem | Input label spacing, button horizontal gaps, compact gutters |
| `spacing.sm` | 12px | 0.75rem | Compact padding, table cell vertical spacing, item separation |
| `spacing.md` | 16px | 1.0rem | Standard card padding, grid gaps, form group spacing |
| `spacing.lg` | 24px | 1.5rem | Large card padding, dashboard column separation |
| `spacing.xl` | 32px | 2.0rem | Section spacing within dashboards |
| `spacing.xxl` | 48px | 3.0rem | Major page section breaks |
| `spacing.section` | 96px | 6.0rem | Hero section vertical spacing |

---

### 2.2 Border Radius Scale

| Token Name | Value | Usage |
| :--- | :--- | :--- |
| `rounded-xs` | 4px | Micro tags, code badges, inline status markers |
| `rounded-sm` | 6px | Small action buttons, dropdown items, compact inputs |
| `rounded-md` | 8px | Standard inputs, form controls, secondary buttons |
| `rounded-lg` | 12px | Dropdown menus, modal dialog insets, sub-panels |
| `rounded-xl` | 16px | Standard cards, notification banners |
| `rounded-2xl` | 24px | Large overview containers, prominent dashboard cards |
| `rounded-pill` / `rounded-full` | 9999px | Status badges, category pills, filter chips, circular icon buttons |

---

### 2.3 Color Tokens & Semantic Intent

```css
:root {
  /* Canvas & Surfaces */
  --ch-canvas: #090A0C;             /* Deepest canvas background */
  --ch-surface: #121519;            /* Base panel & sidebar */
  --ch-card: #181B21;               /* Standard content card */
  --ch-card-secondary: #20242C;     /* Hover state & secondary card */
  --ch-elevated: #262A34;           /* Modals, popovers, floating menus */
  --ch-border: rgba(255, 255, 255, 0.08); /* Hairline card borders */
  --ch-border-hover: rgba(255, 255, 255, 0.16);

  /* Typography */
  --ch-text-primary: #F9FAFB;       /* High-contrast headings & data values */
  --ch-text-secondary: #9CA3AF;     /* Standard body & field labels */
  --ch-text-muted: #6B7280;         /* Captions, timestamps, inactive states */

  /* Evidence & Brand Accents */
  --ch-primary: #10B981;            /* Mint: Verified evidence, primary CTA */
  --ch-primary-hover: #059669;      /* Mint dark active */
  --ch-cyan: #38BDF8;               /* Cyan: Chain hashes, audit explorer */
  --ch-amber: #F59E0B;              /* Amber: Needs review, ambiguous evidence */
  --ch-danger: #EF4444;             /* Red: Unmatched criteria, tamper alerts */
}
```

---

### 2.4 Evidence State Color Palette

ClearHire uses semantic colors strictly for factual evidence verification states:

| Status | Hex | Tailwind Class | Semantic Meaning |
| :--- | :--- | :--- | :--- |
| **Supported / Verified** | `#10B981` | `text-emerald-400 bg-emerald-500/10 border-emerald-500/20` | OCR quote and verbatim citation verified |
| **Ambiguous / Review** | `#F59E0B` | `text-amber-400 bg-amber-500/10 border-amber-500/20` | Human adjudication or candidate clarification required |
| **Not Found** | `#EF4444` | `text-rose-400 bg-rose-500/10 border-rose-500/20` | Criterion absent from resume or claims contradicted |
| **Clarified / Audit** | `#38BDF8` | `text-sky-400 bg-sky-500/10 border-sky-500/20` | Candidate provided additional proof or event logged |

---

## 3. Typography Hierarchy

ClearHire uses **Inter** (system fallback) for UI and **JetBrains Mono** for cryptographic hashes, line coordinates, and code citations.

| Role | Size | Line Height | Weight | Tailwind Class |
| :--- | :--- | :--- | :--- | :--- |
| **Display (Hero)** | 48px - 64px | 1.1 | Bold / ExtraBold | `text-4xl md:text-6xl font-bold tracking-tight` |
| **Title 1 (Page Title)** | 24px | 32px | Bold | `text-2xl font-bold text-white tracking-tight` |
| **Title 2 (Card Header)** | 16px | 24px | SemiBold | `text-base font-semibold text-white` |
| **Title 3 (Subheader)** | 14px | 20px | SemiBold | `text-sm font-semibold text-white/90` |
| **Body (Default)** | 14px | 20px | Regular / Medium | `text-sm text-zinc-300 leading-normal` |
| **Caption / Meta** | 12px | 16px | Regular | `text-xs text-zinc-400 leading-relaxed` |
| **Micro / Status** | 11px | 14px | Medium | `text-[11px] font-medium tracking-wide` |
| **Monospace / Hashes** | 11px - 13px | 16px | Regular / Medium | `font-mono text-zinc-400` |

---

## 4. Reusable Component Library (`src/components/ui/`)

All standard controls and view containers are centralized under `src/components/ui/`:

### 4.1 Button (`Button.tsx`)
```tsx
import { Button } from '@/components/ui';

// Primary CTA (Mint)
<Button variant="primary" size="md">Approve Decision</Button>

// Secondary Card Button
<Button variant="secondary" size="sm">Export Report</Button>

// Outline
<Button variant="outline" size="md">Inspect Chain</Button>

// White Landing CTA
<Button variant="white" size="lg" leftIcon={<ArrowRight />}>Get Started</Button>

// Danger
<Button variant="danger" size="sm">Flag Discrepancy</Button>
```

### 4.2 IconButton (`IconButton.tsx`)
```tsx
import { IconButton } from '@/components/ui';
import { RefreshCw } from 'lucide-react';

<IconButton
  label="Refresh Ledger"
  variant="secondary"
  shape="circular"
  size="md"
  onClick={handleRefresh}
>
  <RefreshCw size={16} />
</IconButton>
```

### 4.3 Input & Form Controls (`Input.tsx`)
- `Input`: 40px height, 8px radius, label, helper text, error state, and icon slots.
- `PasswordInput`: Built-in show/hide toggle.
- `SearchInput`: Built-in search icon and clear button.

```tsx
import { Input, PasswordInput, SearchInput } from '@/components/ui';

<Input
  label="Requisition Title"
  placeholder="Senior Distributed Systems Engineer"
  helperText="Must match SAP SuccessFactors job code"
  error={formError}
/>

<PasswordInput
  label="Master Key"
  value={key}
  onChange={(e) => setKey(e.target.value)}
/>

<SearchInput
  value={query}
  onChange={(e) => setQuery(e.target.value)}
  onClear={() => setQuery('')}
/>
```

### 4.4 Status Badge (`Badge.tsx`)
```tsx
import { Badge } from '@/components/ui';

<Badge variant="success" dot>OCR Grounded</Badge>
<Badge variant="warning" dot>Flagged for Review</Badge>
<Badge variant="danger" dot>Missing Evidence</Badge>
<Badge variant="info">SHA-256 Verified</Badge>
```

### 4.5 Card System (`Card.tsx`)
```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui';

<Card variant="default">
  <CardHeader>
    <CardTitle>Requisition Overview</CardTitle>
    <CardDescription>Verified qualifications extracted from dossier</CardDescription>
  </CardHeader>
  <CardContent>
    ...
  </CardContent>
  <CardFooter>
    <Button variant="secondary" size="sm">View Audit Log</Button>
  </CardFooter>
</Card>
```

### 4.6 Dense Data Table (`Table.tsx`)
```tsx
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui';

<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Candidate</TableHead>
      <TableHead>Requisition</TableHead>
      <TableHead>Status</TableHead>
      <TableHead className="text-right">Action</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell className="font-semibold text-white">Elena Rostova</TableCell>
      <TableCell>Staff Backend Engineer</TableCell>
      <TableCell><Badge variant="success">Verified</Badge></TableCell>
      <TableCell className="text-right"><Button size="sm">Inspect</Button></TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### 4.7 Category Tabs (`Tabs.tsx`)
```tsx
import { Tabs } from '@/components/ui';

<Tabs
  items={[
    { id: 'all', label: 'All Candidates', count: 42 },
    { id: 'pending', label: 'Needs Review', count: 3 },
    { id: 'verified', label: 'Verified', count: 39 },
  ]}
  activeId={activeTab}
  onChange={setActiveTab}
  variant="contained"
/>
```

### 4.8 Modal Dialog (`Modal.tsx`)
- Fully accessible dialog with focus management, backdrop blur, Esc key handling, and responsive width clamps.

### 4.9 Empty State (`EmptyState.tsx`) & Loading Spinner (`LoadingSpinner.tsx`)
- Standardized feedback components preventing blank screen flashes.

---

## 5. Prohibited Anti-Patterns

1. **NO Arbitrary Percentage Rings**: Never display radial progress dials with fabricated percentages like "94% AI Fit".
2. **NO Hallucinatory Scores**: No fake "Trust Scores" or "Confidence Indexes" unless backed by a 1:1 verified criterion count.
3. **NO Excessive Neon Glows**: Keep borders to subtle hairlines (`rgba(255, 255, 255, 0.08)`).
4. **NO Inconsistent Margins**: Every margin and padding must derive from the 4px scale (`p-1`, `p-2`, `p-3`, `p-4`, `p-5`, `p-6`, `p-8`).
