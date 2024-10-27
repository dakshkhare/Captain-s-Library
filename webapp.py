from flask import Flask, render_template, request, redirect, url_for, flash, session
from models.models import db, Student, Book, Borrowing, Admin
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('user_type')

        if user_type == 'admin':
            # Admin login
            username = request.form.get('username')
            password = request.form.get('password')  # Get password for admin
            admin = Admin.query.filter_by(username=username, password=password).first()
            if admin:
                session['admin_id'] = admin.id
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials')

        elif user_type == 'student':
            # Student login
            roll_number = request.form.get('roll_number')
            password = request.form.get('password')  # Get password for student
            student = Student.query.filter_by(roll_number=roll_number, password=password).first()
            if student:
                session['student_id'] = student.id
                return redirect(url_for('student_dashboard'))
            else:
                flash('Invalid student credentials')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        password = request.form.get('password') 

        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already exists')
            return redirect(url_for('register'))

        new_student = Student(name=name, roll_number=roll_number, password=password)  # Password saved as plain text
        db.session.add(new_student)
        db.session.commit()

        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    pending_requests = Borrowing.query.filter_by(status='pending').all()
    books = Book.query.all()
    return render_template('admin_dashboard.html', pending_requests=pending_requests, books=books)

@app.route('/admin/add_book', methods=['POST'])
def add_book():
    name = request.form.get('name')
    quantity = int(request.form.get('quantity'))

    existing_book = Book.query.filter_by(name=name).first()
    if existing_book:
        existing_book.quantity += quantity
    else:
        new_book = Book(name=name, quantity=quantity)
        db.session.add(new_book)

    db.session.commit()
    flash('Book added successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/handle_request/<int:borrow_id>/<action>')
def handle_request(borrow_id, action):
    borrow_request = Borrowing.query.get_or_404(borrow_id)
    book = Book.query.get(borrow_request.book_id)
    student = Student.query.get(borrow_request.student_id)

    if action == 'approve':
        if book.quantity > 0:
            borrow_request.status = 'approved'
            book.quantity -= 1
            student.has_book = True
            student.borrowed_book_id = book.id
            flash('Request approved')
        else:
            flash('Book not available')
    elif action == 'reject':
        borrow_request.status = 'rejected'
        flash('Request rejected')

    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/student/dashboard')
def student_dashboard():
    # Check if student is logged in
    if 'student_id' not in session:
        flash('Please log in first')
        return redirect(url_for('login'))
    
    # Get the logged-in student's data
    student = Student.query.get(session['student_id'])
    if not student:
        session.clear()
        flash('Student not found')
        return redirect(url_for('login'))

    # Get available books and borrowed book if any
    books = Book.query.all()
    borrowed_book = None
    if student.borrowed_book_id:
        borrowed_book = Book.query.get(student.borrowed_book_id)

    return render_template('student_dashboard.html', 
                         student=student,
                         books=books, 
                         borrowed_book=borrowed_book)

@app.route('/student/borrow/<int:book_id>')
def borrow_book(book_id):
    # Check if student is logged in
    if 'student_id' not in session:
        flash('Please log in first')
        return redirect(url_for('login'))

    student = Student.query.get(session['student_id'])
    if not student:
        session.clear()
        flash('Student not found')
        return redirect(url_for('login'))

    book = Book.query.get_or_404(book_id)

    if student.has_book:
        flash('You already have a book borrowed')
        return redirect(url_for('student_dashboard'))

    new_borrowing = Borrowing(
        book_id=book.id,
        student_id=student.id,
        book_name=book.name,
        student_name=student.name
    )
    db.session.add(new_borrowing)
    db.session.commit()

    flash('Borrow request submitted')
    return redirect(url_for('student_dashboard'))

@app.route('/student/return')
def return_book():
    # Check if student is logged in
    if 'student_id' not in session:
        flash('Please log in first')
        return redirect(url_for('login'))

    student = Student.query.get(session['student_id'])
    if not student:
        session.clear()
        flash('Student not found')
        return redirect(url_for('login'))

    if not student.has_book:
        flash('No book to return')
        return redirect(url_for('student_dashboard'))

    borrow_record = Borrowing.query.filter_by(
        student_id=student.id,
        book_id=student.borrowed_book_id,
        status='approved'
    ).first()

    if borrow_record:
        book = Book.query.get(student.borrowed_book_id)
        book.quantity += 1
        student.has_book = False
        student.borrowed_book_id = None
        borrow_record.status = 'returned'
        db.session.commit()
        flash('Book returned successfully')

    return redirect(url_for('student_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

