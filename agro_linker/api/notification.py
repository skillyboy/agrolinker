from ninja import Router
from agro_linker.schemas import *
from agro_linker.models import *
from agro_linker.api import *
from ninja import Router
router = Router(tags=["Notification"])

def notify_loan_update(loan: LoanApplication):
    pass

# def notify_contract_update(contract: Contract):
#     pass

# def notify_product_update(product: Product):
#     pass


# def notify_offer_update(offer: Offer):
#     pass

def notify_bid_update(bid: Bid):
    pass        






