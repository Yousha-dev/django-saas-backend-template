# moderation_service.py

import logging
import re
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class ModerationService:
    """
    Service for content moderation logic.

    Features:
    - Local word/phrase filtering
    - External API integration (OpenAI, Azure Content Safety)
    - Content reporting with database storage
    - Moderation queue management
    - Appeal process support
    """

    # Moderation action types
    ACTION_APPROVE = "approve"
    ACTION_REJECT = "reject"
    ACTION_DELETE = "delete"
    ACTION_REQUEST_CHANGES = "request_changes"

    # Content status
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_DELETED = "deleted"
    STATUS_CHANGES_REQUESTED = "changes_requested"

    def __init__(self):
        # Load banned words from settings or use defaults
        self.banned_words = getattr(
            settings, "BANNED_WORDS", ["badword1", "badword2", "spam", "scam"]
        )
        self.banned_phrases = getattr(settings, "BANNED_PHRASES", [])

        # External API configuration
        self.openai_api_key = getattr(settings, "OPENAI_API_KEY", "")
        self.azure_content_safety_key = getattr(
            settings, "AZURE_CONTENT_SAFETY_KEY", ""
        )
        self.azure_endpoint = getattr(settings, "AZURE_CONTENT_SAFETY_ENDPOINT", "")

        # Moderation threshold (0-1)
        self.strict_mode = getattr(settings, "MODERATION_STRICT_MODE", False)

    def check_text(
        self, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Check text for inappropriate content.

        Args:
            text: Text content to check
            context: Optional context (user_id, content_type, etc.)

        Returns:
            Dict with 'flagged': bool, 'reason': str, 'confidence': float
        """
        if not text:
            return {"flagged": False, "reason": "", "confidence": 0.0}

        # Step 1: Check against local banned words/phrases
        local_result = self._check_local_rules(text)
        if local_result["flagged"]:
            return local_result

        # Step 2: Check external API if available and text is long enough
        if len(text) > 50 and (self.openai_api_key or self.azure_content_safety_key):
            external_result = self._check_external_api(text)
            if external_result["flagged"]:
                return external_result

        return {"flagged": False, "reason": "", "confidence": 0.0}

    def _check_local_rules(self, text: str) -> dict[str, Any]:
        """Check text against local banned words and phrases."""
        lower_text = text.lower()

        # Check banned phrases first (more specific)
        for phrase in self.banned_phrases:
            if phrase.lower() in lower_text:
                return {
                    "flagged": True,
                    "reason": "Contains banned phrase",
                    "confidence": 1.0,
                    "category": "banned_content",
                }

        # Check banned words
        for word in self.banned_words:
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(word.lower()) + r"\b"
            if re.search(pattern, lower_text):
                return {
                    "flagged": True,
                    "reason": f"Contains banned word: {word}",
                    "confidence": 1.0,
                    "category": "banned_content",
                }

        return {"flagged": False, "reason": "", "confidence": 0.0}

    def _check_external_api(self, text: str) -> dict[str, Any]:
        """Check text using external moderation API."""
        # Try OpenAI first
        if self.openai_api_key:
            result = self._check_openai(text)
            if result["flagged"]:
                return result

        # Fall back to Azure Content Safety
        if self.azure_content_safety_key:
            return self._check_azure_content_safety(text)

        return {"flagged": False, "reason": "", "confidence": 0.0}

    def _check_openai(self, text: str) -> dict[str, Any]:
        """Check text using OpenAI Moderation API."""
        try:
            response = requests.post(
                "https://api.openai.com/v1/moderations",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": text, "model": "text-moderation-latest"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                for result in results:
                    if result.get("flagged", False):
                        categories = result.get("categories", {})
                        category_str = ", ".join(
                            [k for k, v in categories.items() if v]
                        )

                        return {
                            "flagged": True,
                            "reason": f"Content flagged by OpenAI: {category_str}",
                            "confidence": 0.8,
                            "category": "ai_detected",
                        }

        except Exception as e:
            logger.warning(f"OpenAI moderation check failed: {e}")

        return {"flagged": False, "reason": "", "confidence": 0.0}

    def _check_azure_content_safety(self, text: str) -> dict[str, Any]:
        """Check text using Azure Content Safety API."""
        try:
            response = requests.post(
                f"{self.azure_endpoint}/contentsafety/text:analyze",
                headers={
                    "Ocp-Apim-Subscription-Key": self.azure_content_safety_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "categories": ["Hate", "Sexual", "Violence", "SelfHarm"],
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                blocklists_match = data.get("blocklistsMatch", [])
                categories_analysis = data.get("categoriesAnalysis", [])

                if blocklists_match or any(
                    c.get("severity", 0) > 2 for c in categories_analysis
                ):
                    return {
                        "flagged": True,
                        "reason": "Content flagged by Azure Content Safety",
                        "confidence": 0.8,
                        "category": "ai_detected",
                    }

        except Exception as e:
            logger.warning(f"Azure Content Safety check failed: {e}")

        return {"flagged": False, "reason": "", "confidence": 0.0}

    def report_content(
        self,
        content_type: str,
        content_id: str,
        reporter_id: int,
        reason: str,
        details: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        User reporting logic - saves to database.

        Args:
            content_type: Type of content (post, comment, message, etc.)
            content_id: ID of the content being reported
            reporter_id: ID of the user reporting
            reason: Reason for reporting
            details: Additional details
            context: Optional context data

        Returns:
            Dict with 'success': bool, 'message': str, 'queue_id': int
        """
        try:
            from myapp.models import ModerationQueue

            # Check if already reported
            existing = ModerationQueue.objects.filter(
                content_type=content_type,
                content_id=content_id,
                reporter_id=reporter_id,
                status=self.STATUS_PENDING,
                is_deleted=0,
            ).first()

            if existing:
                return {
                    "success": False,
                    "message": "You have already reported this content.",
                    "queue_id": existing.moderation_queue_id,
                }

            # Create moderation queue entry
            queue_item = ModerationQueue.objects.create(
                content_type=content_type,
                content_id=content_id,
                reporter_id=reporter_id,
                reason=reason,
                details=details,
                status=self.STATUS_PENDING,
                is_active=1,
                is_deleted=0,
                created_at=timezone.now(),
                created_by=reporter_id,
            )

            logger.info(
                f"User {reporter_id} reported {content_type} {content_id} for {reason}"
            )

            return {
                "success": True,
                "message": "Content reported successfully. Our team will review it.",
                "queue_id": queue_item.moderation_queue_id,
            }

        except Exception as e:
            logger.error(f"Failed to report content: {e}")
            return {
                "success": False,
                "message": "Failed to report content. Please try again.",
                "error": str(e),
            }

    def get_pending_items(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get pending moderation queue items.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of pending moderation items
        """
        try:
            from myapp.models import ModerationQueue

            items = ModerationQueue.objects.filter(
                status=self.STATUS_PENDING, is_deleted=0
            ).order_by("-created_at")[:limit]

            return [
                {
                    "queue_id": item.moderation_queue_id,
                    "content_type": item.content_type,
                    "content_id": item.content_id,
                    "reporter_id": item.reporter_id,
                    "reason": item.reason,
                    "details": item.details,
                    "created_at": item.created_at.isoformat(),
                }
                for item in items
            ]

        except Exception as e:
            logger.error(f"Failed to get pending items: {e}")
            return []

    def take_action(
        self,
        queue_id: int,
        action: str,
        moderator_id: int,
        notes: str = "",
        send_notification: bool = True,
    ) -> dict[str, Any]:
        """
        Take moderation action on a queue item.

        Args:
            queue_id: Moderation queue item ID
            action: Action to take (approve, reject, delete, request_changes)
            moderator_id: ID of the moderator taking action
            notes: Optional notes
            send_notification: Whether to notify user

        Returns:
            Dict with 'success': bool, 'message': str
        """
        try:
            from myapp.models import ModerationQueue

            queue_item = ModerationQueue.objects.get(
                moderation_queue_id=queue_id, status=self.STATUS_PENDING, is_deleted=0
            )

            # Update queue item
            status_map = {
                self.ACTION_APPROVE: self.STATUS_APPROVED,
                self.ACTION_REJECT: self.STATUS_REJECTED,
                self.ACTION_DELETE: self.STATUS_DELETED,
                self.ACTION_REQUEST_CHANGES: self.STATUS_CHANGES_REQUESTED,
            }

            queue_item.status = status_map.get(action, self.STATUS_PENDING)
            queue_item.moderator_id = moderator_id
            queue_item.moderation_notes = notes
            queue_item.moderated_at = timezone.now()
            queue_item.updated_at = timezone.now()
            queue_item.updated_by = moderator_id
            queue_item.save()

            # If action is delete, mark content as deleted
            if action == self.ACTION_DELETE:
                self._delete_content(
                    queue_item.content_type, queue_item.content_id, moderator_id
                )

            # Send notification to reporter if enabled
            if send_notification:
                self._notify_moderation_result(queue_item, action, notes)

            logger.info(
                f"Moderator {moderator_id} took action {action} on queue item {queue_id}"
            )

            return {
                "success": True,
                "message": f"Content {action}d successfully.",
                "queue_id": queue_id,
            }

        except ModerationQueue.DoesNotExist:
            return {
                "success": False,
                "message": "Moderation item not found or already processed.",
            }
        except Exception as e:
            logger.error(f"Failed to take moderation action: {e}")
            return {
                "success": False,
                "message": "Failed to process action. Please try again.",
                "error": str(e),
            }

    def _delete_content(self, content_type: str, content_id: str, deleted_by: int):
        """Mark content as deleted based on type."""
        try:
            # Import models dynamically to avoid circular imports
            if content_type == "post":
                from myapp.models import Post

                Post.objects.filter(post_id=content_id).update(
                    is_deleted=1, deleted_at=timezone.now(), deleted_by=deleted_by
                )
            elif content_type == "comment":
                from myapp.models import Comment

                Comment.objects.filter(comment_id=content_id).update(
                    is_deleted=1, deleted_at=timezone.now(), deleted_by=deleted_by
                )
            # Add more content types as needed

        except Exception as e:
            logger.error(f"Failed to delete content: {e}")

    def _notify_moderation_result(self, queue_item, action: str, notes: str):
        """Notify reporter about moderation result."""
        try:
            from myapp.services.notification_service import NotificationService

            service = NotificationService()

            message_map = {
                self.ACTION_APPROVE: "Your report was reviewed and the content was approved.",
                self.ACTION_REJECT: f"Your report was reviewed. Notes: {notes}",
                self.ACTION_DELETE: "Your report was reviewed and the content was removed.",
                self.ACTION_REQUEST_CHANGES: f"Your report was reviewed. Changes requested: {notes}",
            }

            service.send_notification(
                user_id=queue_item.reporter_id,
                title="Content Moderation Update",
                message=message_map.get(action, "Your report has been reviewed."),
                notification_type="email",
            )

        except Exception as e:
            logger.warning(f"Failed to send moderation notification: {e}")

    def get_user_moderation_history(
        self, user_id: int, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Get moderation history for a specific user.

        Args:
            user_id: User ID to get history for
            limit: Maximum number of items to return

        Returns:
            List of moderation history items
        """
        try:
            from myapp.models import ModerationQueue

            items = ModerationQueue.objects.filter(
                reporter_id=user_id, is_deleted=0
            ).order_by("-created_at")[:limit]

            return [
                {
                    "queue_id": item.moderation_queue_id,
                    "content_type": item.content_type,
                    "content_id": item.content_id,
                    "status": item.status,
                    "reason": item.reason,
                    "moderation_notes": item.moderation_notes,
                    "created_at": item.created_at.isoformat(),
                    "moderated_at": item.moderated_at.isoformat()
                    if item.moderated_at
                    else None,
                }
                for item in items
            ]

        except Exception as e:
            logger.error(f"Failed to get user moderation history: {e}")
            return []

    def submit_appeal(self, queue_id: int, user_id: int, reason: str) -> dict[str, Any]:
        """
        Submit an appeal for a moderation decision.

        Args:
            queue_id: Original moderation queue item ID
            user_id: User ID submitting the appeal
            reason: Reason for appeal

        Returns:
            Dict with 'success': bool, 'message': str
        """
        try:
            from myapp.models import ModerationAppeal, ModerationQueue

            # Check if original item exists and was rejected/deleted
            original = ModerationQueue.objects.get(
                moderation_queue_id=queue_id, is_deleted=0
            )

            if original.status not in [self.STATUS_REJECTED, self.STATUS_DELETED]:
                return {
                    "success": False,
                    "message": "Can only appeal rejected or deleted content.",
                }

            # Check if appeal already exists
            existing = ModerationAppeal.objects.filter(
                original_queue_id=queue_id,
                user_id=user_id,
                status="pending",
                is_deleted=0,
            ).first()

            if existing:
                return {
                    "success": False,
                    "message": "An appeal is already pending for this item.",
                }

            # Create appeal
            appeal = ModerationAppeal.objects.create(
                original_queue_id=queue_id,
                user_id=user_id,
                reason=reason,
                status="pending",
                is_active=1,
                is_deleted=0,
                created_at=timezone.now(),
                created_by=user_id,
            )

            logger.info(
                f"User {user_id} submitted appeal for moderation item {queue_id}"
            )

            return {
                "success": True,
                "message": "Appeal submitted successfully. Our team will review it.",
                "appeal_id": appeal.moderation_appeal_id,
            }

        except ModerationQueue.DoesNotExist:
            return {
                "success": False,
                "message": "Original moderation item not found.",
            }
        except Exception as e:
            logger.error(f"Failed to submit appeal: {e}")
            return {
                "success": False,
                "message": "Failed to submit appeal. Please try again.",
                "error": str(e),
            }
