from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_verified', 'date_joined', 'last_login', 'user_actions')
    list_filter = ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    list_per_page = 25
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Account Status', {'fields': ('is_verified', 'otp', 'otp_created_at')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login', 'otp_created_at')

    def user_actions(self, obj):
        actions = []
        actions.append(f'<a href="/admin/accounts/user/{obj.id}/change/" style="color: #007bff; text-decoration: none; margin-right: 10px;">✏️ Edit</a>')
        
        # Show conferences created by this user
        from conference.models import Conference
        user_conferences = Conference.objects.filter(chair=obj)
        if user_conferences.exists():
            actions.append(f'<a href="/admin/conference/conference/?chair__id__exact={obj.id}" style="color: #28a745; text-decoration: none; margin-right: 10px;">🏢 Conferences ({user_conferences.count()})</a>')
        
        # Show papers by this user
        from conference.models import Paper
        user_papers = Paper.objects.filter(author=obj)
        if user_papers.exists():
            actions.append(f'<a href="/admin/conference/paper/?author__id__exact={obj.id}" style="color: #ffc107; text-decoration: none;">📄 Papers ({user_papers.count()})</a>')
        
        return admin.utils.format_html_join('', '{}', ((action,) for action in actions))
    user_actions.short_description = 'Actions'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related()

admin.site.register(User, CustomUserAdmin) 