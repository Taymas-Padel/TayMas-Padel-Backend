from django.db import migrations


def migrate_service_types(apps, schema_editor):
    MembershipType = apps.get_model('memberships', 'MembershipType')

    mapping = {
        'PADEL': 'PADEL_HOURS',
        'GYM_UNLIMITED': 'GYM',
        'GYM_PACK': 'GYM',
    }

    for old_val, new_val in mapping.items():
        MembershipType.objects.filter(service_type=old_val).update(service_type=new_val)


def reverse_service_types(apps, schema_editor):
    MembershipType = apps.get_model('memberships', 'MembershipType')
    MembershipType.objects.filter(service_type='PADEL_HOURS').update(service_type='PADEL')
    MembershipType.objects.filter(service_type='GYM').update(service_type='GYM_UNLIMITED')


class Migration(migrations.Migration):

    dependencies = [
        ('memberships', '0004_redesign_membership_for_new_tariffs'),
    ]

    operations = [
        migrations.RunPython(migrate_service_types, reverse_service_types),
    ]
