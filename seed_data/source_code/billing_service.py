"""
Fictional Training Data - Billing Service Module
This is a prototype service for healthcare documentation automation training.
NOT FOR PRODUCTION USE.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class ClaimStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    REQUIRES_APPROVAL = "requires_approval"  # Manual approval required on UI
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class BillingClaim(BaseModel):
    claim_id: str
    patient_id: str
    procedure_codes: List[str]
    amount: Decimal
    status: ClaimStatus
    created_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    denial_reason: Optional[str] = None


class BillingService:
    """Service for managing billing claims and insurance submissions."""

    APPROVAL_THRESHOLD = Decimal("5000.00")  # Claims over this require manual approval

    def __init__(self):
        self._claims: dict[str, BillingClaim] = {}

    def create_claim(
        self,
        patient_id: str,
        procedure_codes: List[str],
        amount: Decimal
    ) -> BillingClaim:
        """Create a new billing claim."""
        claim = BillingClaim(
            claim_id=f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            patient_id=patient_id,
            procedure_codes=procedure_codes,
            amount=amount,
            status=ClaimStatus.PENDING,
            created_at=datetime.now()
        )
        self._claims[claim.claim_id] = claim
        return claim

    def submit_claim(self, claim_id: str) -> BillingClaim:
        """Submit claim for processing."""
        if claim_id not in self._claims:
            raise ValueError(f"Claim {claim_id} not found")

        claim = self._claims[claim_id]

        # Check if claim requires manual approval
        if claim.amount > self.APPROVAL_THRESHOLD:
            claim.status = ClaimStatus.REQUIRES_APPROVAL
        else:
            claim.status = ClaimStatus.SUBMITTED
            claim.submitted_at = datetime.now()

        return claim

    def approve_claim(self, claim_id: str, approver_id: str) -> BillingClaim:
        """Manually approve a claim requiring approval."""
        if claim_id not in self._claims:
            raise ValueError(f"Claim {claim_id} not found")

        claim = self._claims[claim_id]

        if claim.status != ClaimStatus.REQUIRES_APPROVAL:
            raise ValueError(f"Claim {claim_id} does not require approval")

        claim.status = ClaimStatus.APPROVED
        claim.approved_at = datetime.now()
        claim.approved_by = approver_id

        return claim

    def get_claims_requiring_approval(self) -> List[BillingClaim]:
        """Get all claims pending manual approval."""
        return [
            c for c in self._claims.values()
            if c.status == ClaimStatus.REQUIRES_APPROVAL
        ]

    def process_payment(self, claim_id: str, amount: Decimal) -> BillingClaim:
        """Record payment for an approved claim."""
        if claim_id not in self._claims:
            raise ValueError(f"Claim {claim_id} not found")

        claim = self._claims[claim_id]

        if claim.status != ClaimStatus.APPROVED:
            raise ValueError(f"Claim {claim_id} must be approved before payment")

        # Simulate payment processing
        claim.status = ClaimStatus.PAID
        return claim


# NOTE: Historical claims older than 7 years should be archived
# This is mentioned in requirements but not yet implemented
