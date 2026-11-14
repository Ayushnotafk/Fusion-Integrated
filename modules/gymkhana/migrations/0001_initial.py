import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Venue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=120, unique=True)),
                ('is_configured', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'gymkhana_venue',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Club',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.SlugField(max_length=60, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('description', models.TextField(blank=True)),
                ('coordinator_id', models.PositiveBigIntegerField()),
                ('co_coordinator_id', models.PositiveBigIntegerField()),
                ('faculty_councillor_id', models.PositiveBigIntegerField()),
                ('category', models.CharField(choices=[('Technical', 'Technical'), ('Sports', 'Sports'), ('Cultural', 'Cultural')], max_length=20)),
                ('status', models.CharField(choices=[('open', 'Open'), ('confirmed', 'Confirmed')], db_index=True, default='open', max_length=9)),
            ],
            options={
                'db_table': 'gymkhana_club',
                'ordering': ['name'],
                'constraints': [models.CheckConstraint(condition=models.Q(('category__in', ['Technical', 'Sports', 'Cultural'])), name='gymkhana_club_category_allowed'), models.CheckConstraint(condition=models.Q(('status__in', ['open', 'confirmed'])), name='gymkhana_club_status_allowed')],
            },
        ),
        migrations.CreateModel(
            name='EventReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_incharge_id', models.PositiveBigIntegerField()),
                ('event_name', models.CharField(max_length=160)),
                ('event_date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('description', models.TextField()),
                ('report_file', models.FileField(upload_to='gymkhana/event-reports/')),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='event_reports', to='gymkhana.club')),
            ],
            options={
                'db_table': 'gymkhana_event_report',
                'ordering': ['-event_date', 'start_time'],
            },
        ),
        migrations.CreateModel(
            name='Poll',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=160)),
                ('description', models.TextField(blank=True)),
                ('expiration_date', models.DateTimeField()),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='polls', to='gymkhana.club')),
            ],
            options={
                'db_table': 'gymkhana_poll',
                'ordering': ['expiration_date'],
            },
        ),
        migrations.CreateModel(
            name='PollChoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('text', models.CharField(max_length=240)),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='choices', to='gymkhana.poll')),
            ],
            options={
                'db_table': 'gymkhana_poll_choice',
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='BudgetRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('purpose', models.CharField(max_length=240)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('supporting_file', models.FileField(upload_to='gymkhana/budget-requests/')),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('open', 'Open')], db_index=True, default='open', max_length=4)),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='budget_requests', to='gymkhana.club')),
            ],
            options={
                'db_table': 'gymkhana_budget_request',
                'ordering': ['-created_at'],
                'constraints': [models.CheckConstraint(condition=models.Q(('amount__gte', 0)), name='gymkhana_budget_amount_non_negative'), models.CheckConstraint(condition=models.Q(('status', 'open')), name='gymkhana_budget_status_open')],
            },
        ),
        migrations.CreateModel(
            name='ClubLeadershipDesignation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_id', models.PositiveBigIntegerField()),
                ('role', models.CharField(choices=[('coordinator', 'Coordinator'), ('head', 'Club Head'), ('co_coordinator', 'Co-Coordinator')], max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leadership_designations', to='gymkhana.club')),
            ],
            options={
                'db_table': 'gymkhana_leadership_designation',
                'indexes': [models.Index(fields=['club', 'is_active'], name='gymkhana_le_club_id_0a758d_idx'), models.Index(fields=['student_id', 'is_active'], name='gymkhana_le_student_23587b_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('role__in', ['coordinator', 'co_coordinator', 'head'])), name='gymkhana_leadership_designation_allowed'), models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('club', 'role'), name='gymkhana_one_current_leader_per_designation')],
            },
        ),
        migrations.CreateModel(
            name='MembershipApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_id', models.PositiveBigIntegerField()),
                ('achievements', models.TextField(blank=True)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('open', 'Open'), ('confirmed', 'Confirmed')], db_index=True, default='open', max_length=9)),
                ('remarks', models.TextField(blank=True)),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='membership_applications', to='gymkhana.club')),
            ],
            options={
                'db_table': 'gymkhana_membership_application',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['club', 'status'], name='gymkhana_me_club_id_bc6c30_idx'), models.Index(fields=['student_id', 'status'], name='gymkhana_me_student_3efd87_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('status__in', ['open', 'confirmed'])), name='gymkhana_membership_status_allowed')],
            },
        ),
        migrations.CreateModel(
            name='PollTargetGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('batch', models.PositiveIntegerField()),
                ('branch', models.CharField(max_length=120)),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='target_groups', to='gymkhana.poll')),
            ],
            options={
                'db_table': 'gymkhana_poll_target_group',
                'constraints': [models.UniqueConstraint(fields=('poll', 'batch', 'branch'), name='gymkhana_unique_poll_target_group')],
            },
        ),
        migrations.CreateModel(
            name='PollVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_id', models.PositiveBigIntegerField()),
                ('choice', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='votes', to='gymkhana.pollchoice')),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='gymkhana.poll')),
            ],
            options={
                'db_table': 'gymkhana_poll_vote',
                'constraints': [models.UniqueConstraint(fields=('poll', 'student_id'), name='gymkhana_one_vote_per_student_poll')],
            },
        ),
        migrations.CreateModel(
            name='ClubSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('booking_date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('description', models.TextField()),
                ('poster', models.FileField(upload_to='gymkhana/posters/')),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sessions', to='gymkhana.club')),
                ('venue', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sessions', to='gymkhana.venue')),
            ],
            options={
                'db_table': 'gymkhana_session',
                'ordering': ['booking_date', 'start_time'],
                'constraints': [models.CheckConstraint(condition=models.Q(('start_time__lt', models.F('end_time'))), name='gymkhana_session_start_before_end')],
            },
        ),
        migrations.CreateModel(
            name='ClubEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=160)),
                ('booking_date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('description', models.TextField()),
                ('poster', models.FileField(upload_to='gymkhana/posters/')),
                ('faculty_id', models.PositiveBigIntegerField()),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='events', to='gymkhana.club')),
                ('venue', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='events', to='gymkhana.venue')),
            ],
            options={
                'db_table': 'gymkhana_event',
                'ordering': ['booking_date', 'start_time'],
                'constraints': [models.CheckConstraint(condition=models.Q(('start_time__lt', models.F('end_time'))), name='gymkhana_event_start_before_end')],
            },
        ),
    ]
