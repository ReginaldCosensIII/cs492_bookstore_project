// app/static/js/cart_handler.js

/**
 * Adds an item to the cart via AJAX.
 * Called from product listings (home.html, customer.html) and book detail modals.
 * @param {string} bookId - The ID of the book to add.
 * @param {HTMLElement} [buttonElement] - Optional: The button that triggered the action (for context, though not used for messages now).
 */
async function addToCart(bookId, buttonElement) {
    const stringBookId = String(bookId);
    const quantityInput = document.getElementById(`quantity-${stringBookId}`); 
    
    if (!quantityInput) {
        console.error(`Quantity input not found for book ID ${stringBookId}`);
        alert("System error: Could not find quantity input for this book.");
        return;
    }
    const requestedQuantity = parseInt(quantityInput.value, 10);

    if (isNaN(requestedQuantity) || requestedQuantity < 1) {
        alert("Please enter a valid quantity (at least 1).");
        quantityInput.value = "1"; // Reset if invalid input
        return;
    }

    try {
        const response = await fetch('/cart/add_to_cart', { 
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                // 'X-CSRFToken': window.csrfToken // Example for CSRF
            },
            body: JSON.stringify({ book_id: stringBookId, quantity: requestedQuantity })
        });
        
        const data = await response.json(); // Attempt to parse JSON response

        // Always display the message from the backend if available
        if (data.message) { 
            alert(data.message); 
        } else if (data.error) { // Fallback to error field if message isn't there
            alert(data.error);
        } else if (!response.ok) { // For other HTTP errors not producing expected JSON
             alert(`Failed to add item to cart (Status: ${response.status}). Please try again.`);
        }

        if (response.ok) { 
            // If the server processed the request (200 OK), reset the input field to 1
            // for the next potential "add" action from the product card/modal.
            // The alert from data.message has already informed the user of capping or success.
            quantityInput.value = "1"; 
            
            // Update navbar cart count if the data is available
            if (typeof updateNavbarCartCount === "function" && data.cart_item_count !== undefined) {
                updateNavbarCartCount(data.cart_item_count, data.cart_total_str);
            }
        }
        // If response.ok was false, an alert with an error should have already been shown.
        // The quantity input will retain the user's attempted value in that case.

    } catch (error) { 
        console.error('Error adding to cart:', error);
        let fallbackMessage = 'An error occurred while adding to cart.';
        if (typeof window.currentUserId === 'undefined' || window.currentUserId === null) {
            fallbackMessage += ' You may need to log in first.';
        }
        alert(fallbackMessage); 
    }
}

/**
 * Updates the quantity of an item in the cart via AJAX (for cart.html).
 * @param {string} bookId - The ID of the book.
 * @param {number} newQuantity - The new quantity.
 * @param {HTMLElement} [buttonElement] - Optional: The button that triggered the action.
 */
async function updateCartItemQuantityOnPage(bookId, newQuantity, buttonElement) {
    console.log(`Updating quantity on cart page for book ${bookId} to ${newQuantity}`);
    try {
        const response = await fetch("/cart/update", { // Ensure this route is defined in cart/routes.py
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                // 'X-CSRFToken': window.csrfToken 
            },
            body: JSON.stringify({ book_id: bookId, quantity: newQuantity })
        });
        const result = await response.json();

        if (response.ok && result.success) {
            console.log(result.message); // Log success
            if (result.message && (result.message.toLowerCase().includes("adjusted") || result.message.toLowerCase().includes("capped"))) {
                alert(result.message); // Inform user specifically about stock adjustments
            }
            // Reloading the page is the simplest way to reflect all changes (item total, grand total, item removal if qty is 0)
            window.location.reload(); 
        } else {
            alert(result.error || "Failed to update quantity.");
        }
    } catch (error) {
        console.error("Error updating cart quantity:", error);
        alert("An error occurred while updating quantity.");
    }
}

/**
 * Removes an item from the cart via AJAX (for cart.html).
 * @param {string} bookId - The ID of the book to remove.
 * @param {HTMLElement} [buttonElement] - Optional: The button that triggered the action.
 */
async function removeCartItemFromPage(bookId, buttonElement) {
    console.log(`Removing book ${bookId} from cart page`);
    try {
        const response = await fetch("/cart/remove", { // Ensure this route is defined
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                // 'X-CSRFToken': window.csrfToken 
            },
            body: JSON.stringify({ book_id: bookId })
        });
        const result = await response.json();
        if (response.ok && result.success) {
            console.log(result.message); // Log success
            // alert(result.message); // Optional: Could alert success here before reload
            window.location.reload(); // Simplest way to update cart display
        } else {
            alert(result.error || "Failed to remove item.");
        }
    } catch (error) {
        console.error("Error removing item from cart:", error);
        alert("An error occurred while removing item.");
    }
}

// Event listeners specifically for the cart.html page
document.addEventListener('DOMContentLoaded', function () {
    // Check if we are on the cart page by looking for a specific element ID
    const cartPageIdentifier = document.getElementById('cart-page-main-container-js');
    if (cartPageIdentifier) {
        const cartItemsContainer = document.getElementById('cart-items-container-js');

        if (cartItemsContainer) {
            cartItemsContainer.addEventListener('click', function (event) {
                const target = event.target;
                let bookId;
                let buttonElement; // The button clicked, for context

                // Handle Update Quantity Button
                if (target.classList.contains('update-quantity-btn-js') || target.closest('.update-quantity-btn-js')) {
                    event.preventDefault();
                    buttonElement = target.classList.contains('update-quantity-btn-js') ? target : target.closest('.update-quantity-btn-js');
                    bookId = buttonElement.dataset.bookId;
                    const quantityInput = document.getElementById(`cart-quantity-${bookId}`);
                    if (!quantityInput) return;
                    const newQuantity = parseInt(quantityInput.value, 10);

                    if (isNaN(newQuantity) || newQuantity < 0) { // Allow 0 for removal by update
                        alert("Quantity must be a non-negative number.");
                        return;
                    }
                    updateCartItemQuantityOnPage(bookId, newQuantity, buttonElement);
                }

                // Handle Remove Item Button
                if (target.classList.contains('remove-from-cart-btn-js') || target.closest('.remove-from-cart-btn-js')) {
                    event.preventDefault();
                    buttonElement = target.classList.contains('remove-from-cart-btn-js') ? target : target.closest('.remove-from-cart-btn-js');
                    bookId = buttonElement.dataset.bookId;
                    if (confirm('Are you sure you want to remove this item from your cart?')) {
                        removeCartItemFromPage(bookId, buttonElement);
                    }
                }
            });
        }
        // if (typeof checkIfCartIsEmptyOnPage === "function") checkIfCartIsEmptyOnPage(); // Definition needed
    }
});