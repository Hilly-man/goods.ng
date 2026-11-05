from enum import StrEnum as _S


class UserRole(_S):
    USER = "user"  # buyer; becomes a seller by creating a seller profile
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class AdminPermission(_S):
    USERS_MANAGE = "users.manage"
    SELLERS_VERIFY = "sellers.verify"
    LISTINGS_MODERATE = "listings.moderate"
    CATEGORIES_MANAGE = "categories.manage"
    SUBSCRIPTIONS_MANAGE = "subscriptions.manage"
    ORDERS_VIEW = "orders.view"
    PAYMENTS_VIEW = "payments.view"
    DISPUTES_RESOLVE = "disputes.resolve"
    REFUNDS_REQUEST = "refunds.request"
    REFUNDS_APPROVE = "refunds.approve"
    BNPL_VIEW = "bnpl.view"
    REVIEWS_MODERATE = "reviews.moderate"
    REPORTS_MANAGE = "reports.manage"
    SETTINGS_MANAGE = "settings.manage"
    PROMOTIONS_MANAGE = "promotions.manage"
    AUDIT_VIEW = "audit.view"
    ANALYTICS_VIEW = "analytics.view"


class OtpPurpose(_S):
    PHONE_VERIFY = "phone_verify"
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"


class VerificationLevel(_S):
    UNVERIFIED = "unverified"
    PHONE = "phone_verified"
    IDENTITY = "identity_verified"
    BUSINESS = "business_verified"


class VerificationStatus(_S):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SubscriptionStatus(_S):
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ProductCondition(_S):
    BRAND_NEW = "brand_new"
    FOREIGN_USED = "foreign_used"
    NIGERIAN_USED = "nigerian_used"
    REFURBISHED = "refurbished"


class ProductStatus(_S):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    SOLD = "sold"
    INACTIVE = "inactive"
    REJECTED = "rejected"


class ContactChannel(_S):
    WHATSAPP = "whatsapp"
    PHONE = "phone"
    CHAT = "chat"


class NegotiationStatus(_S):
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    CONVERTED = "converted"  # agreed price used in an order


class OfferStatus(_S):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COUNTERED = "countered"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


class OfferParty(_S):
    BUYER = "buyer"
    SELLER = "seller"


class PaymentMethod(_S):
    FULL = "full"
    BNPL = "bnpl"


class EscrowStatus(_S):
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_CONFIRMED = "payment_confirmed"
    FUNDS_SAFEGUARDED = "funds_safeguarded"
    AWAITING_SELLER = "awaiting_seller"
    PROCESSING = "processing"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    AWAITING_BUYER_CONFIRMATION = "awaiting_buyer_confirmation"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentStatus(_S):
    INITIALIZED = "initialized"
    SUCCESS = "success"
    FAILED = "failed"
    ABANDONED = "abandoned"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentPurpose(_S):
    ORDER = "order"
    SUBSCRIPTION = "subscription"
    BNPL_DOWN_PAYMENT = "bnpl_down_payment"
    BNPL_INSTALLMENT = "bnpl_installment"
    PROMOTION = "promotion"


class RefundStatus(_S):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class DisputeReason(_S):
    NOT_RECEIVED = "not_received"
    NOT_AS_DESCRIBED = "not_as_described"
    DAMAGED = "damaged"
    WRONG_ITEM = "wrong_item"
    SELLER_NON_FULFILMENT = "seller_non_fulfilment"
    DELIVERY_ISSUE = "delivery_issue"
    BUYER_REFUSES_CONFIRMATION = "buyer_refuses_confirmation"
    FRAUDULENT_CLAIM = "fraudulent_claim"
    OTHER = "other"


class DisputeStatus(_S):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED_BUYER = "resolved_buyer"  # refund buyer
    RESOLVED_SELLER = "resolved_seller"  # release to seller
    CANCELLED = "cancelled"


class DeliveryStatus(_S):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"


class ReviewStatus(_S):
    PUBLISHED = "published"
    HIDDEN = "hidden"


class BnplStatus(_S):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DECLINED = "declined"
    ACCEPTED = "accepted"  # buyer accepted terms
    ACTIVE = "active"  # down payment made, financing disbursed
    COMPLETED = "completed"
    DEFAULTED = "defaulted"
    CANCELLED = "cancelled"


class InstallmentStatus(_S):
    SCHEDULED = "scheduled"
    PAID = "paid"
    OVERDUE = "overdue"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LedgerAccountType(_S):
    ASSET = "asset"
    LIABILITY = "liability"
    REVENUE = "revenue"
    EXPENSE = "expense"


class EntryDirection(_S):
    DEBIT = "debit"
    CREDIT = "credit"


class ReportStatus(_S):
    OPEN = "open"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class PromotionStatus(_S):
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
