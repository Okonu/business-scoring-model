# BASEPOINT / FSS Backend Entity Relationship Diagram

## Overview
This ERD represents the complete database schema for the BASEPOINT Enterprise Business Suite (FSS) backend, powered by `biggie_api`. It covers the core POS operations, multi-shop & multi-tenancy management, table service, customer loyalty & subscriptions, inventory, double-entry accounting, CRM & lead acquisition, document management & e-signatures, omnichannel WhatsApp messaging, Dala real-estate property management, and Bandu HR & payroll.

## ERD Diagram (Mermaid Syntax)

```mermaid
erDiagram
    %% Core Multi-Tenant Entities
    Tenant {
        ObjectId _id PK
        String name
        String email UK
        String phone
        String business_size
        String db_name UK
        String tenant_code UK
        ObjectId subscription_id FK
        ObjectId business_type_id FK
        Boolean is_vat_enabled
        String vat_pricing_mode
        Number vat_standard_rate
        String subscription_status
        String subscription_cycle
        Date createdAt
        Date updatedAt
    }

    Shop {
        ObjectId _id PK
        String name UK
        Object location
        String pos_mode
        Boolean staff_earning_enabled
        Boolean require_payment_before_print
        Object print_settings
        Object hotel_settings
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    ShopLocation {
        String address
        String place_id
        Number lat
        Number lng
        String city
        String country
        String formatted_address
        String maps_url
    }

    User {
        ObjectId _id PK
        String fullname
        String username UK
        String email UK
        Number phone
        Number idNumber UK
        String pin UK
        String hashedPin
        Boolean isAdmin
        String thumbnail
        String status
        ObjectId shop_id FK
        ObjectId role_id FK
        ObjectId tenant_id FK
        Array categories_id FK
        Date createdAt
        Date updatedAt
    }

    %% Customer Management
    Customer {
        ObjectId _id PK
        String customer_name
        String code UK
        String email
        Number phone UK
        String location
        String kra_pin
        Number payment_terms
        Number credit_limit
        ObjectId account_id FK
        Number opening_balance
        Number current_balance
        Boolean is_active
        String notes
        String source
        String project
        ObjectId converted_from FK
        ObjectId campaign_id FK
        ObjectId assigned_to FK
        String lifecycle_stage
        Date first_purchase_date
        Date last_purchase_date
        Number lifetime_value
        ObjectId created_by FK
        ObjectId updated_by FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    %% CRM Module
    Lead {
        ObjectId _id PK
        String entity_type
        String lead_name
        String company_name
        String contact_person
        String email
        String phone
        String website
        String stage
        String source
        String project
        Number estimated_value
        String currency
        Number probability
        Date expected_close_date
        ObjectId assigned_to FK
        ObjectId campaign_id FK
        ObjectId customer_id FK
        Date converted_at
        ObjectId converted_by FK
        String lost_reason
        String lost_to_competitor
        Date next_follow_up
        Date last_contacted_at
        String notes
        Array tags
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    Campaign {
        ObjectId _id PK
        String name
        String description
        String type
        String status
        Date start_date
        Date end_date
        Number budget
        Number actual_spend
        String currency
        Number target_leads
        Number target_conversions
        Number target_revenue
        ObjectId shop_id FK
        ObjectId tenant_id FK
        ObjectId created_by FK
        Date createdAt
        Date updatedAt
    }

    LeadActivity {
        ObjectId _id PK
        String activity_type
        String title
        String description
        Date due_date
        Date completed_at
        String status
        ObjectId lead_id FK
        ObjectId assigned_to FK
        ObjectId created_by FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    %% Document Management & E-Signatures
    Document {
        ObjectId _id PK
        String name
        String original_name
        String file_type
        String mime_type
        Number file_size
        String s3_url
        String local_path
        String document_type
        String status
        String signature_status
        ObjectId parent_folder_id FK
        String path
        ObjectId lead_id FK
        ObjectId customer_id FK
        ObjectId property_id FK
        ObjectId unit_id FK
        ObjectId lease_id FK
        ObjectId invoice_id FK
        ObjectId purchase_order_id FK
        ObjectId sale_id FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        ObjectId created_by FK
        ObjectId updated_by FK
        String public_share_token
        Date public_share_expires_at
        Boolean public_share_revoked
        Date createdAt
        Date updatedAt
    }

    DocumentSignature {
        ObjectId _id PK
        ObjectId document_id FK
        ObjectId user_id FK
        String signer_name
        String signer_email
        String signer_role
        String signature_url
        String status
        Date signed_at
        Date createdAt
        Date updatedAt
    }

    %% Omnichannel & WhatsApp Messaging
    WhatsappChannel {
        ObjectId _id PK
        String channel_name
        String phone_number UK
        String phone_number_id
        String waba_id
        String provider
        String status
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    Conversation {
        ObjectId _id PK
        ObjectId channel_id FK
        String external_contact_id
        String external_contact_name
        String external_contact_phone
        String status
        ObjectId customer_id FK
        ObjectId lead_id FK
        ObjectId assigned_to FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date last_message_at
        Date createdAt
        Date updatedAt
    }

    Message {
        ObjectId _id PK
        ObjectId conversation_id FK
        String direction
        String message_type
        String content
        String status
        String media_url
        String meta_message_id
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date timestamp
        Date createdAt
        Date updatedAt
    }

    %% Product & Category Management
    Category {
        ObjectId _id PK
        String name
        ObjectId shop_id FK
        ObjectId sub_category_id FK
        Date createdAt
        Date updatedAt
    }

    SubCategory {
        ObjectId _id PK
        String name
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    Product {
        ObjectId _id PK
        String name
        String code UK
        String desc
        Number quantity
        Number price
        Number min_viable_quantity
        Boolean activateInventory
        String vat_type
        String thumbnail
        ObjectId category_id FK
        ObjectId shop_id FK
        Array addons_id FK
        Date createdAt
        Date updatedAt
    }

    Addons {
        ObjectId _id PK
        String name
        Number price
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    Modifiers {
        ObjectId _id PK
        String name
        Array options
        ObjectId product_id FK
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    %% Table & Area Management
    Table {
        ObjectId _id PK
        String name UK
        Boolean isOccupied
        ObjectId shop_id FK
        ObjectId locatedAt_id FK
        ObjectId cart_id FK
        Date createdAt
        Date updatedAt
    }

    TableLocation {
        ObjectId _id PK
        String name
        ObjectId shop_id FK
        Boolean isDisabled
        Date createdAt
        Date updatedAt
    }

    %% Cart & Order Management
    Cart {
        ObjectId _id PK
        String order_no UK
        String status
        Boolean pending_print
        Boolean void
        Number discount
        String discount_type
        Number tip_amount
        String tip_type
        String client_name
        String client_pin
        String payment_type
        Boolean use_subscription
        ObjectId table_id FK
        ObjectId created_by FK
        ObjectId served_by FK
        ObjectId shop_id FK
        ObjectId customer_id FK
        ObjectId subscription_id FK
        Date createdAt
        Date updatedAt
    }

    CartItem {
        ObjectId _id PK
        Number quantity
        Number price
        ObjectId cart_id FK
        ObjectId product_id FK
        Date createdAt
        Date updatedAt
    }

    Order {
        ObjectId _id PK
        String order_no UK
        String order_type
        String order_status
        String payment_status
        Number order_amount
        Number total_cart_amount
        Number discount_amount
        Number subtotal
        Number total_vat_amount
        Mixed vat_breakdown
        String customer_name
        String customer_phone
        String customer_email
        ObjectId cart_id FK
        ObjectId shop_id FK
        ObjectId table_id FK
        ObjectId customer_id FK
        ObjectId subscription_id FK
        ObjectId package_id FK
        ObjectId updated_by FK
        ObjectId served_by FK
        Array method_ids FK
        ObjectId journal_entry_id FK
        Date createdAt
        Date updatedAt
    }

    OrderItem {
        ObjectId _id PK
        Number quantity
        Number price
        ObjectId order_id FK
        ObjectId product_id FK
        Date createdAt
        Date updatedAt
    }

    %% Invoice Management
    Invoice {
        ObjectId _id PK
        String order_no
        String source
        String direction
        String status
        Number grand_total
        Number discount_amount
        Number subtotal
        Number total_vat_amount
        Mixed vat_breakdown
        String vat_pricing_mode
        Number vat_standard_rate
        Number amount_paid
        Number amount_due
        String currency
        Date issue_date
        Date due_date
        Date paid_date
        String notes
        String terms
        String internal_notes
        Boolean is_converted_quote
        Date converted_at
        ObjectId cart_id FK
        ObjectId shop_id FK
        ObjectId table_id FK
        ObjectId customer_id FK
        ObjectId supplier_id FK
        ObjectId updated_by FK
        ObjectId served_by FK
        ObjectId created_by FK
        ObjectId journal_entry_id FK
        ObjectId order_id FK
        ObjectId payment_id FK
        Array payment_ids FK
        ObjectId quote_id FK
        ObjectId converted_by FK
        Date createdAt
        Date updatedAt
    }

    InvoiceItem {
        ObjectId _id PK
        Number quantity
        Number price
        Number total
        String description
        ObjectId invoice_id FK
        ObjectId product_id FK
        Date createdAt
        Date updatedAt
    }

    %% Payment Management
    PaymentMethod {
        ObjectId _id PK
        String name
        ObjectId shop_id FK
        ObjectId account_id FK
        String account_code
        String account_name
        Date createdAt
        Date updatedAt
    }

    OrderPayment {
        ObjectId _id PK
        Number amount
        String payment_type
        Number change_amount
        ObjectId order_id FK
        ObjectId invoice_id FK
        ObjectId payment_method_id FK
        ObjectId customer_id FK
        Date createdAt
        Date updatedAt
    }

    PaymentDetails {
        ObjectId _id PK
        Mixed payment_data
        ObjectId order_payment_id FK
        Date createdAt
        Date updatedAt
    }

    %% Subscription Management
    Subscription {
        ObjectId _id PK
        String name
        String description
        Number price
        String billing_cycle
        Boolean is_active
        Date createdAt
        Date updatedAt
    }

    CustomerSubscription {
        ObjectId _id PK
        Date start_date
        Date end_date
        String status
        Number visits_remaining
        ObjectId customer_id FK
        ObjectId subscription_id FK
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    Package {
        ObjectId _id PK
        String name
        String description
        Number price
        Number duration_days
        Number total_visits
        Boolean is_active
        ObjectId subscription_id FK
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    SubscriptionVisitLog {
        ObjectId _id PK
        Date visit_date
        String notes
        ObjectId customer_subscription_id FK
        ObjectId order_id FK
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    %% Inventory Management
    ProductInventory {
        ObjectId _id PK
        String name
        String code
        String thumbnail
        Number quantity
        Number price
        Number supplier_price
        String desc
        Number min_viable_quantity
        String usage_type
        String status
        String vat_type
        String barcode
        String location
        Object dimensions
        Object weight
        String manufacturer
        ObjectId shop_id FK
        ObjectId unit_id FK
        ObjectId subcategory_id FK
        ObjectId category_id FK
        ObjectId supplier_id FK
        Date createdAt
        Date updatedAt
    }

    PurchaseOrder {
        ObjectId _id PK
        String order_no UK
        String status
        Number total_amount
        Date order_date
        Date expected_date
        ObjectId supplier_id FK
        ObjectId shop_id FK
        ObjectId created_by FK
        Date createdAt
        Date updatedAt
    }

    PurchaseOrderItem {
        ObjectId _id PK
        Number quantity
        Number unit_price
        Number total_price
        ObjectId purchase_order_id FK
        ObjectId product_id FK
        Date createdAt
        Date updatedAt
    }

    Delivery {
        ObjectId _id PK
        String delivery_no UK
        String status
        Date delivery_date
        ObjectId purchase_order_id FK
        ObjectId shop_id FK
        ObjectId received_by FK
        Date createdAt
        Date updatedAt
    }

    DeliveryItem {
        ObjectId _id PK
        Number quantity_delivered
        Number quantity_received
        ObjectId delivery_id FK
        ObjectId purchase_order_item_id FK
        ObjectId product_id FK
        Date createdAt
        Date updatedAt
    }

    Transfer {
        ObjectId _id PK
        String transfer_no UK
        String status
        Date transfer_date
        ObjectId from_shop_id FK
        ObjectId to_shop_id FK
        ObjectId created_by FK
        Date createdAt
        Date updatedAt
    }

    TransferItem {
        ObjectId _id PK
        Number quantity
        ObjectId transfer_id FK
        ObjectId product_id FK
        Date createdAt
        Date updatedAt
    }

    %% Property Management (Dala Module)
    Property {
        ObjectId _id PK
        String name
        String code UK
        String property_type
        String category
        String purpose
        String description
        Object location
        Number total_units
        ObjectId shop_id FK
        ObjectId tenant_id FK
        ObjectId created_by FK
        Date createdAt
        Date updatedAt
    }

    Unit {
        ObjectId _id PK
        String unit_number
        String unit_type
        String status
        Number rent_amount
        Number sale_price
        ObjectId property_id FK
        ObjectId block_id FK
        ObjectId floor_id FK
        ObjectId current_lease_id FK
        ObjectId customer_id FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    Lease {
        ObjectId _id PK
        String lease_number UK
        String leaseType
        Date start_date
        Date end_date
        Number rent_amount
        Number deposit_amount
        String billing_cycle
        String status
        ObjectId property_id FK
        ObjectId unit_id FK
        ObjectId occupantId FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        ObjectId created_by FK
        Date createdAt
        Date updatedAt
    }

    PropertyTenant {
        ObjectId _id PK
        String fullName
        String email
        String phone
        String idType
        String idNumber
        String kraPin
        String occupantType
        String companyName
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    RentInvoice {
        ObjectId _id PK
        String invoice_number UK
        Number amount
        Number balance_due
        Date billing_period_start
        Date billing_period_end
        Date due_date
        String status
        ObjectId lease_id FK
        ObjectId property_id FK
        ObjectId unit_id FK
        ObjectId occupantId FK
        ObjectId journal_entry_id FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    RentPayment {
        ObjectId _id PK
        String receipt_number UK
        Number amount
        String payment_method
        Date payment_date
        ObjectId rent_invoice_id FK
        ObjectId lease_id FK
        ObjectId occupantId FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    MaintenanceTicket {
        ObjectId _id PK
        String ticket_number UK
        String title
        String description
        String priority
        String status
        ObjectId property_id FK
        ObjectId unit_id FK
        ObjectId reported_by FK
        ObjectId assigned_to FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    %% HR & Payroll (Bandu Module)
    Employee {
        ObjectId _id PK
        String employee_number UK
        String employment_type
        String job_title
        String employment_status
        Date hire_date
        Number basic_salary
        ObjectId user_id FK
        ObjectId department_id FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    Payroll {
        ObjectId _id PK
        String payroll_period
        Number month
        Number year
        Number total_gross
        Number total_net
        Number total_deductions
        String status
        ObjectId shop_id FK
        ObjectId tenant_id FK
        ObjectId approved_by FK
        Date createdAt
        Date updatedAt
    }

    Payslip {
        ObjectId _id PK
        Number basic_salary
        Number gross_pay
        Number total_deductions
        Number net_pay
        String status
        ObjectId payroll_id FK
        ObjectId employee_id FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    Leave {
        ObjectId _id PK
        String leave_type
        Date start_date
        Date end_date
        Number days
        String status
        String reason
        ObjectId employee_id FK
        ObjectId approved_by FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    %% Accounting & Fixed Assets Module
    ChartOfAccount {
        ObjectId _id PK
        String account_code UK
        String account_name
        String account_type
        String description
        Boolean is_active
        ObjectId parent_id FK
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    JournalEntry {
        ObjectId _id PK
        String entry_no UK
        Date entry_date
        String description
        String reference_type
        ObjectId reference_id
        ObjectId shop_id FK
        ObjectId created_by FK
        Date createdAt
        Date updatedAt
    }

    JournalEntryLine {
        ObjectId _id PK
        Number debit_amount
        Number credit_amount
        String memo
        ObjectId journal_entry_id FK
        ObjectId account_id FK
        Date createdAt
        Date updatedAt
    }

    Asset {
        ObjectId _id PK
        String asset_no UK
        String asset_name
        String asset_category
        String asset_type
        Date acquisition_date
        Number purchase_cost
        Number salvage_value
        Number useful_life_years
        String depreciation_method
        Number accumulated_depreciation
        Number net_book_value
        String status
        ObjectId custodian FK
        ObjectId shop_id FK
        ObjectId tenant_id FK
        Date createdAt
        Date updatedAt
    }

    %% User Management & RBAC
    RoleType {
        ObjectId _id PK
        String name UK
        String description
        Date createdAt
        Date updatedAt
    }

    Role {
        ObjectId _id PK
        ObjectId role_type_id FK
        Array permissions_id FK
        Date createdAt
        Date updatedAt
    }

    Permission {
        ObjectId _id PK
        String name UK
        String description
        String resource
        String action
        Date createdAt
        Date updatedAt
    }

    %% Other Supporting Entities
    BusinessType {
        ObjectId _id PK
        String name UK
        String description
        Date createdAt
        Date updatedAt
    }

    UOM {
        ObjectId _id PK
        String name UK
        String abbreviation
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    Printer {
        ObjectId _id PK
        String name
        String type
        String connection_string
        Boolean is_default
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    Notification {
        ObjectId _id PK
        String title
        String message
        String type
        Boolean is_read
        ObjectId user_id FK
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    FAQ {
        ObjectId _id PK
        String question
        String answer
        Boolean is_active
        ObjectId category_id FK
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    FAQCategory {
        ObjectId _id PK
        String name
        ObjectId shop_id FK
        Date createdAt
        Date updatedAt
    }

    %% Relationships
    Tenant ||--o{ Shop : "has many"
    Tenant ||--o{ User : "has many"
    Tenant ||--o{ Customer : "has many"
    Tenant ||--o{ Lead : "has many"
    Tenant ||--o{ Document : "has many"
    Tenant ||--o{ WhatsappChannel : "has many"
    Tenant ||--o{ Property : "has many"
    Tenant ||--o{ Employee : "has many"
    Tenant ||--o{ Payroll : "has many"
    
    Shop ||--o{ User : "has many"
    Shop ||--o{ Customer : "has many"
    Shop ||--o{ Category : "has many"
    Shop ||--o{ SubCategory : "has many"
    Shop ||--o{ Product : "has many"
    Shop ||--o{ Addons : "has many"
    Shop ||--o{ Modifiers : "has many"
    Shop ||--o{ Table : "has many"
    Shop ||--o{ TableLocation : "has many"
    Shop ||--o{ ShopLocation : "embedded in"
    Shop ||--o{ Cart : "has many"
    Shop ||--o{ Order : "has many"
    Shop ||--o{ Invoice : "has many"
    Shop ||--o{ PaymentMethod : "has many"
    Shop ||--o{ CustomerSubscription : "has many"
    Shop ||--o{ Package : "has many"
    Shop ||--o{ ProductInventory : "has many"
    Shop ||--o{ PurchaseOrder : "has many"
    Shop ||--o{ Delivery : "has many"
    Shop ||--o{ Transfer : "has many"
    Shop ||--o{ ChartOfAccount : "has many"
    Shop ||--o{ JournalEntry : "has many"
    Shop ||--o{ Asset : "has many"
    Shop ||--o{ Notification : "has many"
    Shop ||--o{ FAQ : "has many"
    Shop ||--o{ FAQCategory : "has many"
    Shop ||--o{ UOM : "has many"
    Shop ||--o{ Printer : "has many"
    Shop ||--o{ Lead : "has many"
    Shop ||--o{ Campaign : "has many"
    Shop ||--o{ Document : "has many"
    Shop ||--o{ WhatsappChannel : "has many"
    Shop ||--o{ Property : "has many"
    Shop ||--o{ Employee : "has many"

    User }o--|| Role : "belongs to"
    User ||--o{ Cart : "creates"
    User ||--o{ Order : "serves"
    User ||--o{ Invoice : "creates"
    User ||--o{ Notification : "receives"
    User ||--o{ Lead : "assigned to"
    User ||--o{ LeadActivity : "assigned to"
    User ||--o{ Conversation : "assigned to"
    User ||--o| Employee : "profile linked to"

    Customer ||--o{ Order : "places"
    Customer ||--o{ Invoice : "has"
    Customer ||--o{ CustomerSubscription : "has"
    Customer ||--o{ OrderPayment : "makes"
    Customer ||--o{ Document : "has"
    Customer ||--o{ Conversation : "initiates"

    Lead ||--o{ LeadActivity : "has"
    Lead ||--o| Customer : "converts to"
    Lead ||--o{ Document : "has"
    Lead ||--o{ Conversation : "linked with"

    Campaign ||--o{ Lead : "generates"
    Campaign ||--o{ Customer : "generates"

    Document ||--o{ DocumentSignature : "requires"

    WhatsappChannel ||--o{ Conversation : "routes"
    Conversation ||--o{ Message : "contains"

    Category ||--o{ Product : "contains"
    Category }o--|| SubCategory : "belongs to"
    Category ||--o{ FAQ : "categorizes"

    ProductInventory ||--o{ CartItem : "contains"
    ProductInventory ||--o{ OrderItem : "in"
    ProductInventory ||--o{ InvoiceItem : "in"
    ProductInventory ||--o{ PurchaseOrderItem : "ordered"
    ProductInventory ||--o{ DeliveryItem : "delivered"
    ProductInventory ||--o{ TransferItem : "transferred"

    Table ||--o{ Cart : "has"
    Table ||--o{ Order : "served at"
    Table }o--|| TableLocation : "located at"

    Cart ||--o{ CartItem : "contains"
    Cart ||--|| Order : "becomes"
    Cart ||--o| Invoice : "generates"

    Order ||--o{ OrderItem : "contains"
    Order ||--o| Invoice : "generates"
    Order ||--o{ OrderPayment : "paid for"
    Order ||--o{ SubscriptionVisitLog : "logs"

    Invoice ||--o{ InvoiceItem : "contains"
    Invoice ||--o{ OrderPayment : "paid for"
    Invoice ||--o{ JournalEntry : "posts to"

    PaymentMethod ||--o{ OrderPayment : "used for"
    PaymentMethod }o--|| ChartOfAccount : "posts to"

    Subscription ||--o{ CustomerSubscription : "creates"
    Subscription ||--o{ Package : "offers"

    CustomerSubscription ||--o{ SubscriptionVisitLog : "logs"
    CustomerSubscription ||--o{ Order : "enables"

    Package ||--o{ CustomerSubscription : "used in"
    Package ||--o{ Order : "applied to"

    PurchaseOrder ||--o{ PurchaseOrderItem : "contains"
    PurchaseOrder ||--o| Delivery : "delivers"

    Delivery ||--o{ DeliveryItem : "contains"
    Delivery }o--|| PurchaseOrder : "from"

    Transfer ||--o{ TransferItem : "contains"

    Property ||--o{ Unit : "contains"
    Property ||--o{ Lease : "has"
    Property ||--o{ MaintenanceTicket : "has"
    Property ||--o{ Document : "associated with"

    Unit ||--o{ Lease : "leased under"
    Unit ||--o{ MaintenanceTicket : "requires"

    PropertyTenant ||--o{ Lease : "signs"
    PropertyTenant ||--o{ RentInvoice : "billed"
    PropertyTenant ||--o{ RentPayment : "pays"

    Lease ||--o{ RentInvoice : "generates"
    RentInvoice ||--o{ RentPayment : "settled by"
    RentInvoice ||--o{ JournalEntry : "posts to"

    Employee ||--o{ Payslip : "receives"
    Employee ||--o{ Leave : "requests"
    Payroll ||--o{ Payslip : "contains"

    ChartOfAccount ||--o{ JournalEntryLine : "used in"
    ChartOfAccount }o--|| ChartOfAccount : "parent of"

    JournalEntry ||--o{ JournalEntryLine : "contains"
    JournalEntry }o--|| Order : "references"
    JournalEntry }o--|| Invoice : "references"

    Asset ||--o{ ChartOfAccount : "depreciates to"

    RoleType ||--o{ Role : "defines"
    Role ||--o{ User : "assigned to"
    Role ||--o{ Permission : "has"

    Permission ||--o{ Role : "granted to"

    BusinessType ||--o{ Tenant : "categorizes"

    FAQCategory ||--o{ FAQ : "contains"
```

## Key Changes in Latest Update

### Cart & Bill Printing Controls
- Added `pending_print: Boolean` to **Cart**: When `require_payment_before_print` is active in the shop settings, the cart remains in `"Open"` status after payment with `pending_print: true` until the bill is physically printed and the cart is explicitly closed via the `/carts/:id/close-after-print` endpoint, ensuring the table remains occupied.
- Added `require_payment_before_print: Boolean` to **Shop**: Configuration toggle allowing business owners to mandate that payment be completed before a bill can be printed.
- Added `staff_earning_enabled: Boolean` to **Shop**: Configuration toggle for calculating and tracking staff commissions per order based on `served_by`.

### CRM Pipeline & Customer Traceability
- **Lead** entity introduced with full lifecycle stages (`new`, `contacted`, `qualified`, `proposal`, `negotiation`, `won`, `lost`, `disqualified`).
- Free-form `source` field on **Lead** and **Customer**: Replaced rigid enums with free-form strings, enabling tenants to register custom lead sources while preserving defaults in the UI.
- `project` association: Added `project` string to both **Lead** and **Customer** to bind acquisition pipelines to specific real-estate developments (Dala portfolio properties) or custom project identifiers.
- Customer Conversion linkage: Added `converted_from` ObjectId (referencing `Lead`) on **Customer** to maintain full traceability across the conversion funnel.
- Linked **Campaign** (`campaign_id`), **LeadActivity**, and assigned sales agents (`assigned_to`) across leads and customer records.

### Document Management & Public E-Signatures
- **Document** entity schema added to ERD with hierarchical folder paths (`path`, `parent_folder_id`) and multi-entity attachments (`lead_id`, `customer_id`, `property_id`, `unit_id`, `lease_id`, `invoice_id`, `purchase_order_id`, `sale_id`).
- Added `public_share` subdocument to **Document**: Enables tokenized, shareable public signing URLs (`token`, `expires_at`, `created_by`, `revoked`, `signer_name`, `signer_email`, `signed_at`, `last_accessed_at`) allowing external clients to sign contracts or quotes without tenant authentication.
- Added **DocumentSignature** entity tracking signer status, signatures, and timestamps.

### Omnichannel WhatsApp Messaging
- Integrated **WhatsappChannel**, **Conversation**, and **Message** entities into the schema.
- Added `"pending_dispatch"` status to `Conversation` status enum (`"open"`, `"pending"`, `"pending_dispatch"`, `"resolved"`, `"closed"`).
- Added `"call"` message type to `Message` (`"text"`, `"image"`, `"document"`, `"audio"`, `"video"`, `"sticker"`, `"location"`, `"contacts"`, `"reaction"`, `"template"`, `"order"`, `"call"`, `"unsupported"`) to track voice/video call events.

### Inventory Enhancements
- **ProductInventory**: Product code (`code`) now defaults to auto-generated unique codes (`generateUniqueCode`) upon insert and during Excel imports.
- Explicit `usage_type` ('selling', 'internal', 'both') for distinguishing between sellable goods and raw restaurant/operational supplies.

### Dala Real Estate & Property Management
- Schema coverage for **Property**, **Unit**, **Lease**, **PropertyTenant**, **RentInvoice**, **RentPayment**, and **MaintenanceTicket**.
- Automated double-entry integration: Rent invoices post to `JournalEntry` and settle through `RentPayment`.

### Bandu HR & Payroll
- Schema coverage for **Employee**, **Payroll**, **Payslip**, and **Leave**.
- Integrated with `User` authentication and automated ledger debit/credit postings.

### Fixed Asset Accounting
- Added **Asset** register entity with depreciation calculation models (`straight_line`, `declining_balance`, `double_declining`), tracking accumulated depreciation and net book value linked to **ChartOfAccount**.

## Key Relationships Summary

### Multi-Tenant Architecture
- **Tenant** is the master root entity with database-per-tenant isolation.
- **Shops** operate as business units / locations under a Tenant.
- **Users**, **Customers**, **Products**, **Orders**, and **Leases** are all scoped to `tenant_id` and `shop_id`.

### Core POS Flow
1. **Cart** → **Order** → **Invoice** → **Payment**
2. **Table** and **TableLocation** handle dine-in seating and room orders.
3. If `require_payment_before_print` is true, Cart transitions to `pending_print: true` after payment until bill generation is finalized.

### Lead & CRM Acquisition Funnel
1. **Campaign** attracts prospective clients into **Lead** entries.
2. Sales activities and follow-ups logged via **LeadActivity**.
3. Won leads convert into **Customer** records with `converted_from` back-references and preserved `project` / `source` metadata.

### Omnichannel Communication Loop
1. Customers or leads contact business via **WhatsappChannel**.
2. A **Conversation** is mapped to existing **Customer** or **Lead** via phone number matching.
3. Inbound/outbound **Message** records preserve chat history, media, templates, orders, and call events.

### Document Generation & E-Signing
1. Invoices, sales agreements, and leases generate **Document** records.
2. Signers sign internally via `DocumentSignature` or externally via public tokenized link (`public_share`).

### Property & Lease Management (Dala)
1. **Property** contains **Units** (and optional blocks/floors).
2. **PropertyTenant** enters a **Lease** for a designated unit.
3. Recurring **RentInvoice** entries are issued and paid via **RentPayment**, feeding directly into the double-entry accounting ledger (**JournalEntry**).

### Financial & Accounting Integration
1. Every sale, purchase delivery, rent invoice, and payroll run automatically writes balanced debits and credits via **JournalEntryLine** to **ChartOfAccount**.
2. **Asset** depreciation periodically posts depreciation expenses against accumulated depreciation asset accounts.

## Notes on Implementation

1. **Multi-tenancy**: High security database-per-tenant isolation managed dynamically by connection poolers in `biggie_api`.
2. **Soft Deletes**: Entities use flags (`is_active`, `is_deleted`, `status`) to retain audit trails and historic reporting integrity.
3. **Audit Trails**: Creation and modifications tracked with `created_by`, `updated_by`, `createdAt`, and `updatedAt`.
4. **Fiscal Compliance**: Built-in support for VAT pricing modes, item tax rates, and Kenya Revenue Authority (KRA eTIMS / DigiTax) fiscal verification.
