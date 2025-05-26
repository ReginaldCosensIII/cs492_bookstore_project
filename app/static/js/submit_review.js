function openModal(bookId) {
  document.getElementById(`reviewModal-${bookId}`).style.display = "block";
}

function closeModal(bookId) {
  document.getElementById(`reviewModal-${bookId}`).style.display = "none";
  document.getElementById(`reviewId-${bookId}`).value = "";
  document.getElementById(`rating-${bookId}`).value = "";
  document.getElementById(`comment-${bookId}`).value = "";
}

function submitReview(event, bookId) {
  event.preventDefault();
  const reviewId = document.getElementById(`reviewId-${bookId}`).value;
  const rating = document.getElementById(`rating-${bookId}`).value;
  const comment = document.getElementById(`comment-${bookId}`).value;

  const method = reviewId ? "PUT" : "POST";
  const url = reviewId ? `/reviews/${reviewId}` : `/reviews`;
  const payload = { book_id: bookId, rating, comment };

  fetch(url, {
    method: method,
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  }).then(() => location.reload());
}

function editReview(reviewId, bookId, rating, comment) {
  openModal(bookId);
  document.getElementById(`reviewId-${bookId}`).value = reviewId;
  document.getElementById(`rating-${bookId}`).value = rating;
  document.getElementById(`comment-${bookId}`).value = comment;
}

function deleteReview(reviewId, bookId) {
  if (confirm("Are you sure you want to delete this review?")) {
    fetch(`/reviews/${reviewId}`, {
      method: "DELETE"
    }).then(() => location.reload());
  }
}
