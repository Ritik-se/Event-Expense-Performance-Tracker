import random
import datetime
from datetime import timedelta
from models import db, User, Club, Event, TicketSale, Message, AuditLog

def seed_database():
    """Seeds the database with realistic Medi-Caps University data."""

    if User.query.count() > 0:
        return  # Already seeded

    # ── Clubs ──────────────────────────────────────────────────────────────
    club_names = ['Impetus Coding Club', 'Moonstone Cultural', 'E-Cell Medi-Caps']
    clubs = []
    for cname in club_names:
        c = Club(name=cname)
        db.session.add(c)
        clubs.append(cname)

    db.session.flush()

    # ── Users ──────────────────────────────────────────────────────────────
    users_data = [
        ('admin',     'admin123',  'admin', 'All',                  'Director of Student Affairs',
         'https://cdn-icons-png.flaticon.com/512/2202/2202112.png',  'admin@medicaps.ac.in'),
        ('impetus',   '1234',      'head',  'Impetus Coding Club',  'President',
         'https://cdn-icons-png.flaticon.com/512/4248/4248744.png',  'impetus@medicaps.ac.in'),
        ('moonstone', '1234',      'head',  'Moonstone Cultural',   'Secretary',
         'https://cdn-icons-png.flaticon.com/512/4345/4345428.png',  'moonstone@medicaps.ac.in'),
        ('ecell',     '1234',      'head',  'E-Cell Medi-Caps',     'Lead',
         'https://cdn-icons-png.flaticon.com/512/3079/3079165.png',  'ecell@medicaps.ac.in'),
    ]

    user_objs = {}
    for uname, pwd, role, club, position, pic, email in users_data:
        u = User(username=uname, role=role, club=club, position=position,
                 profile_pic=pic, email=email)
        u.set_password(pwd)
        db.session.add(u)
        user_objs[uname] = u

    db.session.flush()

    # ── Events ─────────────────────────────────────────────────────────────
    event_templates = [
        "Hackathon", "E-Summit", "RoboWars", "Cultural Night",
        "Pitch Deck", "Code Sprint", "Startup Fair", "Open Mic",
        "Design Sprint", "AI Workshop"
    ]
    payments = ['UPI', 'Card', 'Cash']
    event_objs = []

    for i in range(40):
        club  = random.choice(club_names)
        etype = 'Income' if random.random() > 0.3 else 'Expense'
        amount = round(random.uniform(1500, 25000), 2)
        days_ago = random.randint(0, 180)
        date_val = datetime.date.today() - timedelta(days=days_ago)
        t_id  = f"EVT-{datetime.datetime.now().timestamp():.0f}-{i}"
        ename = f"{random.choice(event_templates)} {random.choice(['1.0','2.0','3.0','Phase '+str(i%4+1)])}"

        ev = Event(
            name=ename, type=etype, amount=amount,
            tickets_sold=random.randint(50, 300),
            participation=random.randint(20, 250),
            club=club,
            added_by_id=user_objs['admin'].id,
            date=date_val,
            payment_method=random.choice(payments),
            ticket_id=t_id,
        )
        db.session.add(ev)
        event_objs.append(ev)

    db.session.flush()

    # ── Ticket Sales ───────────────────────────────────────────────────────
    for i in range(60):
        ev    = random.choice(event_objs)
        club  = ev.club
        status = random.choices(
            ['Active', 'Refund Requested', 'Refunded'], weights=[80, 10, 10]
        )[0]
        t_code = f"TKT-{random.randint(100000, 999999)}"
        buyer  = f"Medi-Caps Student {random.randint(1, 500)}"
        days_ago = random.randint(0, 30)
        p_date = datetime.datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))

        ts = TicketSale(
            event_id=ev.id,
            event_name=ev.name,
            buyer_name=buyer,
            payment_method=random.choice(payments),
            amount=round(random.uniform(300, 2000), 2),
            ticket_code=t_code,
            status=status,
            club=club,
            purchase_date=p_date,
        )
        db.session.add(ts)

    # ── Messages ───────────────────────────────────────────────────────────
    mock_chats = [
        ('admin',     'admin', 'Welcome to the Medi-Caps EventIQ portal. Budget tracking is now strictly enforced.'),
        ('impetus',   'head',  'Noted! We are preparing the budget for the upcoming Hackathon.'),
        ('moonstone', 'head',  'Admin, please check the pending refund requests for the Cultural Night.'),
        ('ecell',     'head',  'E-Summit registration is live! Expecting 200+ attendees.'),
        ('admin',     'admin', 'All club heads: monthly finance reports are due by Friday.'),
    ]
    for uname, role, text in mock_chats:
        m = Message(
            sender_id=user_objs[uname].id,
            sender=uname,
            role=role,
            text=text,
            timestamp=datetime.datetime.now() - timedelta(hours=random.randint(1, 48))
        )
        db.session.add(m)

    # ── Audit Logs ─────────────────────────────────────────────────────────
    audit_actions = [
        ('admin',     'System initialised and database seeded with Medi-Caps data', 'success'),
        ('impetus',   'Launched new event: Hackathon 3.0',                          'info'),
        ('moonstone', 'Submitted refund request for ticket TKT-MOCK-00012',         'refund'),
        ('admin',     'Approved refund for ticket TKT-MOCK-00012',                  'success'),
        ('ecell',     'New ticket sale: E-Summit — Medi-Caps Student 241',          'info'),
        ('admin',     'Added new club head account: drama_club',                    'info'),
    ]
    for uname, action, cat in audit_actions:
        log = AuditLog(
            user_id=user_objs[uname].id,
            action=action,
            category=cat,
            timestamp=datetime.datetime.now() - timedelta(hours=random.randint(1, 72))
        )
        db.session.add(log)

    db.session.commit()
    print("[EventIQ] ✅ Database seeded successfully.")
