# 📚 CS492 Bookstore Project - v2.0 ✨

Welcome to the BookNook (v2.0)! This is a full-stack web application developed using Flask for an online bookstore. Originally a final project for CS492, this version represents a significant refactor focused on a robust, modular, and maintainable codebase, implementing core e-commerce functionalities and preparing for future expansion.

The application allows users to browse an extensive collection of books, create and manage user accounts, build a shopping cart (as guests or registered users), place orders, and manage book reviews. The backend leverages a PostgreSQL database and features user authentication with role-based access considerations for future admin and employee functionalities.

---

## 🚀 Key Features & Enhancements in v2.0

This refactor introduced a more professional structure and several key features:

* **📖 Book Browse & Details:**
    * View all available books on the home page.
    * Dynamic book detail modals showing descriptions, price, and AJAX-loaded reviews.
* **🛒 Shopping Cart Functionality:**
    * **Guest & User Carts:** Session-based cart accessible to both anonymous guests and logged-in users.
    * Add items to cart with quantity selection.
    * View and manage cart contents.
    * Update item quantities or remove items directly from the cart page.
    * **Stock Capping:** Automatic adjustment of cart quantities based on available stock, with clear user feedback via pop-up messages.
    * Dynamic update of cart item count in the navbar.
* **🛍️ Order Processing & Checkout:**
    * **Guest Checkout:** Allows users to place orders without creating an account, requiring only an email and shipping details.
    * **Authenticated User Checkout:** Pre-fills shipping details for logged-in users.
    * Transactional order creation ensuring data integrity (order details, item details, stock deduction).
    * Storage of order history for registered users and essential details for guest orders (including `guest_email`, `unit_price_at_purchase`).
    * Order confirmation page display for both guests and logged-in users.
* **👤 User Accounts & Profile:**
    * Secure user registration with input validation and password hashing (Werkzeug).
    * User login and logout functionality (Flask-Login).
    * **Profile Page:**
        * Displays order history for logged-in users.
        * Allows users to view their submitted reviews (with stubs for edit/delete functionality from profile).
        * Placeholders for future "Edit Personal Info" and "Payment Methods".
* **🌟 Book Reviews:**
    * Authenticated users can submit, update, and delete their *own* reviews (rating and comment).
    * AJAX-driven review display, submission, and deletion within book detail modals.
    * Ownership checks ensure users can only modify their own reviews.
    * `is_owner` flag provided by the API for frontend to conditionally show edit/delete buttons.
* **🏗️ Application Architecture & Quality (v2.0 Refactor):**
    * **Modular Design:** Flask Blueprints for `main`, `auth`, `cart`, `reviews` (API), and `order` concerns.
    * **Service Layer:** Encapsulates business logic, separating it from route handlers.
    * **Model Layer:** Clear data representation classes.
    * **Centralized Configuration:** Environment-based settings via `config.py` and `.env` files.
    * **Professional Logging:** Application-wide custom logging (`app/logger.py`) with console and file output, replacing `print()` statements.
    * **Custom Exception Handling:** Structured error management using custom exceptions (`app/services/exceptions.py`) and global error handlers.
    * **Utility Functions:** Centralized utilities for input sanitization and normalization (`app/utils.py`).
    * **Professional Code Documentation:** Consistent docstrings (summary, Args, Returns, Raises) and inline comments.
    * **Improved Frontend Layout:** New header (with SVG logo, slogan) and footer in `base.html`.
    * **JavaScript Consolidation:** Interactive logic moved to external static JS files.
* **🔒 Security Foundations:**
    * Input sanitization for form data and user-generated content.
    * Output encoding (via Jinja2 autoescaping).
    * Parameterized SQL queries (via `psycopg2`).
    * Password hashing.

---

## 🛠️ Tech Stack

* **Backend:** Python (3.10+), Flask
* **Database:** PostgreSQL
* **Templating:** Jinja2
* **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5
* **Authentication:** Flask-Login
* **Password Hashing:** Werkzeug
* **WSGI Server (Production):** Gunicorn
* **Environment Management:** `python-dotenv` (for local development)
* **Deployment:** Configured for Render.com

---

## 📁 Updated Project Structure (v2.0)

```
cs492_bookstore_project/
├── app/                           # Main Flask application package
│   ├── init.py                # Application factory (create_app), blueprint registration, error handlers
│   ├── auth/                      # Authentication blueprint (login, register, logout)
│   │   ├── init.py            # Defines auth_bp
│   │   └── routes.py
│   ├── cart/                      # Shopping cart blueprint
│   │   ├── init.py            # Defines cart_bp
│   │   └── routes.py
│   ├── main/                      # Main application routes (home, profile, dashboards)
│   │   ├── init.py            # Defines main_bp
│   │   └── routes.py
│   ├── models/                    # Database models (User, Book, Order, etc.)
│   │   ├── init.py            # Exposes model classes
│   │   ├── db.py                  # Database connection setup (get_db_connection)
│   │   ├── book.py
│   │   ├── order.py
│   │   ├── order_item.py
│   │   ├── review.py
│   │   └── user.py
│   │   └── (admin.py, customer.py, employee.py - stubs for future use)
│   ├── order/                     # Order display blueprint (confirmation, details)
│   │   ├── init.py            # Defines order_bp
│   │   └── routes.py
│   ├── reviews/                   # Reviews API blueprint
│   │   ├── init.py            # Defines reviews_api_bp
│   │   └── routes.py
│   ├── services/                  # Service layer (business logic)
│   │   ├── init.py            # Package marker
│   │   ├── auth_service.py
│   │   ├── book_service.py
│   │   ├── exceptions.py          # Custom exception classes
│   │   ├── order_service.py
│   │   ├── reg_service.py
│   │   └── review_service.py
│   ├── static/                    # Static assets (CSS, JavaScript, images)
│   │   ├── css/
│   │   │   └── styles.css
│   │   ├── js/
│   │   │   ├── cart_handler.js
│   │   │   ├── navbar_cart_updater.js
│   │   │   ├── review_handler.js  # Consolidated review AJAX logic
│   │   │   └── utils.js           # Shared JS utilities
│   │   └── images/                # For logos, etc.
│   │       └── booknook_logo.svg  # Example logo
│   ├── templates/                 # Jinja2 HTML templates
│   │   ├── errors/                # Error page templates (400, 401, 403, 404, 500, general_error.html)
│   │   ├── base.html              # Base layout template with header & footer
│   │   ├── home.html
│   │   ├── customer.html          # Customer dashboard (similar to home for book Browse)
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── cart.html
│   │   ├── checkout.html
│   │   ├── order_confirmation.html
│   │   ├── order_details.html
│   │   ├── profile.html
│   │   ├── admin.html             # Placeholder admin dashboard
│   │   └── employee.html          # Placeholder employee dashboard
│   └── utils.py                   # Core utility functions (sanitization, normalization)
├── instance/                      # Instance-specific files (e.g., logs) - GITIGNORED
│   └── logs/
│       └── bookstore_app.log      # Application log file
├── .env                           # Environment variables for local development (GITIGNORED)
├── .flaskenv                      # Optional: For Flask CLI environment variables (e.g., FLASK_APP, FLASK_ENV)
├── .gitignore                     # Specifies intentionally untracked files Git should ignore
├── config.py                      # Application configuration classes (Config, DevelopmentConfig, etc.)
├── requirements.txt               # Python package dependencies for pip
├── render.yaml                    # Deployment configuration for Render.com
├── build.sh                       # Build script for Render.com
├── run.py                         # Application entry point / development server runner
└── README.md                      # This file: Project overview, setup, and usage
```
## 🔧 Setup and Installation (Local Development - v2.0)

1.  **Prerequisites:**
    * Python (version 3.10 or newer recommended)
    * `pip` (Python package installer)
    * PostgreSQL server installed and running.
    * Git for version control.

2.  **Clone the Repository:**
    ```bash
    git clone <your_repository_url>
    cd cs492-bookstore-project
    ```

3.  **Create and Activate a Virtual Environment:**
    * It's highly recommended to use a virtual environment to manage project dependencies.
    ```bash
    python -m venv venv
    ```
    * Activate the environment:
        * Windows: `venv\Scripts\activate`
        * macOS/Linux: `source venv/bin/activate`

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Database Setup:**
    * Ensure your PostgreSQL server is running.
    * Create a new database (e.g., `bookstore_v2_dev`).
    * Create a database user with necessary privileges for this database.
    * **Important:** Manually create the tables in your PostgreSQL database using SQL DDL scripts according to the finalized schema for v2.0. This includes:
        * `users` (with `role`, address fields, `created_at`)
        * `books` (with `price` as `NUMERIC(10,2)`, `stock_quantity`, `image_url`, `description`, `created_at`, `updated_at`)
        * `reviews` (with `user_id`, `book_id`, `rating`, `comment`, `created_at`, and now `updated_at` - *you deferred this, so ensure your schema matches your code for now*)
        * `orders` (with `user_id` nullable, `guest_email` nullable, `order_date`, `total_amount` as `NUMERIC(10,2)`, `status`, all shipping columns, `updated_at`)
        * `order_items` (with `order_id`, `book_id`, `quantity`, `unit_price_at_purchase` as `NUMERIC(10,2)`)
        * Ensure primary keys, foreign keys, `NOT NULL` constraints, and default values (like `CURRENT_TIMESTAMP` for `updated_at` columns and `DEFAULT 'Pending Payment'` for `orders.status`) are correctly set up. Add indexes for frequently queried columns.

6.  **Environment Variables:**
    * Create a `.env` file in the project root (`cs492_bookstore_project/.env`).
    * Add the following, replacing placeholder values:
        ```env
        FLASK_SECRET_KEY='your_actual_strong_random_secret_key_here_PLEASE_GENERATE_ONE'
        DATABASE_URL='postgresql://your_db_user:your_db_password@your_db_host:your_db_port/your_database_name'
        FLASK_CONFIG='development'  # Or 'production', 'testing'
        
        # Optional: Define log levels for different environments if not using defaults from config.py
        # LOG_LEVEL_DEV='DEBUG'
        # LOG_LEVEL_PROD='INFO'
        ```
    * **Security:** Generate a new, strong, random string for `FLASK_SECRET_KEY`.
    * Update `DATABASE_URL` with your actual PostgreSQL connection details.

7.  **Run the Application (Local Development Server):**
    ```bash
    python run.py
    ```
    The application should be accessible at `http://127.0.0.1:5000/` (or the host/port configured in `run.py` or via environment variables). Check the terminal for logs, including any startup errors. Log files will be in the `instance/logs/` directory.

---

## ☁️ Deployment (Render.com)

This application is configured for deployment on Render.com using the `render.yaml` blueprint and `build.sh` script.

1.  **Push Code:** Ensure all your code, including `render.yaml` and `build.sh`, is pushed to your GitHub repository.
2.  **Render Setup:**
    * Create a new "Web Service" on Render.com and connect it to your GitHub repository.
    * Render should automatically detect `render.yaml` ("Blueprint instance").
3.  **Environment Variables on Render:**
    * In your Render.com service settings, navigate to "Environment".
    * Create an **Environment Group** (e.g., `bookstore-credentials-prod`).
    * Add your production `DATABASE_URL` (this will be the connection string for your Render PostgreSQL instance) and a unique, strong `FLASK_SECRET_KEY` to this group.
    * In your `render.yaml`, the `fromGroup: bookstore-credentials` line will pull these in.
    * `FLASK_CONFIG` is set to `production` in `render.yaml`.
4.  **Build & Deploy:** Render will use `build.sh` to install dependencies and then `gunicorn run:app` (from `render.yaml`) to start the application. Monitor the build and deploy logs on Render for any issues.
5.  The health check path at `/health` will be used by Render to verify service health.

---

## 📚 License

This project is developed for educational purposes as part of the CS492 curriculum. License details are to be determined (e.g., MIT, GNU GPLv3, or proprietary for educational use).

---

## 👨‍💻 Authors

* Reginald Cosens III
* Dustin Keith
* Edwin Zacarias
* Lawrence Valdivia

*Computer Science Students @ Colorado Technical University*
*Passionate about building robust software and bringing innovative ideas to life!*

---