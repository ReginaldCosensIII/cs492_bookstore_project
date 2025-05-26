// app/static/js/utils.js

/**
 * Displays a temporary message near a given reference element, typically a button or input.
 * Creates a dedicated div for the message if one doesn't exist.
 * THIS FUNCTION IS CURRENTLY UNUSED by cart_handler.js and review_handler.js as per user request.
 * It is kept for potential future re-implementation of on-page messages.
 * @param {HTMLElement} referenceElement - The element near which to display the message.
 * @param {string} message - The message text.
 * @param {string} type - 'success', 'error', or 'info' (maps to Bootstrap text colors).
 * @param {number} duration - How long the message should stay, in milliseconds.
 */
function displayActionMessage(referenceElement, message, type = 'info', duration = 3500) {
    if (!referenceElement) {
        // console.warn("displayActionMessage: referenceElement is null or undefined.");
        // alert(`${type.toUpperCase()}: ${message}`); // Fallback if uncommented
        return;
    }
    let messageContainerId = `action-message-for-${referenceElement.id || 'element'}-${Math.random().toString(36).substring(2,7)}`;
    let messageContainer = document.getElementById(messageContainerId);
    if (!messageContainer) {
        let parentGroup = referenceElement.closest('.input-group, .d-flex.justify-content-between.align-items-center, form');
        let targetInsertLocation = parentGroup || referenceElement.parentNode;
        messageContainer = document.createElement('div');
        messageContainer.id = messageContainerId;
        if (referenceElement.isSameNode(messagePlacementTarget) || !messagePlacementTarget.contains(referenceElement)){
             referenceElement.parentNode.insertBefore(messageContainer, referenceElement.nextSibling);
        } else {
             messagePlacementTarget.appendChild(messageContainer);
        }
    }
    const cleanMessage = message.replace(/(<([^>]+)>)/gi, "");
    messageContainer.textContent = cleanMessage;
    messageContainer.className = `action-message small mt-2 text-center alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} py-1`;
    messageContainer.style.display = 'block';
    messageContainer.setAttribute('role', 'alert');
    if (messageContainer.timerId) {
        clearTimeout(messageContainer.timerId);
    }
    messageContainer.timerId = setTimeout(() => {
        if (messageContainer) {
            messageContainer.style.display = 'none';
            messageContainer.textContent = ''; 
        }
    }, duration);
}

// function getCsrfToken() { ... } // Keep if you have it
console.log("utils.js loaded (displayActionMessage is defined but currently unused by handlers)");