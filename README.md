# PANN POS System

A modern Point of Sale system built with Vue.js frontend and Django backend, using MongoDB Atlas for cloud data storage with local fallback capability.

## Tech Stack

- **Frontend**: Vue.js with Vite
- **Backend**: Django REST Framework  
- **Database**: MongoDB Atlas (cloud) with local MongoDB fallback
- **Deployment**: Netlify (frontend) + Render (backend)

## Project Structure

```
Ramyeon-Backoffice/
├── src/
│   ├── pages/             # Top-level route views
│   ├── components/        # Reusable UI components (by domain)
│   ├── composables/       # Business logic (api/, auth/, data/, ui/)
│   ├── services/          # Axios API layer (one file per domain)
│   ├── layouts/           # AppLayout, MainLayout, Sidebar
│   ├── router/            # Route definitions + auth guard
│   ├── assets/styles/     # Global CSS, color tokens
│   └── main.js
├── public/
├── index.html
├── vite.config.js
├── netlify.toml
├── .env                   # Not committed — copy from .env.example
├── .env.example
└── package.json
```

## Prerequisites

Before setting up the project, ensure you have:

- **Node.js** (v16 or higher) - [Download here](https://nodejs.org/)
- **Python** (v3.9 or higher) - [Download here](https://python.org/)
- **Git** - [Download here](https://git-scm.com/)
- **MongoDB Community Edition** (optional, for local fallback) - [Download here](https://www.mongodb.com/try/download/community)
- **MongoDB Atlas Account** (recommended for cloud database) - [Sign up here](https://www.mongodb.com/cloud/atlas)

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/PANN_POS.git
cd PANN_POS
```

### 2. Backend Setup (Django)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# For Windows Command Prompt:
venv\Scripts\activate
# For Git Bash/Mac/Linux:
source venv/bin/activate

# Install Python dependencies from requirements file
pip install -r requirements.txt

# Alternative: Manual installation
# pip install django djangorestframework django-cors-headers pymongo djongo python-decouple pytz dnspython bcrypt cryptography python-jose passlib motor
```

### 3. Database Access Setup

#### Option A: Join Existing MongoDB Atlas Project (Recommended)

The project uses a shared MongoDB Atlas database. You'll need to join the existing Atlas project:

1. **Create MongoDB Atlas Account**
   - Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
   - Sign up with your email

2. **Get Project Invitation**
   - Ask the project lead to invite you to the Atlas organization
   - Check your email for the invitation link
   - Accept the invitation

3. **Access Shared Database**
   - Once added, you'll see the `PANN` project in your Atlas dashboard
   - Navigate to the `pos_system` database
   - You can view data, monitor performance, and manage collections

4. **Get Connection String**
   - Go to "Database" → "Connect" → "Connect your application"
   - Choose Python driver
   - Copy the connection string (ask team lead for credentials)

#### Option B: Local MongoDB (Development Fallback)

```bash
# Install MongoDB Community Edition
# MongoDB should automatically start as a Windows service after installation
# The app will connect to mongodb://localhost:27017 by default
```

## Team Setup Instructions

### For Project Lead (Database Owner)

To add new team members to the MongoDB Atlas project:

1. **Go to Atlas Dashboard**
   - Navigate to your MongoDB Atlas account
   - Select the PANN project

2. **Invite Team Members**
   - Go to "Project Settings" → "Access Manager"
   - Click "Invite To Project"
   - Enter team member's email address
   - Set role to "Project Data Access Admin" or "Project Owner"
   - Click "Invite"

3. **Share Connection Details**
   - Provide the connection string format
   - Share database username/password securely

### For Team Members

1. **Accept Atlas Invitation**
   - Check email for MongoDB Atlas invitation
   - Create account and accept invitation
   - You'll have access to the shared database

### 4. Environment Configuration

After joining the Atlas project and getting credentials, create a `.env` file in the `backend/` directory:

```env
# Cloud Database (MongoDB Atlas) - Primary
# Ask the team lead for the actual connection string. Never commit real credentials.
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.qumhbyz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
MONGODB_DATABASE=pos_system

# Local Database (Optional Fallback)
MONGODB_LOCAL_URI=mongodb://localhost:27017
MONGODB_LOCAL_DATABASE=pos_system

# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production
```

**Important**: Ask your team lead for the actual `MONGODB_URI` connection string.

### 5. Start Backend Server

```bash
# Make sure virtual environment is activated
# Run Django development server
python manage.py runserver
```

The Django backend will be running at http://localhost:8000

### 6. Frontend Setup (Vue.js)

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Install additional packages (if not already included)
npm install axios

# Create frontend environment file
# Create .env file in frontend/ directory:
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env

# Start the development server
npm run dev
```

The Vue frontend will be running at http://localhost:5173

## Database Connection Features

### Automatic Fallback System
The system automatically tries to connect to MongoDB Atlas first, then falls back to local MongoDB if cloud connection fails:

1. **Cloud-first**: Attempts MongoDB Atlas connection
2. **Local fallback**: Uses local MongoDB if Atlas is unavailable
3. **Error handling**: Graceful degradation with proper error messages

### Testing Database Connection

```bash
# Test in Django shell
python manage.py shell

# Test database connection
from app.database import db_manager
db = db_manager.get_database()
print(f"Connected to: {db.name}")
print(f"Collections: {db.list_collection_names()}")
```

## Testing the Setup

### 1. Backend API Test
- Visit: http://localhost:8000/api/v1/health/
- You should see: `{"status": "healthy", "database": "connected"}`

### 2. Frontend-Backend Connection
- Go to: http://localhost:5173
- Test login functionality
- Check browser console for any errors

### 3. Database Operations
```bash
# Test user creation via API
POST http://localhost:8000/api/v1/users/
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "password123",
  "role": "admin"
}
```

## Development Workflow

### Daily Development Setup

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python manage.py runserver

# Terminal 2: Frontend  
cd frontend
npm run dev
```

### Common Commands

#### Backend Commands
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install new package and update requirements
pip install package-name
pip freeze > requirements.txt

# Database operations
python manage.py shell     # Interactive shell
python manage.py migrate   # Apply migrations

# Create superuser
python manage.py createsuperuser
```

#### Frontend Commands
```bash
# Install new package
npm install package-name

# Build for production
npm run build

# Run linting
npm run lint
```

## API Endpoints

- **GET** `/api/v1/health/` - Check API and database status
- **POST** `/api/v1/auth/login/` - User authentication
- **GET** `/api/v1/users/` - List users
- **POST** `/api/v1/users/` - Create new user
- **GET** `/api/v1/customers/` - List customers
- **GET** `/admin/` - Django admin interface

## Production Deployment

### Environment Variables for Production

```env
# Production .env
DEBUG=False
MONGODB_URI=your_atlas_production_connection_string
MONGODB_DATABASE=pos_system_production
SECRET_KEY=your_super_secure_secret_key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```bash
# Check environment variables
python -c "from decouple import config; print(config('MONGODB_URI'))"

# Test direct connection
python manage.py shell
>>> import pymongo
>>> client = pymongo.MongoClient("your_connection_string")
>>> client.admin.command('ping')
```

#### 2. Module Not Found Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### 3. CORS Errors
- Check that `corsheaders` is installed and configured
- Verify frontend URL is in `CORS_ALLOWED_ORIGINS` in settings

#### 4. MongoDB Atlas Connection Issues
- Verify IP whitelist includes `0.0.0.0/0`
- Check username/password in connection string
- Ensure database user has proper permissions

#### 5. Port Already in Use
```bash
# Change port
python manage.py runserver 8001

# Or kill existing process (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

#### 6. Frontend Issues
```bash
# Clear npm cache and reinstall
npm cache clean --force
rm -rf node_modules
npm install
```

### Database Truth Value Error
If you encounter: `"Database objects do not implement truth value testing"`
- Update `database.py` to use `if self.current_db is not None:` instead of `if self.current_db:`

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Add feature"`
4. Push to branch: `git push origin feature-name`
5. Create Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section above
- Verify all environment variables are set correctly
