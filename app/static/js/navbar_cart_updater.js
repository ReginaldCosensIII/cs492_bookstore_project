// app/static/js/navbar_cart_updater.js

/**
 * Updates the cart item count badge in the navbar.
 * Hides the badge if the item count is zero or less.
 *
 * @param {number} itemCount - The total number of items (sum of quantities) in the cart.
 * @param {string} [cartTotalString] - Optional: The cart total, formatted as a string (e.g., "123.45").
 * This parameter is available but not currently used to display total in navbar.
 */
function updateNavbarCartCount(itemCount, cartTotalString) {
    const cartCountBadgeNavbar = document.getElementById('cart-item-count-badge-navbar');

    if (cartCountBadgeNavbar) {
        const count = parseInt(itemCount, 10); // Ensure it's treated as a number

        if (isNaN(count) || count <= 0) {
            cartCountBadgeNavbar.textContent = '0';
            cartCountBadgeNavbar.style.display = 'none'; // Hide badge if cart is empty or count is invalid
        } else {
            cartCountBadgeNavbar.textContent = count;
            cartCountBadgeNavbar.style.display = 'inline-block'; // Show badge with the count
        }
        // console.log(`Navbar cart count badge updated to: ${count > 0 ? count : '0 (hidden)'}`);
    } else {
        // console.warn("Navbar cart count badge element ('cart-item-count-badge-navbar') not found.");
    }

    // Optional: If you had an element to display the cart total in the navbar:
    // const cartTotalDisplayNavbar = document.getElementById('navbar-cart-total-display');
    // if (cartTotalDisplayNavbar && cartTotalString !== undefined) {
    //     cartTotalDisplayNavbar.textContent = `$${cartTotalString}`;
    // }
}

/**
 * Initializes the navbar cart count on page load.
 * It attempts to read initial cart data passed from the server via a global
 * JavaScript variable `window.initialCartData` (expected to be set in base.html).
 */
document.addEventListener('DOMContentLoaded', () => {
    const cartBadgeElement = document.getElementById('cart-item-count-badge-navbar');
    
    if (cartBadgeElement) { // Only proceed if the badge element exists on the page
        // Check for the global variable set by base.html
        if (typeof window.initialCartData !== 'undefined' && 
            window.initialCartData.hasOwnProperty('itemCount')) {
            
            // console.log("DOMContentLoaded: Initializing navbar cart count from window.initialCartData:", window.initialCartData);
            updateNavbarCartCount(window.initialCartData.itemCount); 
            // If you also pass cartTotalStr in window.initialCartData, you can use it:
            // updateNavbarCartCount(window.initialCartData.itemCount, window.initialCartData.cartTotalStr);
        } else {
            // Fallback if initialCartData or itemCount is not set.
            // This ensures the badge is correctly hidden or shows 0 if no specific initial data.
            // console.log("DOMContentLoaded: window.initialCartData.itemCount not found, defaulting navbar cart count to 0.");
            updateNavbarCartCount(0); 
        }
    } else {
        // console.warn("DOMContentLoaded: Navbar cart badge element ('cart-item-count-badge-navbar') not found. Cannot initialize count.");
    }
});