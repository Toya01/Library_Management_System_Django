from library.forms import IssueBookForm
from django.shortcuts import redirect, render,HttpResponse
from .models import *
from .forms import IssueBookForm
from django.contrib.auth import authenticate, login, logout
from . import forms, models
from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from .models import Student
from .forms import OTPForm  # Create a form to handle OTP input
from django.conf import settings
import time
import requests
from django.shortcuts import render

from .forms import OTPForm  # This assumes OTPForm is in the same 'library' app.


# Function to generate and send OTP to user's email
def generate_and_send_otp(email):
    otp = get_random_string(length=6, allowed_chars='0123456789')
    # Store OTP in the session for verification later
    # (Alternatively, store it in the database for persistence)
    # Example: store OTP in session
    session_key = f"otp_{email}"
    session_value = {'otp': otp, 'timestamp': time.time()}
    request.session[session_key] = session_value

    # Send OTP to the user's email
    send_mail(
        'Your OTP for Email Verification',
        f'Your OTP is: {otp}',
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    return otp

# View for displaying OTP verification page
def verify_otp(request):
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        image = request.FILES.get('image')

        # Get the OTP from the session
        session_data = request.session.get(f"otp_{request.user.email}", None)

        if session_data:
            session_otp = session_data.get('otp')
            session_timestamp = session_data.get('timestamp')

            # Check if OTP is expired (e.g., 5 minutes validity)
            if time.time() - session_timestamp > 300:  # 5 minutes expiry
                messages.error(request, 'OTP has expired. Please request a new one.')
                return redirect('verify_otp')

            if otp_input == session_otp:
                # Verify OTP successfully and handle image
                student = Student.objects.get(user=request.user)
                student.image = image
                student.save()
                messages.success(request, 'Email verified successfully!')
                return redirect('home')  # Redirect to a page after successful verification
            else:
                messages.error(request, 'Invalid OTP. Please try again.')
        else:
            messages.error(request, 'OTP is not available or has expired.')
    
    return render(request, 'verify_otp.html')

def index(request):
    return render(request, "index.html")

@login_required(login_url = '/admin_login')
def add_book(request):
    if request.method == "POST":
        name = request.POST['name']
        author = request.POST['author']
        isbn = request.POST['isbn']
        category = request.POST['category']

        books = Book.objects.create(name=name, author=author, isbn=isbn, category=category)
        books.save()
        alert = True
        return render(request, "add_book.html", {'alert':alert})
    return render(request, "add_book.html")

@login_required(login_url = '/admin_login')
def view_books(request):
    books = Book.objects.all()
    return render(request, "view_books.html", {'books':books})

@login_required(login_url = '/admin_login')
def view_students(request):
    students = Student.objects.all()
    return render(request, "view_students.html", {'students':students})

@login_required(login_url = '/admin_login')
def issue_book(request):
    form = forms.IssueBookForm()
    if request.method == "POST":
        form = forms.IssueBookForm(request.POST)
        if form.is_valid():
            obj = models.IssuedBook()
            obj.student_id = request.POST['name2']
            obj.isbn = request.POST['isbn2']
            obj.save()
            alert = True
            return render(request, "issue_book.html", {'obj':obj, 'alert':alert})
    return render(request, "issue_book.html", {'form':form})


@login_required(login_url='/admin_login')
def view_issued_book(request):
    issuedBooks = IssuedBook.objects.all()
    
    # If there are no issued books, we can return an empty or a special message
    if not issuedBooks:
        return render(request, "view_issued_book.html", {'message': 'No books issued.'})
    
    details = []
    
    for i in issuedBooks:
        # Calculate the number of days since the book was issued
        days = (date.today() - i.issued_date).days
        fine = 0
        
        # Apply fine if the book is overdue
        if days > 14:
            day = days - 14
            fine = day * 5
        
        # Get the book and student related to the issued book
        books = models.Book.objects.filter(isbn=i.isbn)
        students = models.Student.objects.filter(user=i.student_id)
        
        # Check if there are books and students to avoid index errors
        if books and students:
            for book, student in zip(books, students):
                t = (student.user, student.user_id, book.name, book.isbn, i.issued_date, i.expiry_date, fine)
                details.append(t)
    
    return render(request, "view_issued_book.html", {'issuedBooks': issuedBooks, 'details': details})


@login_required(login_url = '/student_login')
def student_issued_books(request):
    student = Student.objects.filter(user_id=request.user.id)
    issuedBooks = IssuedBook.objects.filter(student_id=student[0].user_id)
    li1 = []
    li2 = []

    for i in issuedBooks:
        books = Book.objects.filter(isbn=i.isbn)
        for book in books:
            t=(request.user.id, request.user.get_full_name, book.name,book.author)
            li1.append(t)

        days=(date.today()-i.issued_date)
        d=days.days
        fine=0
        if d>15:
            day=d-14
            fine=day*5
        t=(issuedBooks[0].issued_date, issuedBooks[0].expiry_date, fine)
        li2.append(t)
    return render(request,'student_issued_books.html',{'li1':li1, 'li2':li2})

@login_required(login_url = '/student_login')
def profile(request):
    return render(request, "profile.html")

@login_required(login_url = '/student_login')
def edit_profile(request):
    student = Student.objects.get(user=request.user)
    if request.method == "POST":
        email = request.POST['email']
        phone = request.POST['phone']
        branch = request.POST['branch']
        classroom = request.POST['classroom']
        roll_no = request.POST['roll_no']

        student.user.email = email
        student.phone = phone
        student.branch = branch
        student.classroom = classroom
        student.roll_no = roll_no
        student.user.save()
        student.save()
        alert = True
        return render(request, "edit_profile.html", {'alert':alert})
    return render(request, "edit_profile.html")

def delete_book(request, myid):
    books = Book.objects.filter(id=myid)
    books.delete()
    return redirect("/view_books")

def delete_student(request, myid):
    students = Student.objects.filter(id=myid)
    students.delete()
    return redirect("/view_students")

def change_password(request):
    if request.method == "POST":
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        try:
            u = User.objects.get(id=request.user.id)
            if u.check_password(current_password):
                u.set_password(new_password)
                u.save()
                alert = True
                return render(request, "change_password.html", {'alert':alert})
            else:
                currpasswrong = True
                return render(request, "change_password.html", {'currpasswrong':currpasswrong})
        except:
            pass
    return render(request, "change_password.html")

def student_registration(request):
    if request.method == "POST":
        # Retrieve form data
        username = request.POST['username']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        phone = request.POST['phone']
        branch = request.POST['branch']
        classroom = request.POST['classroom']
        roll_no = request.POST['roll_no']
        image = request.FILES.get('image')  # Safely retrieve the image from the form
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            passnotmatch = True
            return render(request, "student_registration.html", {'passnotmatch': passnotmatch})

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)
        
        # Create student and save
        student = Student.objects.create(user=user, phone=phone, branch=branch, classroom=classroom, roll_no=roll_no, image=image)
        user.save()
        student.save()

        # Set alert to True for success
        alert = True
        return render(request, "student_registration.html", {'alert': alert})

    return render(request, "student_registration.html")

def student_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            if request.user.is_superuser:
                return HttpResponse("You are not a student!!")
            else:
                return redirect("/profile")
        else:
            alert = True
            return render(request, "student_login.html", {'alert':alert})
    return render(request, "student_login.html")

def admin_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            if request.user.is_superuser:
                return redirect("/add_book")
            else:
                return HttpResponse("You are not an admin.")
        else:
            alert = True
            return render(request, "admin_login.html", {'alert':alert})
    return render(request, "admin_login.html")

def Logout(request):
    logout(request)
    return redirect ("/")

def search_books(request):
    query = request.GET.get('q')
    books = []

    if query:
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            books = data.get('items', [])

    return render(request, 'search_books.html', {'books': books})
