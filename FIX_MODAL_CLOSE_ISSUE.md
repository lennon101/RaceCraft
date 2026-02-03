# Fix: Load Known Race Modal Close Issue

## Problem Statement

When loading a known race:
1. The modal window remained open after loading a race
2. The page appeared to hang/freeze
3. The cancel button didn't work properly

## Root Cause Analysis

### Issue 1: Inconsistent Modal Display Methods
- **Problem**: `showKnownRaceModal()` used `knownRaceModal.style.display = 'flex'` 
- **Problem**: `hideModal()` used `modal.classList.remove('active')`
- **Result**: Modal couldn't be hidden because it wasn't using the `.active` class

### Issue 2: Alert Timing
- **Problem**: `alert()` was called AFTER `hideModal()`
- **Result**: User saw alert while modal was trying to close, causing confusion and making UI appear frozen

## Solution

### Change 1: Standardize Modal Display (Line 2087)
```javascript
// Before:
knownRaceModal.style.display = 'flex';

// After:
knownRaceModal.classList.add('active');
```

**Rationale**: All other modals in the app use `classList.add('active')` / `classList.remove('active')`. This change ensures consistency.

### Change 2: Proper Alert Sequence (Lines 2213-2220)
```javascript
// Before:
hideModal(knownRaceModal);
knownRaceSearch.value = '';
alert('Known race loaded successfully!...');

// After:
knownRaceSearch.value = '';
alert('Known race loaded successfully!...');
hideModal(knownRaceModal);
```

**Rationale**: Alert should display BEFORE closing the modal so the user can see both the alert and the race data loading. After the user acknowledges the alert, the modal closes cleanly.

## Testing Results

### Manual Testing ✅
- Modal opens correctly when "Load Known Race" button is clicked
- Races are displayed grouped by organiser
- Clicking "Load" on a race shows the success alert
- After acknowledging the alert, the modal closes properly
- Race data is correctly displayed in the form
- Cancel button works properly

### Browser Automation Testing ✅
Using Playwright automation:
- Verified modal opens with `active` class
- Confirmed alert displays before modal closes
- Verified modal closes after alert is dismissed
- Tested cancel button functionality

## Files Modified

- `static/js/app.js`
  - Line 2087: Changed modal display method
  - Lines 2213-2220: Reordered alert and hideModal calls

## Impact

- **User Experience**: Modal now closes properly after loading a race
- **Consistency**: All modals now use the same show/hide mechanism
- **No Freezing**: Page no longer appears to hang
- **Cancel Works**: Cancel button properly closes the modal

## Related Code Patterns

For reference, other modals in the codebase use this pattern:

```javascript
// Show modal
function showSaveModal() {
    saveModal.classList.add('active');
}

function showLoadModal() {
    loadModal.classList.add('active');
}

// Hide modal
function hideModal(modal) {
    modal.classList.remove('active');
}
```

The Known Races modal now follows this same pattern.
