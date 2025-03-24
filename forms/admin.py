from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, IntegerField, EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Optional, Length


class CreateUserForm(FlaskForm):
    """Form for creating a new user"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    first_name = StringField('First Name', validators=[Optional(), Length(max=64)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=64)])
    role = SelectField('System Role', validators=[DataRequired()], choices=[
        ('individual', 'Individual User'),
        ('organization', 'Organization Owner'),
        ('organization_member', 'Organization Member'),
        ('admin', 'Administrator')
    ])
    account_type = SelectField('Account Type', validators=[DataRequired()], choices=[
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise')
    ])
    tokens_available = IntegerField('Available Tokens', default=50)
    is_active = BooleanField('Active Account', default=True)


class EditUserForm(FlaskForm):
    """Form for editing a user"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[Optional(), Length(max=64)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=64)])
    role = SelectField('System Role', validators=[DataRequired()], choices=[
        ('individual', 'Individual User'),
        ('organization', 'Organization Owner'),
        ('organization_member', 'Organization Member'),
        ('admin', 'Administrator')
    ])
    account_type = SelectField('Account Type', validators=[DataRequired()], choices=[
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise')
    ])
    tokens_available = IntegerField('Available Tokens')
    is_active = BooleanField('Active Account', default=True)
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('new_password', message='Passwords must match')
    ])


class CreateRoleForm(FlaskForm):
    """Form for creating a new role"""
    name = StringField('Role Name', validators=[DataRequired(), Length(min=3, max=50)])
    description = StringField('Description', validators=[Optional(), Length(max=200)])
    is_default = BooleanField('Default Role', default=False)
    is_custom = BooleanField('Custom Role', default=True)


class EditRoleForm(FlaskForm):
    """Form for editing a role"""
    name = StringField('Role Name', validators=[DataRequired(), Length(min=3, max=50)])
    description = StringField('Description', validators=[Optional(), Length(max=200)])
    is_default = BooleanField('Default Role')
    is_custom = BooleanField('Custom Role')


class CreateOrganizationForm(FlaskForm):
    """Form for creating a new organization"""
    name = StringField('Organization Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = StringField('Description', validators=[Optional()])
    address = StringField('Address', validators=[Optional()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = EmailField('Email', validators=[Optional(), Email()])
    size = IntegerField('Organization Size', default=1)
    account_type = SelectField('Account Type', validators=[DataRequired()], choices=[
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise')
    ])
    is_active = BooleanField('Active Account', default=True)


class EditOrganizationForm(FlaskForm):
    """Form for editing an organization"""
    name = StringField('Organization Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = StringField('Description', validators=[Optional()])
    address = StringField('Address', validators=[Optional()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = EmailField('Email', validators=[Optional(), Email()])
    size = IntegerField('Organization Size', default=1)
    account_type = SelectField('Account Type', validators=[DataRequired()], choices=[
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise')
    ])
    is_active = BooleanField('Active Account', default=True)