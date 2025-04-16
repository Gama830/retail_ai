from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CustomUserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from accounts.decorators import admin_required
from .models import CustomUser
from .forms import CustomUserEditForm  # make sure this is imported
from django.shortcuts import render, redirect, get_object_or_404

User = get_user_model()
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        try:
            user_obj = User.objects.get(username=username)
            if not user_obj.is_active:
                messages.error(request, "⛔ Your account is not yet activated. Please contact the admin.")
                return redirect('accounts:login')
        except User.DoesNotExist:
            pass  # Let it fall through to invalid login

        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('dashboard:dashboard_main')
            elif user.is_staff_user:
                return redirect('billing:create_sale')
            # fallback if needed
            return redirect('dashboard:dashboard_main')  # redirect to the new dashboard view
        else:
            messages.error(request, "❌ Invalid username or password.")
            return redirect('accounts:login')
    
    return render(request, 'accounts/login.html')

def user_logout(request):
    logout(request)
    return redirect('accounts:login')

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_active = False  # ❌ Inactive by default
            # Optional: Set default role
            user.is_staff_user = True
            user.save()
            messages.info(request, "✅ Account created. Awaiting admin approval.")
            return redirect('accounts:login')
            # login(request, user)  # auto login after signup
            # return redirect('billing:create_sale')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

User = get_user_model()
@admin_required
def manage_accounts(request):
    users = User.objects.exclude(id=request.user.id)  # Exclude the admin himself
    return render(request, 'accounts/manage_accounts.html', {'users': users})

@admin_required
def edit_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    # 🔄 Update: Check if the user is a "standard admin"
    is_standard_admin = user.is_superuser and user.is_staff and not user.is_staff_user

    # 🔄 Update: Only allow editing another admin if they're standard
    if user.is_superuser and user != request.user and is_standard_admin:
        return render(request, 'errors/permission_denied.html')

    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, instance=user)
        if form.is_valid():
            updated_user = form.save(commit=False)

            selected_role = form.cleaned_data['role']

            # Prevent demoting yourself from admin
            if user.id == request.user.id and selected_role != 'admin':
                messages.error(request, "❌ You cannot change your own role.")
                return redirect('accounts:manage_accounts')

            # Apply role change
            if selected_role == 'admin':
                updated_user.is_superuser = True
                updated_user.is_staff = False      # ✅ required for admin access
                updated_user.is_staff_user = False
            else:
                updated_user.is_superuser = False
                updated_user.is_staff = False  # ✅ remove admin panel access
                updated_user.is_staff_user = True

            updated_user.save()
            messages.success(request, "✅ User updated successfully.")
            return redirect('accounts:manage_accounts')
    else:
        form = CustomUserEditForm(instance=user)

    return render(request, 'accounts/edit_user.html', {'form': form, 'user_obj': user})



@admin_required
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if user.is_superuser:
        return render(request, 'errors/permission_denied.html')

    if request.method == 'POST':
        user.delete()
        return redirect('accounts:manage_accounts')

    return render(request, 'accounts/confirm_delete.html', {'user_obj': user})

@admin_required
def toggle_user_activation(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if user == request.user:
        messages.error(request, "❌ You cannot deactivate your own account.")
        return redirect('accounts:manage_accounts')

    is_standard_admin = user.is_superuser and user.is_staff and not user.is_staff_user
    if user.is_superuser and user != request.user and is_standard_admin:
        return render(request, 'errors/permission_denied.html')
    
    user.is_active = not user.is_active
    user.save()

    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"✅ {user.username}'s account has been {status}.")
    return redirect('accounts:manage_accounts')
