from django.db.models import Sum
from django.db import transaction
from ...models import ThriftGroup, ThriftMembership, ThriftPayout, ThriftContribution


def rotate_payout(group_id):
    group = ThriftGroup.objects.get(id=group_id)
    members = group.thriftmembership_set.filter(is_active=True)
    
    # Get last payout to determine the next beneficiary
    last_payout = ThriftPayout.objects.filter(group=group).order_by('-payout_order').first()
    next_order = last_payout.payout_order + 1 if last_payout else 1
    
    # Circular rotation logic
    if next_order > members.count():
        next_order = 1
    
    next_beneficiary = members.get(rotation_order=next_order)
    
    # Calculate total pot
    total_contributions = ThriftContribution.objects.filter(
        membership__group=group,
        is_verified=True
    ).aggregate(total=Sum('amount'))['total']
    
    # Create payout record in a transaction
    with transaction.atomic():
        payout = ThriftPayout.objects.create(
            group=group,
            beneficiary=next_beneficiary.user,
            amount=total_contributions,
            payout_order=next_order
        )
    
    return payout

def create_thrift_group(group_data: dict):
    group = ThriftGroup.objects.create(**group_data)
    return group

def create_thrift_membership(membership_data: dict):
    membership = ThriftMembership.objects.create(**membership_data)
    return membership
