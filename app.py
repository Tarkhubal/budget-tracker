from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField, FloatField, SelectField, DateField, BooleanField, IntegerField, Form
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Template filters
@app.template_filter('category_icon')
def category_icon(category):
    icons = {
        'food': '🍽️',
        'hygiene': '🧼',
        'transportation': '🚗',
        'utilities': '🏠',
        'entertainment': '🎬',
        'healthcare': '🏥',
        'clothing': '👕',
        'other': '📦'
    }
    return icons.get(category, '📦')

@app.template_filter('category_color')
def category_color(index):
    colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
        '#9966FF', '#FF9F40', '#C9CBCF', '#4BC0C0'
    ]
    return colors[index % len(colors)]

# Add min function to template context
@app.template_global()
def min(a, b):
    return a if a < b else b

# Database Models
class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_frequency = db.Column(db.String(20))  # 'monthly', 'yearly'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_frequency = db.Column(db.String(20))  # 'monthly', 'yearly'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False, unique=True)
    allocated_amount = db.Column(db.Float, nullable=False)
    is_adaptive = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=1)  # 1 = high priority, 5 = low priority
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Forms
class IncomeForm(Form):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    description = StringField('Description', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=datetime.today)
    is_recurring = BooleanField('Recurring Income')
    recurring_frequency = SelectField('Frequency', choices=[('', 'Select...'), ('monthly', 'Monthly'), ('yearly', 'Yearly')])

class ExpenseForm(Form):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    description = StringField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('food', 'Food'),
        ('hygiene', 'Hygiene'),
        ('transportation', 'Transportation'),
        ('utilities', 'Utilities'),
        ('entertainment', 'Entertainment'),
        ('healthcare', 'Healthcare'),
        ('clothing', 'Clothing'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=datetime.today)
    is_recurring = BooleanField('Recurring Expense')
    recurring_frequency = SelectField('Frequency', choices=[('', 'Select...'), ('monthly', 'Monthly'), ('yearly', 'Yearly')])

class BudgetForm(Form):
    category = SelectField('Category', choices=[
        ('food', 'Food'),
        ('hygiene', 'Hygiene'),
        ('transportation', 'Transportation'),
        ('utilities', 'Utilities'),
        ('entertainment', 'Entertainment'),
        ('healthcare', 'Healthcare'),
        ('clothing', 'Clothing'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    allocated_amount = FloatField('Budget Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    priority = IntegerField('Priority (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)], default=1)

# Helper functions
def get_date_range(period, date=None):
    if date is None:
        date = datetime.today().date()
    
    if period == 'week':
        start_date = date - timedelta(days=date.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = date.replace(day=1)
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
    elif period == 'year':
        start_date = date.replace(month=1, day=1)
        end_date = date.replace(month=12, day=31)
    
    return start_date, end_date

def calculate_adaptive_budgets():
    """Calculate adaptive budget allocations based on income and expenses"""
    current_month_start, current_month_end = get_date_range('month')
    
    # Get current month income
    monthly_income = db.session.query(db.func.sum(Income.amount)).filter(
        Income.date >= current_month_start,
        Income.date <= current_month_end
    ).scalar() or 0
    
    # Add recurring income
    recurring_income = db.session.query(db.func.sum(Income.amount)).filter(
        Income.is_recurring == True,
        Income.recurring_frequency == 'monthly'
    ).scalar() or 0
    
    yearly_recurring = db.session.query(db.func.sum(Income.amount)).filter(
        Income.is_recurring == True,
        Income.recurring_frequency == 'yearly'
    ).scalar() or 0
    
    total_monthly_income = monthly_income + recurring_income + (yearly_recurring / 12)
    
    # Get fixed expenses (recurring)
    fixed_monthly_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.is_recurring == True,
        Expense.recurring_frequency == 'monthly'
    ).scalar() or 0
    
    fixed_yearly_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.is_recurring == True,
        Expense.recurring_frequency == 'yearly'
    ).scalar() or 0
    
    total_fixed_expenses = fixed_monthly_expenses + (fixed_yearly_expenses / 12)
    
    # Available budget after fixed expenses
    available_budget = total_monthly_income - total_fixed_expenses
    
    if available_budget <= 0:
        return {}
    
    # Get all budgets ordered by priority
    budgets = Budget.query.filter(Budget.is_adaptive == True).order_by(Budget.priority).all()
    
    if not budgets:
        return {}
    
    # Calculate proportional allocation based on priority
    priority_weights = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1, 5: 0.05}
    total_weight = sum(priority_weights.get(b.priority, 0.05) for b in budgets)
    
    adaptive_allocations = {}
    for budget in budgets:
        weight = priority_weights.get(budget.priority, 0.05)
        allocated = (available_budget * weight / total_weight)
        adaptive_allocations[budget.category] = allocated
    
    return adaptive_allocations

# Routes
@app.route('/')
def index():
    # Get current month data
    current_date = datetime.today().date()
    month_start, month_end = get_date_range('month', current_date)
    
    # Calculate totals including recurring income
    monthly_income = db.session.query(db.func.sum(Income.amount)).filter(
        Income.date >= month_start,
        Income.date <= month_end
    ).scalar() or 0
    
    # Add recurring monthly income
    recurring_monthly_income = db.session.query(db.func.sum(Income.amount)).filter(
        Income.is_recurring == True,
        Income.recurring_frequency == 'monthly'
    ).scalar() or 0
    
    # Add prorated yearly recurring income
    recurring_yearly_income = db.session.query(db.func.sum(Income.amount)).filter(
        Income.is_recurring == True,
        Income.recurring_frequency == 'yearly'
    ).scalar() or 0
    
    total_monthly_income = monthly_income + recurring_monthly_income + (recurring_yearly_income / 12 if recurring_yearly_income else 0)
    
    # Calculate monthly expenses including recurring
    monthly_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.date >= month_start,
        Expense.date <= month_end
    ).scalar() or 0
    
    # Add recurring monthly expenses
    recurring_monthly_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.is_recurring == True,
        Expense.recurring_frequency == 'monthly'
    ).scalar() or 0
    
    # Add prorated yearly recurring expenses
    recurring_yearly_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.is_recurring == True,
        Expense.recurring_frequency == 'yearly'
    ).scalar() or 0
    
    total_monthly_expenses = monthly_expenses + recurring_monthly_expenses + (recurring_yearly_expenses / 12 if recurring_yearly_expenses else 0)
    
    # Get recent transactions
    recent_income = Income.query.order_by(Income.date.desc()).limit(5).all()
    recent_expenses = Expense.query.order_by(Expense.date.desc()).limit(5).all()
    
    # Get budget vs spending
    budgets = Budget.query.all()
    budget_status = []
    
    adaptive_budgets = calculate_adaptive_budgets()
    
    for budget in budgets:
        spent = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.category == budget.category,
            Expense.date >= month_start,
            Expense.date <= month_end
        ).scalar() or 0
        
        allocated = adaptive_budgets.get(budget.category, budget.allocated_amount)
        
        budget_status.append({
            'category': budget.category,
            'allocated': allocated,
            'spent': spent,
            'remaining': allocated - spent,
            'percentage': (spent / allocated * 100) if allocated > 0 else 0
        })
    
    return render_template('index.html', 
                         monthly_income=total_monthly_income,
                         monthly_expenses=total_monthly_expenses,
                         balance=total_monthly_income - total_monthly_expenses,
                         recent_income=recent_income,
                         recent_expenses=recent_expenses,
                         budget_status=budget_status)

@app.route('/income')
def income_list():
    period = request.args.get('period', 'month')
    date_str = request.args.get('date')
    
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            selected_date = datetime.today().date()
    else:
        selected_date = datetime.today().date()
    
    start_date, end_date = get_date_range(period, selected_date)
    
    income_records = Income.query.filter(
        Income.date >= start_date,
        Income.date <= end_date
    ).order_by(Income.date.desc()).all()
    
    total_income = sum(record.amount for record in income_records)
    
    return render_template('income.html', 
                         income_records=income_records,
                         total_income=total_income,
                         period=period,
                         selected_date=selected_date,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/add_income', methods=['GET', 'POST'])
def add_income():
    form = IncomeForm(request.form)
    
    if request.method == 'POST' and form.validate():
        income = Income(
            amount=form.amount.data,
            description=form.description.data,
            date=form.date.data,
            is_recurring=form.is_recurring.data,
            recurring_frequency=form.recurring_frequency.data if form.is_recurring.data else None
        )
        
        db.session.add(income)
        db.session.commit()
        flash('Income added successfully!', 'success')
        return redirect(url_for('income_list'))
    
    return render_template('add_income.html', form=form)

@app.route('/expenses')
def expense_list():
    period = request.args.get('period', 'month')
    category = request.args.get('category', 'all')
    date_str = request.args.get('date')
    
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            selected_date = datetime.today().date()
    else:
        selected_date = datetime.today().date()
    
    start_date, end_date = get_date_range(period, selected_date)
    
    query = Expense.query.filter(
        Expense.date >= start_date,
        Expense.date <= end_date
    )
    
    if category != 'all':
        query = query.filter(Expense.category == category)
    
    expenses = query.order_by(Expense.date.desc()).all()
    total_expenses = sum(expense.amount for expense in expenses)
    
    # Get expenses by category for charts
    category_totals = db.session.query(
        Expense.category,
        db.func.sum(Expense.amount).label('total')
    ).filter(
        Expense.date >= start_date,
        Expense.date <= end_date
    ).group_by(Expense.category).all()
    
    return render_template('expenses.html',
                         expenses=expenses,
                         total_expenses=total_expenses,
                         category_totals=category_totals,
                         period=period,
                         selected_category=category,
                         selected_date=selected_date,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    form = ExpenseForm(request.form)
    
    if request.method == 'POST' and form.validate():
        expense = Expense(
            amount=form.amount.data,
            description=form.description.data,
            category=form.category.data,
            date=form.date.data,
            is_recurring=form.is_recurring.data,
            recurring_frequency=form.recurring_frequency.data if form.is_recurring.data else None
        )
        
        db.session.add(expense)
        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('expense_list'))
    
    return render_template('add_expense.html', form=form)

@app.route('/budgets')
def budget_list():
    budgets = Budget.query.order_by(Budget.priority).all()
    current_month_start, current_month_end = get_date_range('month')
    
    budget_data = []
    adaptive_budgets = calculate_adaptive_budgets()
    
    for budget in budgets:
        spent = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.category == budget.category,
            Expense.date >= current_month_start,
            Expense.date <= current_month_end
        ).scalar() or 0
        
        allocated = adaptive_budgets.get(budget.category, budget.allocated_amount)
        
        budget_data.append({
            'id': budget.id,
            'category': budget.category,
            'allocated': allocated,
            'original_allocated': budget.allocated_amount,
            'spent': spent,
            'remaining': allocated - spent,
            'percentage': (spent / allocated * 100) if allocated > 0 else 0,
            'priority': budget.priority,
            'is_adaptive': budget.is_adaptive
        })
    
    return render_template('budgets.html', budget_data=budget_data)

@app.route('/add_budget', methods=['GET', 'POST'])
def add_budget():
    form = BudgetForm(request.form)
    
    if request.method == 'POST' and form.validate():
        # Check if budget for this category already exists
        existing_budget = Budget.query.filter_by(category=form.category.data).first()
        if existing_budget:
            flash('Budget for this category already exists!', 'error')
            return render_template('add_budget.html', form=form)
        
        budget = Budget(
            category=form.category.data,
            allocated_amount=form.allocated_amount.data,
            priority=form.priority.data,
            is_adaptive=True  # Always adaptive for now
        )
        
        db.session.add(budget)
        db.session.commit()
        flash('Budget added successfully!', 'success')
        return redirect(url_for('budget_list'))
    
    return render_template('add_budget.html', form=form)

@app.route('/api/income_chart_data')
def income_chart_data():
    period = request.args.get('period', 'month')
    
    if period == 'week':
        # Get weekly data for last 12 weeks
        data = []
        for i in range(12):
            week_start = datetime.today().date() - timedelta(weeks=i)
            week_start = week_start - timedelta(days=week_start.weekday())
            week_end = week_start + timedelta(days=6)
            
            weekly_income = db.session.query(db.func.sum(Income.amount)).filter(
                Income.date >= week_start,
                Income.date <= week_end
            ).scalar() or 0
            
            data.append({
                'period': f"Week of {week_start.strftime('%m/%d')}",
                'amount': float(weekly_income)
            })
        
        data.reverse()
        
    elif period == 'month':
        # Get monthly data for last 12 months
        data = []
        for i in range(12):
            month_date = datetime.today().date() - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            monthly_income = db.session.query(db.func.sum(Income.amount)).filter(
                Income.date >= month_start,
                Income.date <= month_end
            ).scalar() or 0
            
            data.append({
                'period': month_start.strftime('%Y-%m'),
                'amount': float(monthly_income)
            })
        
        data.reverse()
        
    elif period == 'year':
        # Get yearly data for last 5 years
        data = []
        current_year = datetime.today().year
        for i in range(5):
            year = current_year - i
            year_start = datetime(year, 1, 1).date()
            year_end = datetime(year, 12, 31).date()
            
            yearly_income = db.session.query(db.func.sum(Income.amount)).filter(
                Income.date >= year_start,
                Income.date <= year_end
            ).scalar() or 0
            
            data.append({
                'period': str(year),
                'amount': float(yearly_income)
            })
        
        data.reverse()
    
    return jsonify(data)

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Add some sample data if tables are empty
        if Income.query.first() is None:
            print("Adding sample data...")
            
            # Add sample income
            sample_income = Income(
                amount=5000.0,
                description="Monthly Salary",
                date=datetime.today().date(),
                is_recurring=True,
                recurring_frequency="monthly"
            )
            db.session.add(sample_income)
            
            # Add sample expense
            sample_expense = Expense(
                amount=150.0,
                description="Groceries",
                category="food",
                date=datetime.today().date(),
                is_recurring=False
            )
            db.session.add(sample_expense)
            
            # Add sample budget
            sample_budget = Budget(
                category="food",
                allocated_amount=400.0,
                priority=1,
                is_adaptive=True
            )
            db.session.add(sample_budget)
            
            db.session.commit()
            print("Sample data added successfully!")
    
    app.run(debug=True)