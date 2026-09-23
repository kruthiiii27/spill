import os
import pytest
from app import create_app
from models import db, User, Post, Category
from moderation.filters import analyze_content

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            cat = Category(name="Confessions", slug="confessions")
            db.session.add(cat)
            db.session.commit()
        yield client

def test_moderation_engine_filters():
    """Verify severe violations (phone numbers, slurs) are blocked."""
    clean_check = analyze_content("This is a totally normal campus confession.")
    assert clean_check["is_safe"] == True
    
    phone_dox_check = analyze_content("Call my ex at 555-123-4567 right now!")
    assert phone_dox_check["is_safe"] == False
    assert phone_dox_check["severity"] == "SEVERE"

def test_server_side_ownership_deletion(client):
    """Ensure User B CANNOT delete User A's post via direct HTTP POST requests."""
    with client.application.app_context():
        user_a = User(username="user_a", password_hash="hash")
        user_b = User(username="user_b", password_hash="hash")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        cat = Category.query.first()
        post = Post(content="User A private spill", user_id=user_a.id, category_id=cat.id)
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    # Simulate User B logged in session
    with client.session_transaction() as sess:
        sess['user_id'] = user_b.id

    # User B attempts to delete User A's post
    response = client.post(f'/posts/{post_id}/delete')
    
    # Must yield HTTP 403 Forbidden
    assert response.status_code == 403
    
    # Verify post remains untouched in DB
    with client.application.app_context():
        check_post = db.session.get(Post, post_id)
        assert check_post.is_deleted == False