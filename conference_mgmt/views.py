from django.shortcuts import render
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

def custom_404(request, exception):
    """Custom 404 error handler"""
    logger.warning(f'404 error for URL: {request.path} from IP: {request.META.get("REMOTE_ADDR", "unknown")}')
    return render(request, '404.html', status=404)

def custom_500(request):
    """Custom 500 error handler"""
    logger.error(f'500 error for URL: {request.path} from IP: {request.META.get("REMOTE_ADDR", "unknown")}')
    return render(request, '500.html', status=500)

def custom_403(request, exception):
    """Custom 403 error handler"""
    logger.warning(f'403 error for URL: {request.path} from IP: {request.META.get("REMOTE_ADDR", "unknown")}')
    return render(request, '403.html', status=403)

def health_check(request):
    """Health check endpoint for monitoring"""
    return HttpResponse("OK", content_type="text/plain") 