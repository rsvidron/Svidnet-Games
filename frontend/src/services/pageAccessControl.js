/**
 * Page Access Control Service
 * Client-side middleware to check if users have access to pages
 */

const API_URL = 'http://localhost:8000';

/**
 * Check if the current user has access to a specific page
 * @param {string} pageName - The name of the page to check access for
 * @returns {Promise<{hasAccess: boolean, message: string}>}
 */
export async function checkPageAccess(pageName) {
    try {
        const token = localStorage.getItem('access_token');

        if (!token) {
            return {
                hasAccess: false,
                message: 'Please log in to access this page'
            };
        }

        const response = await fetch(`${API_URL}/api/admin/page-access/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ page_name: pageName })
        });

        if (!response.ok) {
            if (response.status === 401) {
                return {
                    hasAccess: false,
                    message: 'Session expired. Please log in again.'
                };
            }
            throw new Error('Failed to check page access');
        }

        const data = await response.json();
        return {
            hasAccess: data.has_access,
            message: data.message
        };
    } catch (error) {
        console.error('Error checking page access:', error);
        // Fail open - allow access if the check fails (backward compatibility)
        return {
            hasAccess: true,
            message: 'Access check unavailable, allowing access'
        };
    }
}

/**
 * Redirect to access denied page if user doesn't have access
 * @param {string} pageName - The name of the page to check
 */
export async function requirePageAccess(pageName) {
    const result = await checkPageAccess(pageName);

    if (!result.hasAccess) {
        // Redirect to access denied page
        window.location.href = `/access-denied.html?page=${encodeURIComponent(pageName)}&message=${encodeURIComponent(result.message)}`;
        return false;
    }

    return true;
}

/**
 * Add page access script to HTML pages
 * Usage: Add this script tag to the top of each protected page:
 * <script src="/src/services/pageAccessControl.js" type="module"></script>
 * <script type="module">
 *   import { requirePageAccess } from '/src/services/pageAccessControl.js';
 *   await requirePageAccess('sportsbook'); // Replace with actual page name
 * </script>
 */
