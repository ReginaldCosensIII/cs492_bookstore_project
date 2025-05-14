# CS492 Bookstore Project

A full-stack web application developed using Flask for managing a bookstore. Built as a final project for CS492, the app allows users to browse books, create accounts, place orders, and manage inventory. The backend integrates with a PostgreSQL database and supports user authentication and role-based access.

---

## 🚀 Features

- 📚 Browse available books  
- 🛒 Place and view orders  
- 🔐 User registration and login (with secure password hashing)  
- 👤 Role-based access (Admin and Customer)  
- 📦 Inventory tracking  
- 📄 Order history and summaries  
- 🧾 Custom logging and error handling (planned)

---

## 🛠️ Tech Stack

- **Backend:** Flask, Python  
- **Database:** PostgreSQL  
- **Authentication:** Flask-Login  
- **Deployment:** Render.com  
- **ORM (upcoming):** SQLAlchemy (planned migration)

---

## 📁 File Structure
```
cs492_bookstore_project/
├── app/
│ ├── init.py # App factory, blueprint registration
│ ├── auth/
│ │ ├── init.py
│ │ └── routes.py # Login, logout, registration routes
│ ├── main/
│ │ ├── init.py
│ │ └── routes.py # Homepage, dashboard, etc.
│ ├── models/
│ │ ├── init.py
│ │ ├── user.py # User model and user loader
│ │ ├── book.py # Book model (not created yet)
│ │ ├── order.py # Order model (not created yet)
│ │ └── order_item.py # Order item model (not created yet)
│ ├── services/
│ │ ├── init.py
│ │ ├── auth_service.py # Login logic (not created yet)
│ │ ├── reg_service.py # Registration logic (not created yet)
│ │ ├── book_service.py # Book logic (add, update, fetch)
│ │ └── order_service.py # Order creation, stock tracking (not created yet)
│ ├── templates/
│ │ ├── base.html # Base layout template
│ │ ├── login.html
│ │ ├── register.html
│ │ ├── index.html
│ │ └── customer_dashboard.html
│ └── static/
│ └── css/ # Optional static files
├── render.yaml # Render.com deployment config
├── requirements.txt # Python dependencies
├── main.py # Entry point (calls create_app)
├── README.md # Project overview and usage
└── .gitignore # Files/directories to exclude from Git
```
---

## 🔧 Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/cs492_bookstore_project.git
cd cs492_bookstore_project
2. Install dependencies

pip install -r requirements.txt
3. Set up environment variables
Create a .env file or export these manually:

export FLASK_ENV=development
export SECRET_KEY=your-secret-key
export DATABASE_URL=your-database-url
4. Run the application

python main.py
☁️ Deployment (Render)
This app is configured for one-click deployment on Render.
Just connect the repo and Render will detect render.yaml and auto-deploy the app.

📚 License
This project is for educational purposes. License TBD.

👨‍💻 Authors
Reginald Cosens III,
Dustin Keith,
Edwin Zacarias,
Lawrence Valdivia
Computer Science Students @ CTU
Passionate about building tools, teaching kids to code, and bringing ideas to life with Python & Flask.
