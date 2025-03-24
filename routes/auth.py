import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from models import User
from app import db

logger = logging.getLogger(__name__)

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return render_template('auth/login.html')
        
        # Login user
        login_user(user, remember=remember, duration=timedelta(days=14) if remember else None)
        logger.info(f"User {user.username} logged in")
        
        # Redirect to requested page or dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Validate form data
        if not username or not email or not password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        
        # First user is admin
        if User.query.count() == 0:
            user.role = 'admin'
        
        db.session.add(user)
        try:
            db.session.commit()
            logger.info(f"User {username} registered")
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering user: {str(e)}")
            flash('Error registering user. Please try again.', 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile route"""
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')
        
        # Update profile information
        if first_name:
            current_user.first_name = first_name
        if last_name:
            current_user.last_name = last_name
        
        # Update password if provided
        if current_password and new_password and confirm_new_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect', 'error')
                return render_template('auth/profile.html')
            
            if new_password != confirm_new_password:
                flash('New passwords do not match', 'error')
                return render_template('auth/profile.html')
            
            current_user.set_password(new_password)
            flash('Password updated successfully', 'success')
        
        # Save changes
        try:
            db.session.commit()
            flash('Profile updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating profile: {str(e)}")
            flash('Error updating profile. Please try again.', 'error')
    
    return render_template('auth/profile.html')
