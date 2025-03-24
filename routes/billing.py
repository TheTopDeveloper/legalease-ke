from datetime import datetime
import json

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

from app import db
from models import User, Subscription, TokenPackage, Payment, TokenUsage
from utils.pesapal import payment_gateway

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/subscriptions')
@login_required
def subscriptions():
    """View available subscription plans"""
    # Get all active subscription plans
    individual_plans = Subscription.query.filter_by(is_active=True, is_organization=False).all()
    organization_plans = Subscription.query.filter_by(is_active=True, is_organization=True).all()
    
    # Get user's current subscription
    current_plan = None
    if current_user.account_type != 'free':
        current_plan = Subscription.query.filter_by(name=current_user.account_type).first()
    
    return render_template(
        'billing/subscriptions.html',
        individual_plans=individual_plans,
        organization_plans=organization_plans,
        current_plan=current_plan
    )

@billing_bp.route('/tokens')
@login_required
def tokens():
    """View available token packages"""
    # Get all active token packages
    token_packages = TokenPackage.query.filter_by(is_active=True).all()
    
    # Get user's token usage history
    token_usage = TokenUsage.query.filter_by(user_id=current_user.id).order_by(desc(TokenUsage.created_at)).limit(10).all()
    
    return render_template(
        'billing/tokens.html',
        token_packages=token_packages,
        token_usage=token_usage,
        tokens_available=current_user.tokens_available
    )

@billing_bp.route('/subscribe/<int:subscription_id>', methods=['POST'])
@login_required
def subscribe(subscription_id):
    """Subscribe to a plan"""
    # Get the subscription
    subscription = Subscription.query.get_or_404(subscription_id)
    
    if not subscription.is_active:
        flash('This subscription plan is not currently available.', 'danger')
        return redirect(url_for('billing.subscriptions'))
    
    # Check if it's an organization plan and user role is appropriate
    if subscription.is_organization and current_user.role != 'organization':
        flash('You need an organization account for this subscription.', 'danger')
        return redirect(url_for('billing.subscriptions'))
    
    # Store selected subscription in session for later
    payment = Payment(
        user_id=current_user.id,
        amount=subscription.price,
        payment_type='subscription',
        subscription_id=subscription.id,
    )
    db.session.add(payment)
    db.session.commit()
    
    try:
        # Prepare the callback URL for after payment
        callback_url = url_for('billing.payment_callback', _external=True)
        
        # Submit order to payment gateway
        payment_url = payment_gateway.submit_order(
            user=current_user,
            amount=subscription.price,
            description=f"{subscription.name.capitalize()} subscription - {subscription.duration_days} days",
            payment_type="subscription",
            redirect_url=callback_url
        )
        
        # Store payment ID in session
        session['payment_id'] = payment.id
        
        # Redirect to payment page
        return redirect(payment_url)
        
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'danger')
        return redirect(url_for('billing.subscriptions'))

@billing_bp.route('/buy-tokens/<int:package_id>', methods=['POST'])
@login_required
def buy_tokens(package_id):
    """Buy a token package"""
    # Get the token package
    token_package = TokenPackage.query.get_or_404(package_id)
    
    if not token_package.is_active:
        flash('This token package is not currently available.', 'danger')
        return redirect(url_for('billing.tokens'))
    
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        amount=token_package.price,
        payment_type='tokens',
        token_package_id=token_package.id,
    )
    db.session.add(payment)
    db.session.commit()
    
    try:
        # Prepare the callback URL for after payment
        callback_url = url_for('billing.payment_callback', _external=True)
        
        # Submit order to payment gateway
        payment_url = payment_gateway.submit_order(
            user=current_user,
            amount=token_package.price,
            description=f"{token_package.name} Token Package - {token_package.token_count} tokens",
            payment_type="tokens",
            redirect_url=callback_url
        )
        
        # Store payment ID in session
        session['payment_id'] = payment.id
        
        # Redirect to payment page
        return redirect(payment_url)
        
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'danger')
        return redirect(url_for('billing.tokens'))

@billing_bp.route('/mock-payment/<transaction_id>')
def mock_payment(transaction_id):
    """Mock payment page for testing without actual payment gateway"""
    payment = Payment.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    # Store payment ID in session for easier access later
    session['payment_id'] = payment.id
    
    # Get related records if available
    subscription = None
    token_package = None
    
    if payment.payment_type == 'subscription' and payment.subscription_id:
        subscription = Subscription.query.get(payment.subscription_id)
    
    if payment.payment_type == 'tokens' and payment.token_package_id:
        token_package = TokenPackage.query.get(payment.token_package_id)
    
    return render_template(
        'billing/mock_payment.html',
        payment=payment,
        subscription=subscription,
        token_package=token_package,
        transaction_id=transaction_id
    )

@billing_bp.route('/process-payment/<transaction_id>', methods=['POST'])
def process_payment(transaction_id):
    """Process the mock payment"""
    payment_status = request.form.get('payment_status', 'cancel')
    
    if payment_status not in ['completed', 'failed']:
        flash('Invalid payment action.', 'danger')
        return redirect(url_for('billing.payment_status'))
    
    # Process the payment with our mock system
    success = payment_gateway.process_payment(transaction_id, status=payment_status)
    
    if success and payment_status == 'completed':
        flash('Payment completed successfully!', 'success')
        # Clear payment ID from session
        if 'payment_id' in session:
            session.pop('payment_id')
        
        # Redirect based on payment type
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        if payment:
            if payment.payment_type == 'subscription':
                return redirect(url_for('billing.subscriptions'))
            elif payment.payment_type == 'tokens':
                return redirect(url_for('billing.tokens'))
        
        # Default redirect
        return redirect(url_for('dashboard.index'))
    
    elif success and payment_status == 'failed':
        flash('Payment failed.', 'danger')
    
    else: 
        flash('Payment processing error.', 'danger')
    
    return redirect(url_for('billing.payment_status'))

@billing_bp.route('/payment/callback')
def payment_callback():
    """Handle payment callback from payment gateway"""
    # For compatibility with future payment gateway implementation
    # Just redirect to dashboard for now
    flash('Payment completed!', 'success')
    return redirect(url_for('dashboard.index'))

@billing_bp.route('/payment/status')
@login_required
def payment_status():
    """Check payment status"""
    # Check for transaction ID in query string first
    transaction_id = request.args.get('transaction_id')
    if transaction_id:
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        if payment:
            session['payment_id'] = payment.id
    
    # Otherwise, use payment ID from session
    payment_id = session.get('payment_id')
    
    if not payment_id:
        flash('No active payment found.', 'warning')
        return redirect(url_for('dashboard.index'))
    
    payment = Payment.query.get(payment_id)
    
    if not payment:
        flash('Payment not found.', 'danger')
        if 'payment_id' in session:
            session.pop('payment_id')
        return redirect(url_for('dashboard.index'))
    
    # Get related subscription or token package
    subscription = None
    token_package = None
    
    if payment.subscription_id:
        subscription = Subscription.query.get(payment.subscription_id)
    
    if payment.token_package_id:
        token_package = TokenPackage.query.get(payment.token_package_id)
    
    return render_template('billing/payment_status.html', 
                           payment=payment,
                           subscription=subscription,
                           token_package=token_package)

@billing_bp.route('/billing/history')
@login_required
def payment_history():
    """View payment history"""
    page = request.args.get('page', 1, type=int)
    payment_type = request.args.get('payment_type')
    status = request.args.get('status')
    
    # Filter query based on parameters
    query = Payment.query.filter_by(user_id=current_user.id)
    
    if payment_type:
        query = query.filter_by(payment_type=payment_type)
    
    if status:
        query = query.filter_by(status=status)
    
    # Paginate results
    per_page = 10
    pagination = query.order_by(desc(Payment.created_at)).paginate(page=page, per_page=per_page)
    payments = pagination.items
    
    # Calculate payment statistics
    total_spent = db.session.query(db.func.sum(Payment.amount)).filter_by(
        user_id=current_user.id, status='completed').scalar() or 0
    
    # Get total tokens purchased
    token_payments = Payment.query.filter_by(
        user_id=current_user.id, payment_type='tokens', status='completed'
    ).join(TokenPackage).all()
    
    total_tokens = sum(p.token_package.token_count for p in token_payments if p.token_package)
    
    # Count subscription renewals
    subscription_count = Payment.query.filter_by(
        user_id=current_user.id, payment_type='subscription', status='completed'
    ).count()
    
    payment_stats = {
        'total_spent': total_spent,
        'total_tokens': total_tokens,
        'subscription_count': subscription_count
    }
    
    return render_template('billing/history.html', 
                           payments=payments, 
                           pagination=pagination,
                           payment_stats=payment_stats)

@billing_bp.route('/ipn/notification', methods=['GET', 'POST'])
def ipn_notification():
    """Handle IPN notifications - placeholder for future payment gateway integration"""
    # This is a placeholder endpoint that will be implemented when integrating with a real payment gateway
    return jsonify({'success': True, 'message': 'IPN notification handler placeholder'})


# Admin routes for managing subscriptions and token packages

@billing_bp.route('/admin/subscriptions')
@login_required
def admin_subscriptions():
    """Admin view for managing subscription plans"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    subscriptions = Subscription.query.all()
    return render_template('admin/subscriptions.html', subscriptions=subscriptions)

@billing_bp.route('/admin/subscriptions/create', methods=['GET', 'POST'])
@login_required
def create_subscription():
    """Create a new subscription plan"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Create a new subscription plan
        is_org = request.form.get('is_organization') == 'true'
        is_active = request.form.get('is_active') == 'true'
        
        subscription = Subscription(
            name=request.form.get('name'),
            price=float(request.form.get('price')),
            duration_days=int(request.form.get('duration_days')),
            max_cases=int(request.form.get('max_cases')),
            tokens_included=int(request.form.get('tokens_included')),
            is_organization=is_org,
            max_users=int(request.form.get('max_users', 1)),
            is_active=is_active,
            features=request.form.get('features')
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        flash('Subscription plan created successfully.', 'success')
        return redirect(url_for('billing.admin_subscriptions'))
    
    return render_template('admin/create_subscription.html')

@billing_bp.route('/admin/subscriptions/edit/<int:subscription_id>', methods=['GET', 'POST'])
@login_required
def edit_subscription(subscription_id):
    """Edit a subscription plan"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    subscription = Subscription.query.get_or_404(subscription_id)
    
    if request.method == 'POST':
        # Update subscription plan
        is_org = request.form.get('is_organization') == 'true'
        is_active = request.form.get('is_active') == 'true'
        
        subscription.name = request.form.get('name')
        subscription.price = float(request.form.get('price'))
        subscription.duration_days = int(request.form.get('duration_days'))
        subscription.max_cases = int(request.form.get('max_cases'))
        subscription.tokens_included = int(request.form.get('tokens_included'))
        subscription.is_organization = is_org
        subscription.max_users = int(request.form.get('max_users', 1))
        subscription.is_active = is_active
        subscription.features = request.form.get('features')
        
        db.session.commit()
        
        flash('Subscription plan updated successfully.', 'success')
        return redirect(url_for('billing.admin_subscriptions'))
    
    return render_template('admin/edit_subscription.html', subscription=subscription)

@billing_bp.route('/admin/tokens')
@login_required
def admin_tokens():
    """Admin view for managing token packages"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    token_packages = TokenPackage.query.all()
    return render_template('admin/token_packages.html', token_packages=token_packages)

@billing_bp.route('/admin/tokens/create', methods=['GET', 'POST'])
@login_required
def create_token_package():
    """Create a new token package"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Create a new token package
        is_active = request.form.get('is_active') == 'true'
        
        token_package = TokenPackage(
            name=request.form.get('name'),
            token_count=int(request.form.get('token_count')),
            price=float(request.form.get('price')),
            is_active=is_active
        )
        
        db.session.add(token_package)
        db.session.commit()
        
        flash('Token package created successfully.', 'success')
        return redirect(url_for('billing.admin_tokens'))
    
    return render_template('admin/create_token_package.html')

@billing_bp.route('/admin/tokens/edit/<int:package_id>', methods=['GET', 'POST'])
@login_required
def edit_token_package(package_id):
    """Edit a token package"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    package = TokenPackage.query.get_or_404(package_id)
    
    if request.method == 'POST':
        # Update token package
        is_active = request.form.get('is_active') == 'true'
        
        package.name = request.form.get('name')
        package.token_count = int(request.form.get('token_count'))
        package.price = float(request.form.get('price'))
        package.is_active = is_active
        
        db.session.commit()
        
        flash('Token package updated successfully.', 'success')
        return redirect(url_for('billing.admin_tokens'))
    
    # Get package statistics for display
    purchase_count = Payment.query.filter_by(
        token_package_id=package.id, status='completed').count()
    
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(
        token_package_id=package.id, status='completed').scalar() or 0
    
    package_stats = {
        'purchase_count': purchase_count,
        'total_revenue': total_revenue
    }
    
    return render_template('admin/edit_token_package.html', 
                           package=package,
                           package_stats=package_stats)

@billing_bp.route('/admin/give-tokens', methods=['POST'])
@login_required
def give_tokens():
    """Admin function to give tokens to a user"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get user email and token count
    email = request.form.get('email')
    token_count = int(request.form.get('token_amount'))
    reason = request.form.get('reason', 'bonus')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash(f'User with email {email} not found.', 'danger')
        return redirect(url_for('billing.admin_tokens'))
    
    # Add tokens to user
    user.tokens_available += token_count
    
    # Create a payment record for tracking
    transaction_id = f"ADMIN-{reason.upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    payment = Payment(
        user_id=user.id,
        amount=0,  # Free tokens
        payment_type='tokens',
        payment_method='manual',
        transaction_id=transaction_id,
        status='completed',
        completed_at=datetime.now(),
        payment_data=json.dumps({
            'reason': reason,
            'admin_id': current_user.id,
            'admin_name': current_user.username,
            'tokens': token_count
        })
    )
    
    db.session.add(payment)
    db.session.commit()
    
    flash(f'Successfully added {token_count} tokens to {user.username}.', 'success')
    return redirect(url_for('billing.admin_tokens'))