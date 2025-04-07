"""
Forms for organization management.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

class InviteMemberForm(FlaskForm):
    """Form for inviting new members to an organization"""
    email = EmailField('Email', validators=[
        DataRequired(), 
        Email(),
        Length(max=120)
    ])
    first_name = StringField('First Name', validators=[
        DataRequired(),
        Length(max=64)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(),
        Length(max=64)
    ])
    submit = SubmitField('Send Invitation')

class OrganizationForm(FlaskForm):
    """Form for creating or editing an organization"""
    name = StringField('Organization Name', validators=[
        DataRequired(),
        Length(min=3, max=100)
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])
    address = TextAreaField('Address', validators=[
        Optional(),
        Length(max=200)
    ])
    phone = StringField('Phone', validators=[
        Optional(),
        Length(max=20)
    ])
    email = EmailField('Business Email', validators=[
        Optional(),
        Email(),
        Length(max=120)
    ])
    size = SelectField('Organization Size', choices=[
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-1000', '201-1000 employees'),
        ('1000+', 'More than 1000 employees')
    ])
    submit = SubmitField('Save Organization')