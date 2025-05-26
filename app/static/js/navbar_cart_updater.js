// app/static/js/navbar_cart_updater.js

/**
 * Updates the cart item count (and optionally total) in the navbar.
 * @param {number} itemCount - The total number of items (sum of quantities) in the cart.
 * @param {string} [cartTotalString] - The cart total, formatted as a string (e.g., "123.45"). Optional.
 */
function updateNavbarCartCount(itemCount, cartTotalString) {
    const cartCountBadgeNavbar = document.getElementById('cart-item-count-badge-navbar');
    // const cartTotalNavbar = document.getElementById('cart-total-navbar'); // Optional: if you want to show total in navbar

    if (cartCountBadgeNavbar) {
        const count = parseInt(itemCount, 10) || 0;
        if (count > 0) {
            cartCountBadgeNavbar.textContent = count;
            cartCountBadgeNavbar.style.display = 'inline-block'; 
        } else {
            cartCountBadgeNavbar.textContent = '0';
            cartCountBadgeNavbar.style.display = 'none'; 
        }
    }

    // if (cartTotalNavbar && cartTotalString !== undefined) {
    //     cartTotalNavbar.textContent = `$${cartTotalString}`;
    // }
    
    // console.log(`Navbar cart status updated: Items = ${itemCount}, Total = $${cartTotalString || 'N/A'}`);
}

// Optional: Fetch initial cart summary on page load to set the navbar count
// This requires a backend endpoint like GET /cart/summary_api
document.addEventListener('DOMContentLoaded', async () => {
    if (document.getElementById('cart-item-count-badge-navbar')) { 
        try {
            // This assumes you will create an API endpoint at /cart/summary
            // that returns { success: true, item_count: X, cart_total_str: "Y.YY" }
            // For now, this is commented out as the endpoint doesn't exist yet.
            // Cart count will update upon add/remove/update actions.
            /*
            const response = await fetch("{{ url_for('cart.cart_summary_api_route') }}"); // Needs this route
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.item_count !== undefined) {
                    updateNavbarCartCount(data.item_count, data.cart_total_str);
                } else {
                     updateNavbarCartCount(0); // Default to 0 if no data
                }
            } else {
                 updateNavbarCartCount(0); // Default to 0 on error
            }
            */
           // For now, let's just ensure it's hidden if no items initially from server-side (if possible)
           // Or make an explicit call if you have a way to get initial cart count on page load.
           // The cart count will primarily update via JS calls after cart actions.
           // To get initial count, one way is to embed it in a data attribute in base.html from session.
           const initialCartDataElement = document.getElementById('initial-cart-data');
           if (initialCartDataElement) {
               const initialItemCount = parseInt(initialCartDataElement.dataset.itemCount, 10) || 0;
               const initialCartTotal = initialCartDataElement.dataset.cartTotal || "0.00";
               updateNavbarCartCount(initialItemCount, initialCartTotal);
           }


        } catch (error) {
            console.warn("Could not fetch initial cart summary for navbar:", error);
            updateNavbarCartCount(0); // Default to 0 on error
        }
    }
});