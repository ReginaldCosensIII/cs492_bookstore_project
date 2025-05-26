// app/static/js/review_handler.js

async function openBookReviewModal(bookId) {
    const stringBookId = String(bookId); 
    const modalElement = document.getElementById(`bookModal${stringBookId}`);
    if (!modalElement) {
      console.error("Modal element not found for bookId:", stringBookId);
      return;
    }
    const reviewFormMessageDiv = document.getElementById(`reviewFormMessage${stringBookId}`);
    if (reviewFormMessageDiv) reviewFormMessageDiv.innerHTML = ''; 
    const reviewForm = document.getElementById(`reviewForm${stringBookId}`);
    if (reviewForm) {
        reviewForm.reset();
        const submitButton = reviewForm.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.textContent = 'Submit Review';
            submitButton.classList.remove('btn-warning');
            submitButton.classList.add('btn-success');
        }
    }
    const bootstrapModalInstance = bootstrap.Modal.getOrCreateInstance(modalElement);
    bootstrapModalInstance.show();
    await loadReviewsForModal(stringBookId); 
}

async function loadReviewsForModal(stringBookId) {
    const reviewsContainer = document.getElementById(`reviewsContainer${stringBookId}`);
    if (!reviewsContainer) {
        console.error("Review container `reviewsContainer" + stringBookId + "` not found.");
        return; 
    }
    reviewsContainer.innerHTML = '<p class="text-muted p-3">Loading reviews...</p>';
    try {
        const response = await fetch(`/api/reviews/${stringBookId}`);
        if (!response.ok) {
            let errorMsg = `HTTP error! Status: ${response.status}`;
            try {
                const errData = await response.json();
                errorMsg += `, Details: ${errData.details || errData.error || JSON.stringify(errData)}`;
            } catch (jsonError) {
                try { const errText = await response.text(); errorMsg += `, Response: ${errText}`; }
                catch (textError) { /* ignore */ }
            }
            throw new Error(errorMsg);
        }
        const reviews = await response.json();
        let reviewsHtml = '';
        if (reviews && reviews.length > 0) {
            reviewsHtml = '<div class="list-group list-group-flush">';
            const currentAuthUserId = (typeof window.currentUserId !== 'undefined' && window.currentUserId !== null) ? parseInt(window.currentUserId, 10) : null;

            reviews.forEach(review => {
                let reviewerName = `User ${review.user_id}`; 
                if (review.user && review.user.first_name) { 
                    reviewerName = review.user.first_name;
                    if (review.user.last_name) reviewerName += ` ${review.user.last_name}`;
                } else if (review.user_first_name) { 
                   reviewerName = review.user_first_name;
                   if (review.user_last_name) reviewerName += ` ${review.user_last_name}`;
                }
                
                let ratingStars = '';
                for (let i = 1; i <= 5; i++) {
                    // Using actual Unicode characters for stars
                    ratingStars += `<span class="text-${i <= review.rating ? 'warning' : 'secondary'}">${i <= review.rating ? '★' : '☆'}</span>`;
                }
                let reviewDate = 'Date unavailable';
                if (review.created_at) {
                    try { 
                        reviewDate = new Date(review.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
                    } catch(e) { console.warn("Could not parse review date:", review.created_at, e); }
                }
                const safeReviewerName = reviewerName.replace(/(<([^>]+)>)/gi, "");
                const originalComment = (review.comment || '');
                const safeComment = originalComment.replace(/(<([^>]+)>)/gi, ""); // For initiateEditReview
                
                let commentHtml;
                if (originalComment.trim() === "") {
                    commentHtml = `<p class="mb-1 fst-italic text-muted"><em>No comment left.</em></p>`;
                } else {
                    // Display sanitized comment (already escaped by backend if it was user input)
                    // The .replace above is a client-side basic strip for safety with innerHTML
                    commentHtml = `<p class="mb-1 fst-italic">"${safeComment}"</p>`;
                }

                let actionButtons = '';
                if (review.is_owner) { 
                    // Pass the raw (but client-side "safe" for JS template literal) comment to initiateEditReview
                    const commentForEdit = originalComment.replace(/`/g, '\\`').replace(/'/g, "\\'");

                    actionButtons = `
                        <div class="mt-2 review-actions">
                            <button class="btn btn-outline-secondary btn-sm me-2" 
                                    onclick="initiateEditReview('${stringBookId}', '${review.id}', ${review.rating}, \`${commentForEdit}\`)">Edit</button>
                            <button class="btn btn-outline-danger btn-sm" 
                                    onclick="handleDeleteReview('${stringBookId}', '${review.id}')">Delete</button>
                        </div>`;
                }
                reviewsHtml += `
                    <div class="list-group-item py-3" id="review-item-${review.id}">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${safeReviewerName}</h6>
                            <small class="text-muted">${reviewDate}</small>
                        </div>
                        <p class="mb-1"><strong>Rating:</strong> ${ratingStars} (${review.rating}/5)</p>
                        ${commentHtml}
                        ${actionButtons}
                    </div>`;
            });
            reviewsHtml += '</div>';
        } else {
            reviewsHtml = '<p class="p-3">No reviews yet for this book. Be the first!</p>';
        }
        reviewsContainer.innerHTML = reviewsHtml; // This should render Unicode stars correctly
    } catch (error) {
        console.error('Failed to fetch or process reviews for bookId ' + stringBookId + ':', error);
        const safeErrorMessage = (error.message || 'Error loading reviews.').replace(/(<([^>]+)>)/gi, "");
        reviewsContainer.innerHTML = `<p class="text-danger p-3">Could not load reviews. ${safeErrorMessage}</p>`;
    }
}

// ... (handleReviewSubmit, initiateEditReview, handleDeleteReview functions from response #47,
//      they use alert() for feedback and messageDiv for form validation, which is fine for now)
async function handleReviewSubmit(bookId, event) {
    event.preventDefault(); 
    const stringBookId = String(bookId);
    const form = document.getElementById(`reviewForm${stringBookId}`);
    const ratingInput = document.getElementById(`rating${stringBookId}`);
    const messageDiv = document.getElementById(`reviewFormMessage${stringBookId}`); 
    const submitButton = form.querySelector('button[type="submit"]');

    if (messageDiv) messageDiv.innerHTML = ''; 
    if (!ratingInput || !ratingInput.value) { 
        if (messageDiv) messageDiv.innerHTML = '<p class="text-danger">Please select a rating.</p>';
        return;
    }
    const formData = new FormData(form);
    formData.append('book_id', stringBookId); 

    try {
        if (messageDiv) messageDiv.innerHTML = '<p class="text-info small">Submitting...</p>';
        const response = await fetch('/api/reviews', { method: 'POST', body: formData });
        const result = await response.json();

        if (response.ok && result.success) {
            alert(result.message || "Review submitted successfully!"); 
            if(form) {
                form.reset();
                if (submitButton) { 
                    submitButton.textContent = 'Submit Review';
                    submitButton.classList.remove('btn-warning');
                    submitButton.classList.add('btn-success');
                }
            }
            if(messageDiv) messageDiv.innerHTML = ''; 
            await loadReviewsForModal(stringBookId); 
        } else {
            const safeResultMessage = (result.message || result.error || 'Failed to submit review.').replace(/(<([^>]+)>)/gi, "");
            alert(safeResultMessage); 
            if(messageDiv) messageDiv.innerHTML = `<p class="text-danger">${safeResultMessage}</p>`;
        }
    } catch (error) {
        console.error('Error submitting review:', error);
        alert('An unexpected error occurred submitting your review.'); 
        if (messageDiv) messageDiv.innerHTML = '<p class="text-danger">An unexpected error occurred.</p>';
    }
}

function initiateEditReview(bookId, reviewId, rating, comment) {
    const stringBookId = String(bookId);
    const form = document.getElementById(`reviewForm${stringBookId}`);
    const ratingInput = document.getElementById(`rating${stringBookId}`);
    const commentInput = document.getElementById(`comment${stringBookId}`);
    const messageDiv = document.getElementById(`reviewFormMessage${stringBookId}`);
    const submitButton = form.querySelector('button[type="submit"]');
    
    if (!form || !ratingInput || !commentInput || !submitButton) {
        console.error("Review form elements not found for editing, bookId:", stringBookId);
        return;
    }
    if(messageDiv) messageDiv.innerHTML = '';

    ratingInput.value = rating;
    commentInput.value = comment; 
    submitButton.textContent = 'Update Review';
    submitButton.classList.remove('btn-success');
    submitButton.classList.add('btn-warning');
    
    if(messageDiv) messageDiv.innerHTML = "<p class='text-info small'><em>Editing your review. Make changes and click 'Update Review'.</em></p>";
    commentInput.focus();
}

/**
 * Handles the deletion of a review via AJAX.
 * This function is called from both review modals and the profile page.
 * @param {string} bookIdForModalRefresh - The ID of the book (used to refresh its reviews list if in a modal context).
 * @param {string} reviewId - The ID of the review to delete.
 * @param {function} [successCallback] - Optional callback function to execute after successful API deletion and alert.
 */
async function handleDeleteReview(bookIdForModalRefresh, reviewId, successCallback) {
    const stringBookIdForModalRefresh = String(bookIdForModalRefresh);
    const stringReviewId = String(reviewId);

    // Step 1: Confirm with the user
    if (!confirm('Are you sure you want to permanently delete this review? This action cannot be undone.')) {
        console.log("Review deletion cancelled by user.");
        return; // User clicked Cancel, do nothing further
    }

    // Step 2: User confirmed, proceed with API call
    try {
        const response = await fetch(`/api/reviews/${stringReviewId}`, { 
            method: 'DELETE'
            // headers: { 'X-CSRFToken': window.csrfToken } // Example for CSRF
        });
        
        const result = await response.json(); 

        if (response.ok && result.success) {
            alert(result.message || "Review deleted successfully."); // Inform user
            
            // Step 3a: If this delete was initiated from a book modal, refresh its reviews
            if (document.getElementById(`reviewsContainer${stringBookIdForModalRefresh}`)) {
                await loadReviewsForModal(stringBookIdForModalRefresh);
            }
            
            // Step 3b: If a specific successCallback is provided (e.g., for profile page DOM removal), execute it
            if (typeof successCallback === 'function') {
                successCallback(stringReviewId); // Pass reviewId to callback
            }
        } else {
            // API call was made, but backend indicated failure or error
            alert(result.error || result.message || "Failed to delete review. You may not be authorized or the review no longer exists.");
        }
    } catch (error) { // Network errors or if response.json() fails
        console.error('Error deleting review:', error);
        alert("An error occurred while attempting to delete the review. Please try again.");
    }
}