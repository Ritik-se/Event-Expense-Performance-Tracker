# EventIQ — Enterprise Club & Event Management Platform
### Medi-Caps University | SIH & Final Year Project

---

## 📁 Folder Structure

```
eventiq/
├── app.py                    ← Application factory (entry point)
├── models.py                 ← SQLAlchemy ORM models
├── decorators.py             ← RBAC decorators (@admin_required)
├── seed.py                   ← Database seeder (runs once automatically)
├── requirements.txt
├── blueprints/
│   ├── __init__.py
│   ├── auth.py               ← /login, /logout
│   ├── dashboard.py          ← /dashboard, /add_club, /request_refund, /export_data
│   ├── analytics.py          ← /reports, /api/chart_data
│   ├── comms.py              ← /comms, /api/messages (AJAX)
│   └── profile.py            ← /profile
├── templates/
│   ├── login.html
│   ├── dashboard.html
│   ├── reports.html
│   ├── comms.html
│   ├── profile.html
│   ├── verify.html
│   └── 403.html
└── static/
    ├── style.css
    ├── upi_qr.jpg            ← Replace with your actual UPI QR
    └── qrcodes/              ← Auto-generated ticket QR codes
```

---

## 🚀 Setup & Run

### 1. Create a virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
python app.py
```

Open **http://localhost:5001** in your browser.

### 4. Demo credentials
| Username   | Password  | Role        | Club                  |
|------------|-----------|-------------|---------------------- |
| admin      | admin123  | Admin       | Global View           |
| impetus    | 1234      | Club Head   | Impetus Coding Club   |
| moonstone  | 1234      | Club Head   | Moonstone Cultural    |
| ecell      | 1234      | Club Head   | E-Cell Medi-Caps      |

---

## 🏗️ Architecture Highlights

### Security
- **Flask-Login** for session management
- **Werkzeug** `generate_password_hash` / `check_password_hash` — no plain-text passwords
- **RBAC decorators** — `@admin_required` blocks unauthorized access
- Club Heads can **only** see their own club's data

### Database (Flask-SQLAlchemy)
- **User** → has role (admin/head), belongs to a club
- **Club** → parent entity for events and ticket sales
- **Event** → belongs to Club, created by User
- **TicketSale** → belongs to Event + Club, tracks payment & status
- **Message** → belongs to User (AJAX chat)
- **AuditLog** → tracks all critical actions with timestamps

### Analytics
- **Linear Regression** via NumPy for AI revenue forecasting
- **MoM Cashflow** bar chart
- **Payment Distribution** doughnut chart (UPI/Card/Cash)
- **Club Engagement** polar area / radar chart
- **AI Trend Line** overlaid on actual income data
- `/api/chart_data` — JSON endpoint for async chart refresh

### Comms
- **AJAX polling** every 3 seconds — no full page reload
- New messages appear in real-time without refresh
- `GET /api/messages?after=<id>` — fetches only new messages
- `POST /api/messages` — sends a message via JSON

---

## 🎯 SIH Wow-Factor Features
1. ✅ Audit Log timeline on dashboard
2. ✅ Real-time AJAX chat (Slack-style)
3. ✅ NumPy Linear Regression AI forecast with trend line chart
4. ✅ QR code ticket generation + `/verify/<code>` scanner page
5. ✅ UPI modal with amount display + JS form validation
6. ✅ CSV export per club
7. ✅ Role-Based Access Control (admin vs club head)
8. ✅ Dark / Light mode toggle

---

## 📦 Production Deployment
```bash
gunicorn -w 4 -b 0.0.0.0:5001 "app:app"
```
