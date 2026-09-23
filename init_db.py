import os
from werkzeug.security import generate_password_hash
from app import create_app
from models import db, User, Category, Post, Comment, Reaction, Poll, PollOption

def seed_database():
    app = create_app()
    with app.app_context():
        print("Clearing and initializing database schemas...")
        db.drop_all()
        db.create_all()

        # 1. Create Default Categories
        categories_data = [
            ("Confessions", "confessions", "☕"),
            ("Tea", "tea", "👀"),
            ("Funny", "funny", "😂"),
            ("Academics", "academics", "🎓"),
            ("Events", "events", "🎉"),
            ("Opinions", "opinions", "💭"),
            ("Crush", "crush", "❤️"),
            ("Campus", "campus", "🏫")
        ]
        
        categories = {}
        for name, slug, icon in categories_data:
            cat = Category(name=name, slug=slug, icon=icon)
            db.session.add(cat)
            categories[slug] = cat
            
        db.session.commit()

        # 2. Create Default Admin & Demo Users
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'AdminSpill2026!')
        
        admin_user = User(
            username=admin_username,
            email="admin@campus.edu",
            password_hash=generate_password_hash(admin_password),
            is_admin=True
        )
        
        demo_student_1 = User(
            username="student_alex",
            email="alex@campus.edu",
            password_hash=generate_password_hash("password123")
        )
        
        demo_student_2 = User(
            username="student_sam",
            email="sam@campus.edu",
            password_hash=generate_password_hash("password123")
        )

        db.session.add_all([admin_user, demo_student_1, demo_student_2])
        db.session.commit()

        # 3. Create Demo Anonymous Spills
        fictional_spills = [
            ("The library gets louder exactly 10 minutes before an exam.", "academics", demo_student_1.id, 42, 8),
            ("Whoever keeps stealing the good ergonomic chairs in the reading room: I respect the commitment.", "campus", demo_student_2.id, 115, 14),
            ("That 8 AM Monday lecture is a social experiment on human survival.", "academics", demo_student_1.id, 89, 23),
            ("Why does every group project have one person who completely vanishes until the last 2 hours?", "opinions", demo_student_2.id, 210, 45),
            ("To the person who returned my lost airpods at the cafeteria desk: You restored my faith in humanity.", "tea", demo_student_1.id, 67, 3)
        ]

        for content, cat_slug, uid, reactions, comments in fictional_spills:
            post = Post(
                content=content,
                category_id=categories[cat_slug].id,
                user_id=uid,
                reaction_count=reactions,
                comment_count=comments
            )
            db.session.add(post)

        db.session.commit()

        # 4. Create Active Campus Poll
        poll = Poll(question="Canteen Debate: Where is the best chai on campus?")
        db.session.add(poll)
        db.session.commit()

        options = [
            PollOption(poll_id=poll.id, option_text="Main Canteen", votes_count=42),
            PollOption(poll_id=poll.id, option_text="Library Café", votes_count=28),
            PollOption(poll_id=poll.id, option_text="Food Court Stall", votes_count=19),
            PollOption(poll_id=poll.id, option_text="Outside Corner Stall", votes_count=11)
        ]
        db.session.add_all(options)
        db.session.commit()

        print("✓ Database successfully initialized and seeded with campus tea!")

if __name__ == '__main__':
    seed_database()