from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render, redirect
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from conference.models import Conference, UserConferenceRole, SubreviewerInvite
from .views import custom_404, custom_500, custom_403, health_check, run_migrations, create_superuser, check_database, complete_migration, fix_missing_tables
from accounts.decorators import verified_user_required

# Customize admin site
admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE

def homepage(request):
    from django.db.models import Q
    user = request.user
    # Conferences where user is chair, pc_member, author, or subreviewer (via UserConferenceRole)
    user_conferences = Conference.objects.filter(
        Q(chair=user) |
        Q(userconferencerole__user=user, userconferencerole__role__in=['author', 'pc_member', 'subreviewer'])
    ).distinct().filter(is_approved=True)
    # Add conferences where user is assigned as subreviewer via SubreviewerInvite (pending or accepted)
    subreviewer_confs = Conference.objects.filter(
        papers__subreviewer_invites__subreviewer=user,
        papers__subreviewer_invites__status__in=['invited', 'accepted']
    ).distinct().filter(is_approved=True)
    # Combine and deduplicate
    all_confs = (user_conferences | subreviewer_confs).distinct()
    # Add role information to each conference
    for conference in all_confs:
        conference.user_roles = list(UserConferenceRole.objects.filter(
            user=user, 
            conference=conference
        ).values_list('role', flat=True))
    
    # Get live and upcoming conferences for browsing
    live_upcoming_confs = Conference.objects.filter(
        status__in=['live', 'upcoming'], 
        is_approved=True
    ).exclude(id__in=all_confs.values_list('id', flat=True))
    
    context = {
        'user_conferences': all_confs,
        'live_upcoming_confs': live_upcoming_confs,
    }
    return render(request, 'homepage.html', context)

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('homepage')
    else:
        from .views import get_available_conferences
        conferences = get_available_conferences()
        return render(request, 'landing.html', {'conferences': conferences})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('conference/', include('conference.urls', namespace='conference')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('login/', lambda request: redirect('/accounts/login/', permanent=True)),
    path('news/', lambda request: render(request, 'news.html'), name='news'),
    path('quick-start/', TemplateView.as_view(template_name='quick_start_guide.html'), name='quick_start'),
    path('', root_redirect, name='landing'),
    path('home/', homepage, name='homepage'),
    path('health/', health_check, name='health_check'),
    
    # TEMPORARY MIGRATION FIX URLs - DELETE AFTER USE
    path('run-migrations/', run_migrations, name='run_migrations'),
    path('create-superuser/', create_superuser, name='create_superuser'),
    path('check-database/', check_database, name='check_database'),
    path('complete-migration/', complete_migration, name='complete_migration'),
    path('fix-missing-tables/', fix_missing_tables, name='fix_missing_tables'),
]

# Serve static files in development and production
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # In production, serve static files through WhiteNoise
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'conference_mgmt.views.custom_404'
handler500 = 'conference_mgmt.views.custom_500'
handler403 = 'conference_mgmt.views.custom_403' 