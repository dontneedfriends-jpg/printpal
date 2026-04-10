### Performance Issue Report

**Title**: Performance: Online filament tab loads slowly (5+ sec)

**Description**:

## Problem
The online filament (ShpoolkenDB) tab takes 5+ seconds to load and becomes unresponsive when users type in the search field.

## Root Causes

### Critical Issue #1: Auto-Search on Page Load
When the tab opens, it automatically executes `searchFilaments()` (line 198-200 of shpoolken.html), fetching and rendering all 100 filaments without user interaction.

### Critical Issue #2: No Search Debouncing
The search input uses `oninput="searchFilaments()"` (line 25), firing on every keystroke. Typing "PLA" triggers 3 separate API calls and 3 full page re-renders.

### Critical Issue #3: Inefficient DOM Rendering
Lines 124-165 of shpoolken.html render 100+ cards by concatenating strings in a loop, then updating `innerHTML` in one large operation. This causes massive browser reflow/repaint.

### Critical Issue #4: No Pagination Support
Backend always returns max 100 results (app.py line 1300), converting each SQLite row to dict. No pagination or lazy loading.

### Critical Issue #5: CSS Transitions on Initial Render
Line 276 applies `transition: all 0.2s ease` to cards, triggering animations on the initial 100-card render, causing jank.

## Performance Impact
- **Current**: 2-3s initial load, 3 API calls per 3-character search
- **Expected**: 0.3s with fixes, 1 API call per search

## Suggested Fixes

1. **Remove auto-search** (lines 198-200): Don't fetch on page load
2. **Add debouncing**: Wait 300ms after user stops typing before searching
3. **Add pagination**: Return 20 results per page instead of 100
4. **Optimize rendering**: Use single string concatenation instead of +=, add HTML escaping
5. **Disable transitions on initial render**: Only animate on hover after initial render

## Files Affected
- `electron-app/filament-calculator/templates/shpoolken.html` (lines 25, 107-165, 198-200, 276)
- `electron-app/filament-calculator/app.py` (lines 1287-1303)