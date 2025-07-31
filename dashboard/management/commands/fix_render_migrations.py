from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command
import os

class Command(BaseCommand):
    help = 'Fix migration issues on Render deployment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even if errors occur',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting migration fix for Render...'))
        
        # Check if we're in production
        is_production = os.environ.get('DATABASE_URL') is not None
        self.stdout.write(f"Environment: {'Production (PostgreSQL)' if is_production else 'Development (SQLite)'}")
        
        # Test database connection
        self.stdout.write("🔍 Testing database connection...")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    self.stdout.write(self.style.SUCCESS("✅ Database connection successful"))
                else:
                    self.stdout.write(self.style.ERROR("❌ Database connection test failed"))
                    return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Database connection failed: {e}"))
            return
        
        # Show current migration status
        self.stdout.write("\n📋 Current migration status:")
        try:
            call_command('showmigrations', '--list')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  Could not show migrations: {e}"))
        
        # Run migrations
        self.stdout.write("\n🔄 Running migrations...")
        try:
            call_command('migrate', '--no-input', '--verbosity=2')
            self.stdout.write(self.style.SUCCESS("✅ Migrations completed successfully"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  Normal migration failed: {e}"))
            if options['force']:
                self.stdout.write("🔄 Trying with fake initial...")
                try:
                    call_command('migrate', '--fake-initial', '--no-input', '--verbosity=2')
                    self.stdout.write(self.style.SUCCESS("✅ Migrations completed with fake initial"))
                except Exception as e2:
                    self.stdout.write(self.style.ERROR(f"❌ Migration with fake initial also failed: {e2}"))
                    return
            else:
                self.stdout.write(self.style.ERROR("❌ Migration failed. Use --force to try fake initial"))
                return
        
        # Check if required tables exist
        self.stdout.write("\n🔍 Checking required tables...")
        try:
            with connection.cursor() as cursor:
                # Check for accounts_user table
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'accounts_user'
                    );
                """)
                result = cursor.fetchone()
                if result and result[0]:
                    self.stdout.write(self.style.SUCCESS("✅ accounts_user table exists"))
                else:
                    self.stdout.write(self.style.ERROR("❌ accounts_user table does not exist"))
                    return
                
                # Check for other important tables
                tables_to_check = [
                    'django_migrations',
                    'django_content_type',
                    'django_admin_log',
                    'conference_conference'
                ]
                
                for table in tables_to_check:
                    cursor.execute(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = '{table}'
                        );
                    """)
                    result = cursor.fetchone()
                    if result and result[0]:
                        self.stdout.write(self.style.SUCCESS(f"✅ {table} table exists"))
                    else:
                        self.stdout.write(self.style.WARNING(f"⚠️  {table} table does not exist"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Could not check tables: {e}"))
            return
        
        # Create superuser if it doesn't exist
        self.stdout.write("\n👤 Checking superuser...")
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
                self.stdout.write(self.style.SUCCESS("✅ Superuser created: admin/admin123"))
            else:
                self.stdout.write("ℹ️  Superuser already exists")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  Superuser creation failed: {e}"))
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("🎉 Migration fix completed!"))
        self.stdout.write("\n💡 Next steps:")
        self.stdout.write("1. Try accessing your admin panel again")
        self.stdout.write("2. Login with admin/admin123")
        self.stdout.write("3. If issues persist, check Render logs") 