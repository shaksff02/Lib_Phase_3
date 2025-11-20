from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Book, Student, IssuedBook
from .forms import BookForm, StudentForm, IssuedBookForm, ReturnBookForm


# ============= BOOK VIEWS =============
def book_list(request):
    books = Book.objects.all()
    context = {
        'books': books,
        'total_books': books.count(),
        'available_books': sum(1 for book in books if book.quantity > 0),
    }
    return render(request, 'myapp/book_list.html', context)


def create_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Book '{form.cleaned_data['title']}' created successfully!")
            return redirect('myapp:book_list')
    else:
        form = BookForm()
    
    context = {
        'form': form,
        'title': 'Add New Book',
        'button_text': 'Create Book'
    }
    return render(request, 'myapp/book_form.html', context)


def edit_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    
    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f"Book '{form.cleaned_data['title']}' updated successfully!")
            return redirect('myapp:book_list')
    else:
        form = BookForm(instance=book)
    
    context = {
        'form': form,
        'book': book,
        'title': f'Edit: {book.title}',
        'button_text': 'Update Book'
    }
    return render(request, 'myapp/book_form.html', context)


def delete_book(request, pk):
    book = get_object_or_404(Book, pk=pk)
    
    if request.method == 'POST':
        book_title = book.title
        book.delete()
        messages.success(request, f"Book '{book_title}' deleted successfully!")
        return redirect('myapp:book_list')
    
    context = {
        'book': book,
    }
    return render(request, 'myapp/book_confirm_delete.html', context)


# ============= STUDENT VIEWS =============
def student_list(request):
    students = Student.objects.all()
    context = {
        'students': students,
        'total_students': students.count(),
    }
    return render(request, 'myapp/student_list.html', context)


def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    issued_books = student.issued_books.all()
    active_issues = issued_books.filter(is_returned=False)
    
    context = {
        'student': student,
        'issued_books': issued_books,
        'active_issues': active_issues,
        'total_borrowed': active_issues.count(),
    }
    return render(request, 'myapp/student_detail.html', context)


def create_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"Student '{student.name}' created successfully!")
            return redirect('myapp:student_list')
    else:
        form = StudentForm()
    
    context = {
        'form': form,
        'title': 'Add New Student',
        'button_text': 'Create Student'
    }
    return render(request, 'myapp/student_form.html', context)


def edit_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f"Student '{student.name}' updated successfully!")
            return redirect('myapp:student_detail', pk=student.pk)
    else:
        form = StudentForm(instance=student)
    
    context = {
        'form': form,
        'student': student,
        'title': f'Edit: {student.name}',
        'button_text': 'Update Student'
    }
    return render(request, 'myapp/student_form.html', context)


def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        student_name = student.name
        student.delete()
        messages.success(request, f"Student '{student_name}' deleted successfully!")
        return redirect('myapp:student_list')
    
    context = {
        'student': student,
    }
    return render(request, 'myapp/student_confirm_delete.html', context)


# ============= ISSUE/RETURN VIEWS =============
def issued_books_list(request):
    issued_books = IssuedBook.objects.all()
    active_issues = issued_books.filter(is_returned=False)
    returned_books = issued_books.filter(is_returned=True)
    
    # Filter by status if provided
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        issued_books = active_issues
    elif status_filter == 'returned':
        issued_books = returned_books
    
    context = {
        'issued_books': issued_books,
        'total_issued': IssuedBook.objects.filter(is_returned=False).count(),
        'total_returned': IssuedBook.objects.filter(is_returned=True).count(),
        'status_filter': status_filter,
    }
    return render(request, 'myapp/issued_books_list.html', context)


def issue_book(request):
    if request.method == 'POST':
        form = IssuedBookForm(request.POST)
        if form.is_valid():
            issued_book = form.save()
            # Reduce book quantity
            book = issued_book.book
            book.quantity -= issued_book.quantity
            book.save()
            
            messages.success(
                request,
                f"Book '{book.title}' issued to '{issued_book.student.name}' ({issued_book.quantity} copies)"
            )
            return redirect('myapp:issued_books_list')
    else:
        form = IssuedBookForm()
    
    context = {
        'form': form,
        'title': 'Issue Book',
        'button_text': 'Issue Book'
    }
    return render(request, 'myapp/issue_book_form.html', context)


def return_book(request, pk):
    issued_book = get_object_or_404(IssuedBook, pk=pk)
    
    if issued_book.is_returned:
        messages.warning(request, "This book has already been returned!")
        return redirect('myapp:issued_books_list')
    
    if request.method == 'POST':
        form = ReturnBookForm(request.POST, instance=issued_book)
        if form.is_valid():
            quantity_returned = form.cleaned_data['quantity']
            
            if quantity_returned > issued_book.quantity:
                messages.error(request, f"Cannot return more than {issued_book.quantity} copies!")
                return render(request, 'myapp/return_book_form.html', {'form': form, 'issued_book': issued_book})
            
            # Update issued book
            issued_book.quantity -= quantity_returned
            issued_book.return_date = None  # Will be set when fully returned
            
            # If all copies returned, mark as returned
            if issued_book.quantity == 0:
                issued_book.is_returned = True
                from django.utils import timezone
                issued_book.return_date = timezone.now().date()
            
            issued_book.save()
            
            # Increase book quantity
            book = issued_book.book
            book.quantity += quantity_returned
            book.save()
            
            messages.success(
                request,
                f"'{quantity_returned}' copy/copies of '{book.title}' returned successfully!"
            )
            return redirect('myapp:issued_books_list')
    else:
        form = ReturnBookForm(instance=issued_book)
    
    context = {
        'form': form,
        'issued_book': issued_book,
    }
    return render(request, 'myapp/return_book_form.html', context)
