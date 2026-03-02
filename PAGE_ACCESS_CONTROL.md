# Page Access Control System

## Overview

The Page Access Control system allows administrators to manage which user roles can access specific pages in the application. This provides fine-grained access control beyond the basic user role system.

## User Roles

The system supports three user roles:

1. **Basic** - Limited access (Wordle, Trivia, basic features)
2. **User** - Standard user access (Wrestling, most features)
3. **Admin** - Full administrative access (all pages including admin panel)

## How It Works

### Database Schema

A new `page_access` table stores configuration for each page:
- `page_name` - URL slug/identifier (e.g., "sportsbook", "wordle")
- `display_name` - Human-readable name
- `allowed_roles` - Array of roles that can access the page
- `is_active` - Enable/disable page access
- `description` - Optional description

### Backend API

**Endpoints** (all require authentication):

- `GET /api/admin/page-access` - List all page access configurations (Admin only)
- `GET /api/admin/page-access/{page_name}` - Get specific page configuration (Admin only)
- `POST /api/admin/page-access` - Create new page access rule (Admin only)
- `PUT /api/admin/page-access/{page_name}` - Update page access rule (Admin only)
- `DELETE /api/admin/page-access/{page_name}` - Delete page access rule (Admin only)
- `POST /api/admin/page-access/check` - Check if current user has access to a page
- `GET /api/admin/available-roles` - Get list of available roles

### Frontend Protection

Each protected page includes an inline script in the `<head>` that:
1. Checks if the user is logged in
2. Calls the `/api/admin/page-access/check` endpoint
3. Redirects to `/access-denied.html` if access is denied

Example implementation:
```html
<script>
    (async function() {
        const API_URL = 'http://localhost:8000';
        const token = localStorage.getItem('access_token');

        if (!token) {
            window.location.href = `/access-denied.html?page=sportsbook&message=${encodeURIComponent('Please log in to access this page')}`;
            return;
        }

        const response = await fetch(`${API_URL}/api/admin/page-access/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ page_name: 'sportsbook' })
        });

        if (response.ok) {
            const data = await response.json();
            if (!data.has_access) {
                window.location.href = `/access-denied.html?page=sportsbook&message=${encodeURIComponent(data.message)}`;
            }
        }
    })();
</script>
```

### Admin Interface

Admins can manage page access through the Admin Panel:

1. Navigate to **Admin Panel** → **Page Access** tab
2. View all configured pages and their allowed roles
3. Create new page access rules
4. Edit existing rules (change allowed roles, enable/disable)
5. Delete page access rules

## Setup Instructions

### 1. Apply Database Migration

Run the migration to create the `page_access` table:

```bash
psql -U your_db_user -d your_db_name -f backend/migrations/add_page_access_control.sql
```

Or if using Docker:

```bash
docker exec -i your_postgres_container psql -U postgres -d svidnet_games < backend/migrations/add_page_access_control.sql
```

### 2. Verify Default Data

The migration inserts default page access rules:

- **sportsbook** → Admin only
- **wordle** → Basic, User, Admin
- **wrestling** → User, Admin
- **trivia-game** → Basic, User, Admin
- **movies** → Basic, User, Admin
- **dashboard** → Basic, User, Admin
- **profile** → Basic, User, Admin
- **rankings** → Basic, User, Admin
- **admin** → Admin only

### 3. Update User Roles

Make sure existing users have the appropriate role:

```sql
-- Update a user's role
UPDATE users SET role = 'user' WHERE username = 'someuser';
UPDATE users SET role = 'admin' WHERE username = 'adminuser';
UPDATE users SET role = 'basic' WHERE username = 'basicuser';
```

## Usage Examples

### Example 1: Restrict Sportsbook to Admins Only

1. Go to Admin Panel → Page Access
2. Find "sportsbook" in the list
3. Click "Edit"
4. Uncheck "User" and "Basic", keep only "Admin" checked
5. Click "Update Page"

Result: Only users with the "admin" role can access the sportsbook page.

### Example 2: Allow All Users to Access Wrestling

1. Go to Admin Panel → Page Access
2. Find "wrestling" in the list
3. Click "Edit"
4. Check "Basic", "User", and "Admin"
5. Click "Update Page"

Result: All logged-in users can access wrestling.

### Example 3: Add a New Protected Page

1. Go to Admin Panel → Page Access
2. Click "+ New Page"
3. Fill in:
   - Page Name: `new-game` (matches the HTML file name)
   - Display Name: `New Game`
   - Description: `Our newest game feature`
   - Allowed Roles: Check the roles that should have access
4. Click "Create Page"
5. Add the page access script to your HTML file

## Protected Pages

Currently protected pages:
- ✅ Sportsbook (`sportsbook.html`)
- ✅ Wrestling (`wrestling.html`)
- ✅ Wordle (`wordle.html`)

## Adding Protection to New Pages

To protect a new page:

1. Add the page access check script to the `<head>` section
2. Replace the `page_name` with your page's identifier
3. Create the page access rule in the Admin Panel

## API Environment Variable

The frontend access control uses `http://localhost:8000` for the API URL. For production, update this to use an environment variable or configuration:

```javascript
const API_URL = window.ENV?.API_URL || 'http://localhost:8000';
```

## Security Notes

1. **Fail Open**: If the access check fails (network error, API down), the page allows access for backward compatibility
2. **Client-Side**: This is client-side protection only. Always validate access on the backend for API calls
3. **Token Required**: All checks require a valid JWT token from authentication
4. **Admin Protection**: Admin endpoints additionally check that the user has the "admin" role

## Troubleshooting

### Users Can't Access Pages They Should

1. Check user's role: `SELECT username, role FROM users WHERE username = 'username';`
2. Check page access configuration in Admin Panel
3. Ensure the page is marked as "Active"
4. Verify the user is logged in and has a valid token

### Access Denied Page Not Loading

1. Verify `/access-denied.html` exists in the frontend directory
2. Check browser console for JavaScript errors
3. Ensure API_URL is correct for your environment

### Migration Fails

If the migration fails:
1. Check if the table already exists
2. Verify PostgreSQL version supports ARRAY types
3. Check that the `update_updated_at_column()` function exists (from main schema)

## Future Enhancements

- [ ] Role-based navigation menu (hide links to inaccessible pages)
- [ ] Backend middleware to enforce access control on API routes
- [ ] Audit log for page access changes
- [ ] Temporary access grants (time-limited permissions)
- [ ] Group-based permissions (beyond individual roles)
