# Custom migration for the SaaS template refactoring.
#
# This migration handles:
# 1. User model: AbstractBaseUser fields, rename password_hash -> password
# 2. SubscriptionPlan: rename domain-specific fields to generic names
# 3. Subscription: add provider_subscription_id
# 4. ForeignKey on_delete changes across all models
# 5. New models: ModerationQueue, ModerationAppeal, Post, Comment,
#    Coupon, CouponUsage, ReferralCode, ReferralTransaction

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0002_payment_user"),
    ]

    operations = [
        # =====================================================================
        # 1. User model changes (AbstractBaseUser integration)
        # =====================================================================
        # Rename password_hash -> password (same db_column='PasswordHash')
        migrations.RenameField(
            model_name="user",
            old_name="password_hash",
            new_name="password",
        ),
        # Add is_staff field
        migrations.AddField(
            model_name="user",
            name="is_staff",
            field=models.BooleanField(
                default=False,
                help_text="Designates whether the user can log into the admin site.",
            ),
        ),
        # Add is_superuser field
        migrations.AddField(
            model_name="user",
            name="is_superuser",
            field=models.BooleanField(
                default=False,
                help_text="Designates that this user has all permissions.",
            ),
        ),
        # Add last_login field (AbstractBaseUser expects this)
        migrations.AddField(
            model_name="user",
            name="last_login",
            field=models.DateTimeField(
                db_column="LastLogin",
                blank=True,
                null=True,
                help_text="Last login timestamp",
            ),
        ),
        # =====================================================================
        # 2. SubscriptionPlan field renames (domain-specific -> generic)
        # =====================================================================
        migrations.RenameField(
            model_name="subscriptionplan",
            old_name="max_exchanges",
            new_name="max_operations",
        ),
        migrations.RenameField(
            model_name="subscriptionplan",
            old_name="ai_predictions_enabled",
            new_name="feature_tier_1",
        ),
        migrations.RenameField(
            model_name="subscriptionplan",
            old_name="advanced_indicators_enabled",
            new_name="feature_tier_2",
        ),
        migrations.RenameField(
            model_name="subscriptionplan",
            old_name="portfolio_tracking",
            new_name="feature_tier_3",
        ),
        # =====================================================================
        # 3. Subscription: add provider_subscription_id
        # =====================================================================
        migrations.AddField(
            model_name="subscription",
            name="provider_subscription_id",
            field=models.CharField(
                db_column="ProviderSubscriptionID",
                max_length=255,
                blank=True,
                null=True,
                help_text="External subscription ID from the payment provider (Stripe, PayPal, etc.)",
            ),
        ),
        # =====================================================================
        # 4. ForeignKey on_delete changes
        #    (on_delete is Django-level; AlterField updates the migration state)
        # =====================================================================
        # Subscription.user: DO_NOTHING -> CASCADE
        migrations.AlterField(
            model_name="subscription",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="UserID",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="myapp.user",
                help_text="User who owns this subscription",
            ),
        ),
        # Subscription.subscription_plan: DO_NOTHING -> PROTECT
        migrations.AlterField(
            model_name="subscription",
            name="subscription_plan",
            field=models.ForeignKey(
                blank=True,
                db_column="SubscriptionPlanID",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="myapp.subscriptionplan",
                help_text="The subscription plan",
            ),
        ),
        # Payment.subscription: DO_NOTHING -> CASCADE
        migrations.AlterField(
            model_name="payment",
            name="subscription",
            field=models.ForeignKey(
                blank=True,
                db_column="SubscriptionID",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="myapp.subscription",
                help_text="Subscription this payment is for",
            ),
        ),
        # Payment.user: DO_NOTHING -> SET_NULL
        migrations.AlterField(
            model_name="payment",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="UserID",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="myapp.user",
                help_text="User who made this payment",
            ),
        ),
        # Renewal.subscription: DO_NOTHING -> CASCADE
        migrations.AlterField(
            model_name="renewal",
            name="subscription",
            field=models.ForeignKey(
                blank=True,
                db_column="SubscriptionID",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="myapp.subscription",
                help_text="Subscription that was renewed",
            ),
        ),
        # Renewal.renewed_by: DO_NOTHING -> SET_NULL
        migrations.AlterField(
            model_name="renewal",
            name="renewed_by",
            field=models.ForeignKey(
                blank=True,
                db_column="RenewedBy",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="myapp.user",
                help_text="User who processed the renewal",
            ),
        ),
        # Notification.user: DO_NOTHING -> CASCADE
        migrations.AlterField(
            model_name="notification",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="UserID",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="myapp.user",
                help_text="User who should receive this notification",
            ),
        ),
        # Event.user: DO_NOTHING -> CASCADE
        migrations.AlterField(
            model_name="event",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="UserID",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="myapp.user",
                help_text="User who owns this event",
            ),
        ),
        # Reminder.user: DO_NOTHING -> CASCADE
        migrations.AlterField(
            model_name="reminder",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="UserID",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="myapp.user",
                help_text="User who created this reminder",
            ),
        ),
        # ActivityLog.user: DO_NOTHING -> SET_NULL
        migrations.AlterField(
            model_name="activitylog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="UserID",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="myapp.user",
                help_text="User who performed the activity",
            ),
        ),
        # AuditLog.user: DO_NOTHING -> SET_NULL
        migrations.AlterField(
            model_name="auditlog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="UserID",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="myapp.user",
                help_text="User who performed the action",
            ),
        ),
        # MonthlyAnalytics.user: DO_NOTHING -> SET_NULL
        migrations.AlterField(
            model_name="monthlyanalytics",
            name="user",
            field=models.ForeignKey(
                blank=True,
                db_column="UserID",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="myapp.user",
                help_text="User for whom analytics are tracked (optional)",
            ),
        ),
        # =====================================================================
        # 5. New models
        # =====================================================================
        # Post model
        migrations.CreateModel(
            name="Post",
            fields=[
                ("is_active", models.IntegerField(blank=True, db_column="IsActive", default=1, null=True)),
                ("is_deleted", models.IntegerField(blank=True, db_column="IsDeleted", default=0, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="CreatedAt", null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_column="UpdatedAt", null=True)),
                ("created_by", models.IntegerField(blank=True, db_column="CreatedBy", null=True)),
                ("updated_by", models.IntegerField(blank=True, db_column="UpdatedBy", null=True)),
                ("content_text", models.TextField(db_column="ContentText")),
                ("content_status", models.CharField(db_column="ContentStatus", default="published", max_length=20)),
                ("moderated_at", models.DateTimeField(blank=True, db_column="ModeratedAt", null=True)),
                ("moderation_notes", models.TextField(blank=True, db_column="ModerationNotes", null=True)),
                ("post_id", models.AutoField(db_column="PostID", primary_key=True, serialize=False)),
                ("title", models.CharField(db_column="Title", max_length=500)),
                ("content_type", models.CharField(db_column="ContentType", default="general", max_length=50)),
                ("author", models.ForeignKey(db_column="AuthorID", on_delete=django.db.models.deletion.CASCADE, related_name="posts", to="myapp.user")),
            ],
            options={
                "verbose_name": "Post",
                "verbose_name_plural": "Posts",
                "db_table": "Posts",
                "ordering": ["-created_at"],
                "managed": True,
            },
        ),
        # Comment model
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("is_active", models.IntegerField(blank=True, db_column="IsActive", default=1, null=True)),
                ("is_deleted", models.IntegerField(blank=True, db_column="IsDeleted", default=0, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="CreatedAt", null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_column="UpdatedAt", null=True)),
                ("created_by", models.IntegerField(blank=True, db_column="CreatedBy", null=True)),
                ("updated_by", models.IntegerField(blank=True, db_column="UpdatedBy", null=True)),
                ("content_text", models.TextField(db_column="ContentText")),
                ("content_status", models.CharField(db_column="ContentStatus", default="published", max_length=20)),
                ("moderated_at", models.DateTimeField(blank=True, db_column="ModeratedAt", null=True)),
                ("moderation_notes", models.TextField(blank=True, db_column="ModerationNotes", null=True)),
                ("comment_id", models.AutoField(db_column="CommentID", primary_key=True, serialize=False)),
                ("author", models.ForeignKey(db_column="AuthorID", on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="myapp.user")),
                ("post", models.ForeignKey(db_column="PostID", on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="myapp.post")),
                ("parent_comment", models.ForeignKey(blank=True, db_column="ParentCommentID", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="myapp.comment")),
            ],
            options={
                "verbose_name": "Comment",
                "verbose_name_plural": "Comments",
                "db_table": "Comments",
                "ordering": ["created_at"],
                "managed": True,
            },
        ),
        # ModerationQueue model
        migrations.CreateModel(
            name="ModerationQueue",
            fields=[
                ("is_active", models.IntegerField(blank=True, db_column="IsActive", default=1, null=True)),
                ("is_deleted", models.IntegerField(blank=True, db_column="IsDeleted", default=0, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="CreatedAt", null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_column="UpdatedAt", null=True)),
                ("created_by", models.IntegerField(blank=True, db_column="CreatedBy", null=True)),
                ("updated_by", models.IntegerField(blank=True, db_column="UpdatedBy", null=True)),
                ("moderation_queue_id", models.AutoField(db_column="ModerationQueueID", primary_key=True, serialize=False)),
                ("content_type", models.CharField(db_column="ContentType", max_length=50)),
                ("content_id", models.IntegerField(db_column="ContentID")),
                ("reason", models.TextField(db_column="Reason")),
                ("details", models.TextField(blank=True, db_column="Details", default="")),
                ("status", models.CharField(db_column="Status", default="pending", max_length=20)),
                ("moderation_notes", models.TextField(blank=True, db_column="ModerationNotes", null=True)),
                ("moderated_at", models.DateTimeField(blank=True, db_column="ModeratedAt", null=True)),
                ("auto_flagged", models.BooleanField(db_column="AutoFlagged", default=False)),
                ("auto_flag_reason", models.TextField(blank=True, db_column="AutoFlagReason", null=True)),
                ("severity", models.IntegerField(db_column="Severity", default=1)),
                ("reporter_id", models.ForeignKey(blank=True, db_column="ReporterID", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reported_content", to="myapp.user")),
                ("moderator_id", models.ForeignKey(blank=True, db_column="ModeratorID", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="moderated_content", to="myapp.user")),
            ],
            options={
                "verbose_name": "Moderation Queue Item",
                "verbose_name_plural": "Moderation Queue Items",
                "db_table": "ModerationQueue",
                "ordering": ["-severity", "-created_at"],
                "managed": True,
            },
        ),
        # ModerationAppeal model
        migrations.CreateModel(
            name="ModerationAppeal",
            fields=[
                ("is_active", models.IntegerField(blank=True, db_column="IsActive", default=1, null=True)),
                ("is_deleted", models.IntegerField(blank=True, db_column="IsDeleted", default=0, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="CreatedAt", null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_column="UpdatedAt", null=True)),
                ("created_by", models.IntegerField(blank=True, db_column="CreatedBy", null=True)),
                ("updated_by", models.IntegerField(blank=True, db_column="UpdatedBy", null=True)),
                ("moderation_appeal_id", models.AutoField(db_column="ModerationAppealID", primary_key=True, serialize=False)),
                ("reason", models.TextField(db_column="Reason")),
                ("status", models.CharField(db_column="Status", default="pending", max_length=20)),
                ("reviewer_notes", models.TextField(blank=True, db_column="ReviewerNotes", null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, db_column="ReviewedAt", null=True)),
                ("original_queue", models.ForeignKey(db_column="OriginalQueueID", on_delete=django.db.models.deletion.CASCADE, related_name="appeals", to="myapp.moderationqueue")),
                ("user", models.ForeignKey(db_column="UserID", on_delete=django.db.models.deletion.CASCADE, related_name="moderation_appeals", to="myapp.user")),
                ("reviewer", models.ForeignKey(blank=True, db_column="ReviewerID", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_appeals", to="myapp.user")),
            ],
            options={
                "verbose_name": "Moderation Appeal",
                "verbose_name_plural": "Moderation Appeals",
                "db_table": "ModerationAppeals",
                "ordering": ["-created_at"],
                "managed": True,
            },
        ),
        # Coupon model
        migrations.CreateModel(
            name="Coupon",
            fields=[
                ("is_active", models.IntegerField(blank=True, db_column="IsActive", default=1, null=True)),
                ("is_deleted", models.IntegerField(blank=True, db_column="IsDeleted", default=0, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="CreatedAt", null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_column="UpdatedAt", null=True)),
                ("created_by", models.IntegerField(blank=True, db_column="CreatedBy", null=True)),
                ("updated_by", models.IntegerField(blank=True, db_column="UpdatedBy", null=True)),
                ("coupon_id", models.AutoField(db_column="CouponID", primary_key=True, serialize=False)),
                ("code", models.CharField(db_column="Code", max_length=50, unique=True)),
                ("description", models.TextField(blank=True, db_column="Description", default="")),
                ("discount_type", models.CharField(db_column="DiscountType", max_length=12)),
                ("discount_value", models.DecimalField(db_column="DiscountValue", decimal_places=2, max_digits=10)),
                ("max_uses", models.IntegerField(db_column="MaxUses", default=0)),
                ("current_uses", models.IntegerField(db_column="CurrentUses", default=0)),
                ("max_uses_per_user", models.IntegerField(db_column="MaxUsesPerUser", default=1)),
                ("valid_from", models.DateTimeField(db_column="ValidFrom")),
                ("valid_until", models.DateTimeField(db_column="ValidUntil")),
                ("min_purchase_amount", models.DecimalField(blank=True, db_column="MinPurchaseAmount", decimal_places=2, max_digits=10, null=True)),
                ("first_purchase_only", models.BooleanField(db_column="FirstPurchaseOnly", default=False)),
                ("applicable_plans", models.ManyToManyField(blank=True, related_name="coupons", to="myapp.subscriptionplan")),
            ],
            options={
                "verbose_name": "Coupon",
                "verbose_name_plural": "Coupons",
                "db_table": "Coupons",
                "ordering": ["-created_at"],
                "managed": True,
            },
        ),
        # CouponUsage model
        migrations.CreateModel(
            name="CouponUsage",
            fields=[
                ("is_active", models.IntegerField(blank=True, db_column="IsActive", default=1, null=True)),
                ("is_deleted", models.IntegerField(blank=True, db_column="IsDeleted", default=0, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="CreatedAt", null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_column="UpdatedAt", null=True)),
                ("created_by", models.IntegerField(blank=True, db_column="CreatedBy", null=True)),
                ("updated_by", models.IntegerField(blank=True, db_column="UpdatedBy", null=True)),
                ("coupon_usage_id", models.AutoField(db_column="CouponUsageID", primary_key=True, serialize=False)),
                ("discount_applied", models.DecimalField(db_column="DiscountApplied", decimal_places=2, max_digits=10)),
                ("original_amount", models.DecimalField(db_column="OriginalAmount", decimal_places=2, max_digits=10)),
                ("final_amount", models.DecimalField(db_column="FinalAmount", decimal_places=2, max_digits=10)),
                ("coupon", models.ForeignKey(db_column="CouponID", on_delete=django.db.models.deletion.CASCADE, related_name="usages", to="myapp.coupon")),
                ("user", models.ForeignKey(db_column="UserID", on_delete=django.db.models.deletion.CASCADE, related_name="coupon_usages", to="myapp.user")),
                ("subscription", models.ForeignKey(blank=True, db_column="SubscriptionID", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="coupon_usages", to="myapp.subscription")),
            ],
            options={
                "verbose_name": "Coupon Usage",
                "verbose_name_plural": "Coupon Usages",
                "db_table": "CouponUsages",
                "ordering": ["-created_at"],
                "managed": True,
            },
        ),
        # ReferralCode model
        migrations.CreateModel(
            name="ReferralCode",
            fields=[
                ("is_active", models.IntegerField(blank=True, db_column="IsActive", default=1, null=True)),
                ("is_deleted", models.IntegerField(blank=True, db_column="IsDeleted", default=0, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="CreatedAt", null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_column="UpdatedAt", null=True)),
                ("created_by", models.IntegerField(blank=True, db_column="CreatedBy", null=True)),
                ("updated_by", models.IntegerField(blank=True, db_column="UpdatedBy", null=True)),
                ("referral_code_id", models.AutoField(db_column="ReferralCodeID", primary_key=True, serialize=False)),
                ("code", models.CharField(db_column="Code", max_length=20, unique=True)),
                ("max_uses", models.IntegerField(db_column="MaxUses", default=0)),
                ("current_uses", models.IntegerField(db_column="CurrentUses", default=0)),
                ("reward_type", models.CharField(db_column="RewardType", default="credit", max_length=20)),
                ("reward_amount", models.DecimalField(db_column="RewardAmount", decimal_places=2, default=0, max_digits=10)),
                ("expires_at", models.DateTimeField(blank=True, db_column="ExpiresAt", null=True)),
                ("user", models.ForeignKey(db_column="UserID", on_delete=django.db.models.deletion.CASCADE, related_name="referral_codes", to="myapp.user")),
            ],
            options={
                "verbose_name": "Referral Code",
                "verbose_name_plural": "Referral Codes",
                "db_table": "ReferralCodes",
                "ordering": ["-created_at"],
                "managed": True,
            },
        ),
        # ReferralTransaction model
        migrations.CreateModel(
            name="ReferralTransaction",
            fields=[
                ("is_active", models.IntegerField(blank=True, db_column="IsActive", default=1, null=True)),
                ("is_deleted", models.IntegerField(blank=True, db_column="IsDeleted", default=0, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_column="CreatedAt", null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_column="UpdatedAt", null=True)),
                ("created_by", models.IntegerField(blank=True, db_column="CreatedBy", null=True)),
                ("updated_by", models.IntegerField(blank=True, db_column="UpdatedBy", null=True)),
                ("referral_transaction_id", models.AutoField(db_column="ReferralTransactionID", primary_key=True, serialize=False)),
                ("reward_given", models.BooleanField(db_column="RewardGiven", default=False)),
                ("reward_amount", models.DecimalField(blank=True, db_column="RewardAmount", decimal_places=2, max_digits=10, null=True)),
                ("referral_code", models.ForeignKey(db_column="ReferralCodeID", on_delete=django.db.models.deletion.CASCADE, related_name="transactions", to="myapp.referralcode")),
                ("referred_user", models.ForeignKey(db_column="ReferredUserID", on_delete=django.db.models.deletion.CASCADE, related_name="referred_by", to="myapp.user")),
            ],
            options={
                "verbose_name": "Referral Transaction",
                "verbose_name_plural": "Referral Transactions",
                "db_table": "ReferralTransactions",
                "ordering": ["-created_at"],
                "managed": True,
            },
        ),
        # =====================================================================
        # 6. Add indexes for new models
        # =====================================================================
        migrations.AddIndex(
            model_name="post",
            index=models.Index(fields=["author", "content_status"], name="Posts_Author_Status_idx"),
        ),
        migrations.AddIndex(
            model_name="post",
            index=models.Index(fields=["content_status", "created_at"], name="Posts_Status_Created_idx"),
        ),
        migrations.AddIndex(
            model_name="post",
            index=models.Index(fields=["content_type", "content_status"], name="Posts_Type_Status_idx"),
        ),
        migrations.AddIndex(
            model_name="comment",
            index=models.Index(fields=["post", "content_status"], name="Comments_Post_Status_idx"),
        ),
        migrations.AddIndex(
            model_name="comment",
            index=models.Index(fields=["author", "content_status"], name="Comments_Author_Status_idx"),
        ),
        migrations.AddIndex(
            model_name="moderationqueue",
            index=models.Index(fields=["status", "created_at"], name="ModQueue_Status_Created_idx"),
        ),
        migrations.AddIndex(
            model_name="moderationqueue",
            index=models.Index(fields=["content_type", "content_id"], name="ModQueue_Content_idx"),
        ),
        migrations.AddIndex(
            model_name="moderationqueue",
            index=models.Index(fields=["severity", "status"], name="ModQueue_Severity_Status_idx"),
        ),
        migrations.AddIndex(
            model_name="moderationappeal",
            index=models.Index(fields=["status", "created_at"], name="ModAppeal_Status_Created_idx"),
        ),
        migrations.AddIndex(
            model_name="moderationappeal",
            index=models.Index(fields=["user", "status"], name="ModAppeal_User_Status_idx"),
        ),
        migrations.AddIndex(
            model_name="coupon",
            index=models.Index(fields=["code", "is_active"], name="Coupon_Code_Active_idx"),
        ),
        migrations.AddIndex(
            model_name="coupon",
            index=models.Index(fields=["valid_from", "valid_until"], name="Coupon_Valid_Range_idx"),
        ),
        migrations.AddIndex(
            model_name="couponusage",
            index=models.Index(fields=["coupon", "user"], name="CouponUsage_Coupon_User_idx"),
        ),
        migrations.AddIndex(
            model_name="referralcode",
            index=models.Index(fields=["code", "is_active"], name="RefCode_Code_Active_idx"),
        ),
        migrations.AddIndex(
            model_name="referralcode",
            index=models.Index(fields=["user", "is_active"], name="RefCode_User_Active_idx"),
        ),
        migrations.AddIndex(
            model_name="referraltransaction",
            index=models.Index(fields=["referral_code", "referred_user"], name="RefTx_Code_User_idx"),
        ),
    ]
