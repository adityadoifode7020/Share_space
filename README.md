# ShareSpace — Resource Sharing Platform

ShareSpace is a web-based resource-sharing platform that helps students, colleges, and organizations share underused equipment and spaces. Users can list available resources, request bookings, manage reservations, and report incidents.

## Features

- **User Authentication:** Register and log in with different user roles.
- **Resource Listings:** Add, view, and manage shared equipment and spaces.
- **Search and Filter:** Find resources by keyword and category.
- **Booking Management:** Request, approve, or reject reservations.
- **Waitlist Support:** Handle booking conflicts and overlapping reservations.
- **Check-In and Check-Out:** Record resource condition before and after use.
- **Incident Reporting:** Report damage or other resource-related issues.
- **Admin Dashboard:** Manage users, verify accounts, and resolve incidents.
- **Audit Logs:** Track important platform activities.

## Technologies Used

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript

## Project Structure

```text
ShareSpace/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── resource_form.html
│   ├── resource_detail.html
│   └── admin.html
└── static/
    ├── style.css
    └── app.js
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd ShareSpace
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your repository URL.

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

### 5. Open the website

Visit:

http://127.0.0.1:5000

## Demo Accounts

If your project includes the default demo accounts, use these credentials:

| Role | Email | Password |
|---|---|---|
| Owner | owner@sharespace.demo | owner123 |
| Student | student@sharespace.demo | student123 |
| Manager | manager@sharespace.demo | manager123 |
| Admin | admin@sharespace.demo | admin123 |

Change or disable demo credentials before deploying publicly.

## How It Works

1. Users register and log in.
2. Resource owners list equipment or spaces available for sharing.
3. Students browse resources and request booking slots.
4. Owners or managers review booking requests.
5. Users check in and check out while recording resource condition.
6. Incidents can be reported and reviewed by administrators.

## Future Enhancements

- PostgreSQL integration for persistent online storage.
- Cloud-based image uploads for resource listings.
- Email and booking notifications.
- Calendar integration.
- QR-code-based check-in and check-out.
- Online deployment and improved identity verification.

## Security Note

This project is a prototype. Before public deployment, implement secure password hashing, production configuration, appropriate authorization checks, and persistent database storage. Never commit secret keys, passwords, or private database files to GitHub.

## License

This project is available for educational and hackathon use. Add a license file if you intend to distribute it under specific reuse terms.

---

**ShareSpace — Unlocking Underused Equipment and Spaces.**
