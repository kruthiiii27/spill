from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    is_admin = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='ACTIVE') # ACTIVE, RESTRICTED, SUSPENDED, BANNED
    is_suspended = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    
    warning_count = db.Column(db.Integer, default=0)
    violation_count = db.Column(db.Integer, default=0)
    last_violation_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    reactions = db.relationship('Reaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', backref='user', lazy='dynamic', cascade='all, delete-orphan')


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    icon = db.Column(db.String(10), default='☕')
    
    posts = db.relationship('Post', backref='category', lazy='dynamic')


class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    is_hidden = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_tea_of_the_day = db.Column(db.Boolean, default=False)
    
    # Cached metrics for high performance trending calculations
    reaction_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)

    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    reactions = db.relationship('Reaction', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def trending_score(self):
        """Trending Algorithm: (Reactions*3) + (Comments*2) + Recency Decay"""
        hours_old = (datetime.utcnow() - self.created_at).total_seconds() / 3600.0
        recency_factor = max(0, 100 - (hours_old * 2))
        return (self.reaction_count * 3) + (self.comment_count * 2) + recency_factor


class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Reaction(db.Model):
    __tablename__ = 'reactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    reaction_type = db.Column(db.String(20), default='heart') # heart, laugh, eyes, tea
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'post_id', 'reaction_type', name='unique_user_post_reaction'),
    )


class Bookmark(db.Model):
    __tablename__ = 'bookmarks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'post_id', name='unique_user_bookmark'),
    )


class Poll(db.Model):
    __tablename__ = 'polls'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    options = db.relationship('PollOption', backref='poll', lazy='dynamic', cascade='all, delete-orphan')


class PollOption(db.Model):
    __tablename__ = 'poll_options'
    
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('polls.id', ondelete='CASCADE'), nullable=False)
    option_text = db.Column(db.String(100), nullable=False)
    votes_count = db.Column(db.Integer, default=0)

    votes = db.relationship('PollVote', backref='option', lazy='dynamic', cascade='all, delete-orphan')


class PollVote(db.Model):
    __tablename__ = 'poll_votes'
    
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('polls.id', ondelete='CASCADE'), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey('poll_options.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'poll_id', name='unique_user_poll_vote'),
    )


class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='PENDING') # PENDING, REVIEWED, DISMISSED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_report'),
    )


class ModerationAction(db.Model):
    __tablename__ = 'moderation_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False) # WARNING, RESTRICTED, SUSPENDED, BANNED, CONTENT_REMOVED
    reason = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)