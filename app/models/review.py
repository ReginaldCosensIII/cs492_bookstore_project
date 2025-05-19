# app/models/review.py

class Review:
    def __init__(self, id, book_id, user_id, rating, comment, created_at):
        self.id = id
        self.book_id = book_id
        self.user_id = user_id
        self.rating = rating
        self.comment = comment
        self.created_at = created_at

    # Add methods like save(), get_by_book_id(), etc.
