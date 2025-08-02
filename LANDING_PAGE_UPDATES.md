# Landing Page Updates

## Overview
Updated the landing page to include a conference carousel section between the hero and features sections, and replaced mountain images with conference-related images.

## Changes Made

### 1. Conference Carousel Section
- **Location**: Added between hero section and features section
- **Features**:
  - Horizontal scrollable container with conference cards
  - Left (<) and Right (>) arrow buttons for manual navigation
  - Responsive design (arrows hidden on mobile, cards smaller on mobile)
  - Smooth scrolling animation
  - Auto-hide arrows when at start/end of scroll

### 2. Conference Cards
Each card displays:
- Conference status badge (Live/Upcoming)
- Primary research area
- Conference name and acronym
- Venue and city information
- Start and end dates
- "Learn More" link (searches for the conference)
- "Join Conference" button (links to login)

### 3. Search Button
- Large "Browse All Conferences" button below the carousel
- Links to `/conference/search/` page
- Includes search icon and hover effects

### 4. Hero Image Updates
- Replaced mountain images with conference-related images:
  - Conference presentation
  - Conference hall
  - Research collaboration

### 5. Backend Changes
- Added `get_available_conferences()` function in `conference_mgmt/views.py`
- Updated `root_redirect()` function to pass conference data to landing page
- Conferences filtered by: `is_approved=True` and `status__in=['upcoming', 'live']`
- Limited to 10 conferences, ordered by start date

### 6. Responsive Design
- Mobile-friendly: Cards are smaller (w-72 vs w-80)
- Arrows hidden on mobile devices
- Responsive scroll amounts based on screen size
- Touch-friendly scrolling on mobile

### 7. JavaScript Functionality
- Manual scroll with arrow buttons
- Smooth scrolling animation
- Dynamic arrow visibility based on scroll position
- Responsive scroll amounts
- Window resize handling

## Files Modified
1. `templates/landing.html` - Main landing page template
2. `conference_mgmt/views.py` - Added conference data function
3. `conference_mgmt/urls.py` - Updated root redirect to include conferences
4. `dashboard/management/commands/check_landing_conferences.py` - Test command

## Testing
- Created management command to verify conference availability
- Found 6 conferences available for display
- Server runs without errors
- Responsive design tested for mobile and desktop

## Usage
The landing page now automatically displays available conferences to visitors, encouraging them to:
1. Browse available conferences
2. Click "Learn More" to search for specific conferences
3. Click "Browse All Conferences" to see the full search page
4. Register/login to join conferences 