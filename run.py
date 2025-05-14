# run.py

from app import create_app
from flask import redirect
import os

# Create the Flask app using the factory pattern
app = create_app()

# Redirect root URL to /auth/
@app.route('/')
def root():
    return redirect('/auth/')

if __name__ == '__main__':
    # Safety check: Warn if DATABASE_URL is not set
    if not os.environ.get("DATABASE_URL"):
        print("⚠️ Warning: DATABASE_URL is not set! Set it before running the app.")
    
    # Run the development server
    app.run(debug=True)
