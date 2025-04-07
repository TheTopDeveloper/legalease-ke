#!/usr/bin/env python3
"""
Script to create database tables.
"""
from app import app, db
from models import Event

def main():
    """Create database tables"""
    with app.app_context():
        db.create_all()
        print('Database tables created')

if __name__ == '__main__':
    main()