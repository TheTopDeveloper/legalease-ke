"""
Routes for organization management.
These routes handle organization-level operations including member management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_required
from sqlalchemy import select
from werkzeug.security import generate_password_hash
import secrets
import string

from app import db
from models import User, Organization
from forms.organization import InviteMemberForm
from utils.permissions import has_permission, Permissions
from utils.email import send_invitation_email

# Create blueprint
organization = Blueprint('organization', __name__)

@organization.route('/organization/overview')
@login_required
def overview():
    """View organization overview"""
    # Check if user has active organization
    if not current_user.active_organization:
        flash("You need to select an active organization first.", "warning")
        return redirect(url_for('dashboard.index'))
    
    # Get the active organization
    organization = current_user.active_organization
    
    # Get organization statistics
    case_count = len(organization.cases) if hasattr(organization, 'cases') else 0
    member_count = len(organization.members)
    
    return render_template(
        'organization/overview.html',
        organization=organization,
        case_count=case_count,
        member_count=member_count
    )

@organization.route('/organization/invite', methods=['GET', 'POST'])
@login_required
def invite_member():
    """Invite a new member to the organization"""
    # Check if user has active organization
    if not current_user.active_organization:
        flash("You need to select an active organization first.", "warning")
        return redirect(url_for('dashboard.index'))
    
    # Check permissions
    if not (current_user.is_organization_owner() or current_user.is_admin() or 
            current_user.has_permission(Permissions.CREATE_USER)):
        flash("You don't have permission to invite members.", "danger")
        return redirect(url_for('organization.overview'))
    
    # Get the active organization
    organization = current_user.active_organization
    
    # Create form
    form = InviteMemberForm()
    
    if form.validate_on_submit():
        # Check if email already exists
        existing_user = db.session.scalar(
            select(User).where(User.email == form.email.data)
        )
        
        if existing_user:
            # If user exists, add them to the organization
            if existing_user in organization.members:
                flash(f"{existing_user.email} is already a member of this organization.", "info")
                return redirect(url_for('org_roles.index'))
            
            # Add user to organization
            organization.members.append(existing_user)
            db.session.commit()
            
            flash(f"Existing user {existing_user.email} added to the organization.", "success")
            return redirect(url_for('org_roles.index'))
        
        # Create a new user
        # Generate a secure random password
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        new_user = User(
            email=form.email.data,
            username=form.email.data.split('@')[0],  # Use part of email as username
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role='organization_member',  # Set as organization member
            active_organization_id=organization.id
        )
        new_user.set_password(password)
        
        # Add to database and organization
        db.session.add(new_user)
        organization.members.append(new_user)
        db.session.commit()
        
        # Send invitation email with credentials
        try:
            send_invitation_email(
                new_user.email, 
                password, 
                organization.name, 
                current_user.get_full_name()
            )
            flash(f"Invitation sent to {new_user.email}.", "success")
        except Exception as e:
            flash(f"User created but invitation email could not be sent: {str(e)}", "warning")
        
        return redirect(url_for('org_roles.index'))
    
    return render_template(
        'organization/invite_member.html',
        organization=organization,
        form=form
    )

@organization.route('/organization/set-active/<int:org_id>')
@login_required
def set_active(org_id):
    """Set active organization for current user"""
    # Find the organization
    organization = db.session.get(Organization, org_id)
    
    if not organization:
        flash("Organization not found.", "danger")
        return redirect(url_for('dashboard.index'))
    
    # Check if user is a member of this organization
    user_orgs = current_user.organizations.all()
    if organization not in user_orgs:
        flash("You are not a member of this organization.", "danger")
        return redirect(url_for('dashboard.index'))
    
    # Set active organization
    current_user.active_organization_id = organization.id
    db.session.commit()
    
    flash(f"Active organization changed to {organization.name}.", "success")
    
    # Redirect to the referring page or dashboard
    next_page = request.args.get('next') or url_for('dashboard.index')
    return redirect(next_page)