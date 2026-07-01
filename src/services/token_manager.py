"""Token manager for Flow2API with AT auto-refresh"""
import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List
from ..core.database import Database
from ..core.config import config
from ..core.models import Token, Project
from ..core.logger import debug_logger
from ..core.monitoring import record_token_refresh
from .flow_client import FlowClient
from .proxy_manager import ProxyManager


class TokenManager:
    """Token lifecycle manager with AT auto-refresh"""

    def __init__(self, db: Database, flow_client: FlowClient):
        self.db = db
        self.flow_client = flow_client
        self._refresh_lock_guard = asyncio.Lock()
        self._project_lock_guard = asyncio.Lock()
        self._refresh_locks: dict[int, asyncio.Lock] = {}
        self._project_locks: dict[int, asyncio.Lock] = {}
        self._refresh_futures: dict[int, asyncio.Task] = {}
        self._at_validation_cache: dict[int, float] = {}
        self._protocol_refresher_task: Optional[asyncio.Task] = None

    async def _get_token_lock(
        self,
        lock_map: dict[int, asyncio.Lock],
        guard: asyncio.Lock,
        token_id: int,
    ) -> asyncio.Lock:
        """Acquire a per-token lock to prevent serial blocking between different tokens."""
        async with guard:
            lock = lock_map.get(token_id)
            if lock is None:
                lock = asyncio.Lock()
                lock_map[token_id] = lock
            return lock

    def _get_project_pool_size(self) -> int:
        """Read the currently effective single-token project pool size configuration."""
        try:
            return max(1, min(50, int(config.personal_project_pool_size or 4)))
        except Exception:
            return 4

    def _sort_projects(self, projects: List[Project]) -> List[Project]:
        """Sort projects in a stable order for round-robin selection."""
        return sorted(projects, key=lambda project: (project.id or 0, project.project_id))

    def _normalize_project_name_base(self, project_name: Optional[str] = None) -> str:
        """Normalize a project base name for pooled creation."""
        raw_name = (project_name or "").strip()
        if raw_name:
            parts = raw_name.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].startswith("P") and parts[1][1:].isdigit():
                return parts[0]
            return raw_name
        return datetime.now().strftime("%b %d - %H:%M")

    def _build_project_name(self, pool_index: int, base_name: Optional[str] = None) -> str:
        """Build a project name for the pool."""
        normalized_base = self._normalize_project_name_base(base_name)
        return f"{normalized_base} P{pool_index}"

    def _normalize_protocol_mode(self, value: Optional[str]) -> str:
        mode = (value or "session").strip().lower()
        return "protocol" if mode == "protocol" else "session"

    def _normalize_refresh_interval(self, value: Optional[int]) -> int:
        try:
            return max(1, int(value if value is not None else 120))
        except Exception:
            return 120

    def _parse_at_expires(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    def _as_utc(self, value: Optional[datetime]) -> Optional[datetime]:
        if not value:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _normalize_token_proxy_url(self, proxy_url: Optional[str]) -> str:
        raw = (proxy_url or "").strip()
        if not raw:
            return ""
        proxy_manager = getattr(self.flow_client, "proxy_manager", None)
        if proxy_manager and hasattr(proxy_manager, "normalize_proxy_url"):
            normalized = proxy_manager.normalize_proxy_url(raw)
            return normalized or ""
        return raw

    def _clear_at_validation_cache(self, token_id: int) -> None:
        self._at_validation_cache.pop(int(token_id), None)

    def _mark_at_valid(self, token_id: int, ttl_seconds: int = 300) -> None:
        self._at_validation_cache[int(token_id)] = time.monotonic() + max(30, int(ttl_seconds or 300))

    def _has_recent_at_validation(self, token_id: int) -> bool:
        expires_at = float(self._at_validation_cache.get(int(token_id), 0.0) or 0.0)
        if expires_at <= time.monotonic():
            self._clear_at_validation_cache(token_id)
            return False
        return True

    async def _flow_call_for_token(self, token: Token, call):
        previous_fingerprint = self.flow_client.get_request_fingerprint()
        proxy_url = (getattr(token, "proxy_url", "") or "").strip()
        if proxy_url:
            next_fingerprint = dict(previous_fingerprint or {})
            next_fingerprint["proxy_url"] = proxy_url
            self.flow_client._set_request_fingerprint(next_fingerprint)
        try:
            return await call()
        finally:
            self.flow_client._set_request_fingerprint(previous_fingerprint)

    async def _st_to_at_for_token(self, token: Token, st: str) -> Dict[str, Any]:
        return await self._flow_call_for_token(token, lambda: self.flow_client.st_to_at(st))

    async def _get_credits_for_token(self, token: Token, at: str) -> Dict[str, Any]:
        return await self._flow_call_for_token(token, lambda: self.flow_client.get_credits(at))

    async def get_personal_warmup_project_ids(
        self,
        tokens: Optional[List[Token]] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """Return the list of project IDs recommended for warming up at startup in personal mode."""
        token_list = tokens if tokens is not None else await self.get_all_tokens()
        pool_size = self._get_project_pool_size()
        warmup_ids: List[str] = []
        seen_projects: set[str] = set()

        try:
            warmup_limit = None if limit is None else max(1, int(limit))
        except Exception:
            warmup_limit = None

        for token in token_list:
            if not token or not token.is_active:
                continue

            candidate_ids: List[str] = []
            current_project_id = str(token.current_project_id or "").strip()
            if current_project_id:
                candidate_ids.append(current_project_id)

            projects = [project for project in await self.db.get_projects_by_token(token.id) if project.is_active]
            for project in self._sort_projects(projects):
                project_id = str(project.project_id or "").strip()
                if project_id and project_id not in candidate_ids:
                    candidate_ids.append(project_id)

            for project_id in candidate_ids[:pool_size]:
                if project_id in seen_projects:
                    continue
                seen_projects.add(project_id)
                warmup_ids.append(project_id)
                if warmup_limit is not None and len(warmup_ids) >= warmup_limit:
                    return warmup_ids

        return warmup_ids

    async def _create_project_for_token(self, token: Token, pool_index: int, base_name: Optional[str] = None) -> Project:
        """Create a new pooled project for a token and persist it."""
        project_name = self._build_project_name(pool_index, base_name)
        project_id = await self.flow_client.create_project(token.st, project_name)
        debug_logger.log_info(
            f"[PROJECT] Created pooled project for token {token.id}: {project_name} ({project_id})"
        )
        project = Project(
            project_id=project_id,
            token_id=token.id,
            project_name=project_name,
        )
        project.id = await self.db.add_project(project)
        return project

    def _select_next_project(self, token: Token, projects: List[Project]) -> Project:
        """Select the next project from the pool in round-robin order."""
        ordered_projects = self._sort_projects(projects)
        if not ordered_projects:
            raise ValueError("No available projects for token")

        if len(ordered_projects) == 1:
            return ordered_projects[0]

        if token.current_project_id:
            for index, project in enumerate(ordered_projects):
                if project.project_id == token.current_project_id:
                    return ordered_projects[(index + 1) % len(ordered_projects)]

        return ordered_projects[0]

    # ========== Token CRUD ==========

    async def get_all_tokens(self) -> List[Token]:
        """Get all tokens"""
        return await self.db.get_all_tokens()

    async def get_active_tokens(self) -> List[Token]:
        """Get all active tokens"""
        return await self.db.get_active_tokens()

    async def get_token(self, token_id: int) -> Optional[Token]:
        """Get token by ID"""
        return await self.db.get_token(token_id)

    async def delete_token(self, token_id: int):
        """Delete token"""
        token = await self.db.get_token(token_id)
        project_ids: List[str] = []
        if token:
            current_project_id = str(token.current_project_id or "").strip()
            if current_project_id:
                project_ids.append(current_project_id)

        for project in await self.db.get_projects_by_token(token_id):
            project_id = str(project.project_id or "").strip()
            if project_id and project_id not in project_ids:
                project_ids.append(project_id)

        await self.db.delete_token(token_id)

        refresh_task = self._refresh_futures.pop(token_id, None)
        if refresh_task and not refresh_task.done():
            refresh_task.cancel()
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self._refresh_locks.pop(token_id, None)
        self._project_locks.pop(token_id, None)

        if config.captcha_method == "personal" and project_ids:
            try:
                from .browser_captcha_personal import BrowserCaptchaService
                service = await BrowserCaptchaService.get_instance(self.db)
                for project_id in project_ids:
                    await service.stop_resident_mode(project_id)
            except Exception as e:
                debug_logger.log_warning(f"[DELETE_TOKEN] Failed to clean up personal browser state: {e}")

    async def enable_token(self, token_id: int):
        """Enable a token and reset error count"""
        # Enable the token
        await self.db.update_token(token_id, is_active=True, ban_reason=None, banned_at=None)
        # Reset error count when enabling (only reset total error_count, keep today_error_count)
        await self.db.reset_error_count(token_id)

    async def disable_token(self, token_id: int):
        """Disable a token"""
        await self.db.update_token(token_id, is_active=False)

    # ========== Token addition (supports Project creation) ==========

    async def add_token(
        self,
        st: str,
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        remark: Optional[str] = None,
        image_enabled: bool = True,
        video_enabled: bool = True,
        image_concurrency: int = -1,
        video_concurrency: int = -1,
        captcha_proxy_url: Optional[str] = None,
        extension_route_key: Optional[str] = None,
        protocol_mode: str = "session",
        google_cookies: Optional[str] = None,
        login_account: Optional[str] = None,
        login_password: Optional[str] = None,
        proxy_url: Optional[str] = None,
        auto_refresh_enabled: bool = True,
        refresh_interval_minutes: int = 120,
    ) -> Token:
        """Add a new token and prepare its pooled projects."""
        existing_token = await self.db.get_token_by_st(st)
        if existing_token:
            raise ValueError(f"Token already exists: {existing_token.email}")

        debug_logger.log_info(f"[ADD_TOKEN] Converting ST to AT...")
        try:
            result = await self.flow_client.st_to_at(st)
            at = result["access_token"]
            expires = result.get("expires")
            user_info = result.get("user", {})
            email = user_info.get("email", "")
            name = user_info.get("name", email.split("@")[0] if email else "")
            at_expires = None
            if expires:
                try:
                    at_expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                except Exception:
                    pass
        except Exception as e:
            raise ValueError(f"ST to AT conversion failed: {str(e)}")

        try:
            credits_result = await self.flow_client.get_credits(at)
            credits = credits_result.get("credits", 0)
            user_paygate_tier = credits_result.get("userPaygateTier")
        except Exception:
            credits = 0
            user_paygate_tier = None

        base_project_name = self._normalize_project_name_base(project_name)
        project_pool_size = self._get_project_pool_size()
        pooled_projects: List[Project] = []

        if project_id:
            first_project_name = self._build_project_name(1, base_project_name)
            debug_logger.log_info(f"[ADD_TOKEN] Using provided project_id as pooled project #1: {project_id}")
            pooled_projects.append(Project(
                project_id=project_id,
                token_id=0,
                project_name=first_project_name,
                tool_name="PINHOLE"
            ))
        else:
            try:
                first_project_name = self._build_project_name(1, base_project_name)
                first_project_id = await self.flow_client.create_project(st, first_project_name)
                debug_logger.log_info(f"[ADD_TOKEN] Created pooled project #1: {first_project_name} (ID: {first_project_id})")
                pooled_projects.append(Project(
                    project_id=first_project_id,
                    token_id=0,
                    project_name=first_project_name,
                    tool_name="PINHOLE"
                ))
            except Exception as e:
                raise ValueError(f"Failed to create first project: {str(e)}")

        token = Token(
            st=st,
            at=at,
            at_expires=at_expires,
            email=email,
            name=name,
            remark=remark,
            is_active=True,
            credits=credits,
            user_paygate_tier=user_paygate_tier,
            current_project_id=pooled_projects[0].project_id,
            current_project_name=pooled_projects[0].project_name,
            image_enabled=image_enabled,
            video_enabled=video_enabled,
            image_concurrency=image_concurrency,
            video_concurrency=video_concurrency,
            captcha_proxy_url=captcha_proxy_url,
            extension_route_key=extension_route_key,
            protocol_mode=self._normalize_protocol_mode(protocol_mode),
            google_cookies=(google_cookies or "").strip(),
            login_account=(login_account or "").strip(),
            login_password=login_password or "",
            proxy_url=self._normalize_token_proxy_url(proxy_url),
            auto_refresh_enabled=bool(auto_refresh_enabled),
            refresh_interval_minutes=self._normalize_refresh_interval(refresh_interval_minutes),
        )

        token_id = await self.db.add_token(token)
        token.id = token_id

        pooled_projects[0].token_id = token_id
        pooled_projects[0].id = await self.db.add_project(pooled_projects[0])

        while len(pooled_projects) < project_pool_size:
            new_project = await self._create_project_for_token(token, len(pooled_projects) + 1, base_project_name)
            pooled_projects.append(new_project)

        debug_logger.log_info(
            f"[ADD_TOKEN] Token added successfully (ID: {token_id}, Email: {email}, pooled_projects={len(pooled_projects)})"
        )
        return token
    async def update_token(
        self,
        token_id: int,
        st: Optional[str] = None,
        at: Optional[str] = None,
        at_expires: Optional[datetime] = None,
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        remark: Optional[str] = None,
        image_enabled: Optional[bool] = None,
        video_enabled: Optional[bool] = None,
        image_concurrency: Optional[int] = None,
        video_concurrency: Optional[int] = None,
        captcha_proxy_url: Optional[str] = None,
        extension_route_key: Optional[str] = None,
        protocol_mode: Optional[str] = None,
        google_cookies: Optional[str] = None,
        login_account: Optional[str] = None,
        login_password: Optional[str] = None,
        proxy_url: Optional[str] = None,
        auto_refresh_enabled: Optional[bool] = None,
        refresh_interval_minutes: Optional[int] = None,
    ):
        """Update token (supports modifying project_id and project_name)

        When the user edits and saves the token, if the token is not expired,
        automatically clear the 429 ban state.
        """
        update_fields = {}
        credential_updated = any(value is not None for value in (st, at, at_expires))

        if st is not None:
            update_fields["st"] = st
        if at is not None:
            update_fields["at"] = at
        if at_expires is not None:
            update_fields["at_expires"] = at_expires
        if project_id is not None:
            update_fields["current_project_id"] = project_id
        if project_name is not None:
            update_fields["current_project_name"] = project_name
        if remark is not None:
            update_fields["remark"] = remark
        if image_enabled is not None:
            update_fields["image_enabled"] = image_enabled
        if video_enabled is not None:
            update_fields["video_enabled"] = video_enabled
        if image_concurrency is not None:
            update_fields["image_concurrency"] = image_concurrency
        if video_concurrency is not None:
            update_fields["video_concurrency"] = video_concurrency
        if captcha_proxy_url is not None:
            update_fields["captcha_proxy_url"] = captcha_proxy_url
        if extension_route_key is not None:
            update_fields["extension_route_key"] = extension_route_key
        if protocol_mode is not None:
            update_fields["protocol_mode"] = self._normalize_protocol_mode(protocol_mode)
        if google_cookies is not None:
            update_fields["google_cookies"] = google_cookies.strip()
        if login_account is not None:
            update_fields["login_account"] = login_account.strip()
        if login_password is not None:
            update_fields["login_password"] = login_password
        if proxy_url is not None:
            update_fields["proxy_url"] = self._normalize_token_proxy_url(proxy_url)
        if auto_refresh_enabled is not None:
            update_fields["auto_refresh_enabled"] = bool(auto_refresh_enabled)
        if refresh_interval_minutes is not None:
            update_fields["refresh_interval_minutes"] = self._normalize_refresh_interval(refresh_interval_minutes)

        # Check if the token is banned due to 429; if so and it is not expired, clear the 429 state
        token = await self.db.get_token(token_id)
        if credential_updated and token and not token.is_active:
            debug_logger.log_info(f"[UPDATE_TOKEN] Token {token_id} credentials updated, automatically restoring to enabled state")
            update_fields["is_active"] = True
            update_fields["ban_reason"] = None
            update_fields["banned_at"] = None

        if token and token.ban_reason == "429_rate_limit":
            # Check if the token is expired
            is_expired = False
            if token.at_expires:
                now = datetime.now(timezone.utc)
                if token.at_expires.tzinfo is None:
                    at_expires_aware = token.at_expires.replace(tzinfo=timezone.utc)
                else:
                    at_expires_aware = token.at_expires
                is_expired = at_expires_aware <= now

            # If not expired, clear the 429 ban state
            if not is_expired:
                debug_logger.log_info(f"[UPDATE_TOKEN] Token {token_id} edited and saved, clearing 429 ban state")
                update_fields["ban_reason"] = None
                update_fields["banned_at"] = None

        if update_fields:
            if credential_updated:
                self._clear_at_validation_cache(token_id)
            await self.db.update_token(token_id, **update_fields)

    # ========== AT auto-refresh logic (core) ==========

    def _should_refresh_at(self, token: Token) -> bool:
        """Determine whether AT needs to be refreshed based on the current token snapshot."""
        if not token.at:
            debug_logger.log_info(f"[AT_CHECK] Token {token.id}: AT does not exist, refresh required")
            return True

        if not token.at_expires:
            debug_logger.log_info(f"[AT_CHECK] Token {token.id}: AT expiry unknown, attempting refresh")
            return True

        now = datetime.now(timezone.utc)
        if token.at_expires.tzinfo is None:
            at_expires_aware = token.at_expires.replace(tzinfo=timezone.utc)
        else:
            at_expires_aware = token.at_expires

        time_until_expiry = at_expires_aware - now
        if time_until_expiry.total_seconds() < 3600:
            debug_logger.log_info(
                f"[AT_CHECK] Token {token.id}: AT about to expire "
                f"({time_until_expiry.total_seconds():.0f} seconds remaining), refresh required"
            )
            return True

        return False

    def needs_at_refresh(self, token: Optional[Token]) -> bool:
        """Allow the scheduler to quickly determine whether the current token will likely trigger an AT refresh."""
        if not token:
            return True
        return self._should_refresh_at(token)

    async def ensure_valid_token(self, token: Optional[Token]) -> Optional[Token]:
        """Ensure the token's AT is usable and return the latest refreshed object when needed."""
        if not token:
            return None

        if not self._should_refresh_at(token):
            if self._has_recent_at_validation(token.id):
                return token
            try:
                credits_result = await self._get_credits_for_token(token, token.at)
                await self.db.update_token(
                    token.id,
                    credits=credits_result.get("credits", 0),
                    user_paygate_tier=credits_result.get("userPaygateTier"),
                )
                self._mark_at_valid(token.id)
                return await self.db.get_token(token.id) or token
            except Exception as e:
                debug_logger.log_warning(
                    f"[AT_CHECK] Token {token.id}: locally judged as not expired, but upstream validation failed, preparing to refresh AT/ST - {e}"
                )

        if not await self._refresh_at(token.id):
            return None

        return await self.db.get_token(token.id)

    async def is_at_valid(self, token_id: int, token: Optional[Token] = None) -> bool:
        """Check if AT is valid; auto-refresh if invalid or about to expire

        Returns:
            True if AT is valid or refreshed successfully
            False if AT cannot be refreshed
        """
        token_obj = token if token and token.id == token_id else await self.db.get_token(token_id)
        if not token_obj:
            return False

        valid_token = await self.ensure_valid_token(token_obj)
        return valid_token is not None


    async def _refresh_at_inner(self, token_id: int) -> bool:
        """Perform exactly one real AT refresh attempt."""
        refresh_lock = await self._get_token_lock(
            self._refresh_locks,
            self._refresh_lock_guard,
            token_id,
        )
        async with refresh_lock:
            token = await self.db.get_token(token_id)
            if not token:
                return False

            result = await self._do_refresh_at(token_id, token.st, token)
            if result:
                return True

            debug_logger.log_info(f"[AT_REFRESH] Token {token_id}: first AT refresh failed, trying ST refresh...")
            new_st = await self._try_refresh_st(token_id, token)
            if new_st:
                debug_logger.log_info(f"[AT_REFRESH] Token {token_id}: ST refreshed, retrying AT refresh...")
                latest_token = await self.db.get_token(token_id) or token
                result = await self._do_refresh_at(token_id, new_st, latest_token)
                if result:
                    return True

            debug_logger.log_error(f"[AT_REFRESH] Token {token_id}: all refresh attempts failed, disabling token")
            await self.disable_token(token_id)
            self._clear_at_validation_cache(token_id)
            return False

    async def _refresh_at(self, token_id: int) -> bool:
        """Coalesce concurrent AT refresh calls for the same token."""
        existing_task = self._refresh_futures.get(token_id)
        if existing_task:
            return await existing_task

        async def runner() -> bool:
            try:
                return await self._refresh_at_inner(token_id)
            finally:
                current = self._refresh_futures.get(token_id)
                if current is task:
                    self._refresh_futures.pop(token_id, None)

        task = asyncio.create_task(runner())
        self._refresh_futures[token_id] = task
        return await task

    async def _do_refresh_at(self, token_id: int, st: str, token: Optional[Token] = None) -> bool:
        """Core logic for performing AT refresh

        Args:
            token_id: Token ID
            st: Session Token

        Returns:
            True if refresh successful AND AT is valid, False otherwise
        """
        try:
            debug_logger.log_info(f"[AT_REFRESH] Token {token_id}: Starting AT refresh...")

            # Use ST to AT conversion
            token = token or await self.db.get_token(token_id)
            result = await (
                self._st_to_at_for_token(token, st)
                if token is not None
                else self.flow_client.st_to_at(st)
            )
            new_at = result["access_token"]
            expires = result.get("expires")

            # Parse expiry time
            new_at_expires = None
            if expires:
                try:
                    new_at_expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                except:
                    pass

            # Update database
            await self.db.update_token(
                token_id,
                at=new_at,
                at_expires=new_at_expires
            )

            debug_logger.log_info(f"[AT_REFRESH] Token {token_id}: AT refresh succeeded")
            debug_logger.log_info(f"  - New expiry time: {new_at_expires}")

            # Verify AT validity via get_credits
            try:
                credits_result = await (
                    self._get_credits_for_token(token, new_at)
                    if token is not None
                    else self.flow_client.get_credits(new_at)
                )
                await self.db.update_token(
                    token_id,
                    credits=credits_result.get("credits", 0),
                    user_paygate_tier=credits_result.get("userPaygateTier"),
                )
                self._mark_at_valid(token_id)
                debug_logger.log_info(f"[AT_REFRESH] Token {token_id}: AT verification succeeded (credits: {credits_result.get('credits', 0)})")
                record_token_refresh("at", "success")
                return True
            except Exception as verify_err:
                # AT verification failed (may return 401), meaning ST has expired
                error_msg = str(verify_err)
                if "401" in error_msg or "UNAUTHENTICATED" in error_msg:
                    debug_logger.log_warning(f"[AT_REFRESH] Token {token_id}: AT verification failed (401), ST may have expired")
                    record_token_refresh("at", "failure")
                    return False
                else:
                    # Other errors (e.g., network issues) still treated as success
                    debug_logger.log_warning(f"[AT_REFRESH] Token {token_id}: Non-auth error during AT verification: {error_msg}")
                    record_token_refresh("at", "success")
                    return True

        except Exception as e:
            debug_logger.log_error(f"[AT_REFRESH] Token {token_id}: AT refresh failed - {str(e)}")
            record_token_refresh("at", "failure")
            return False

    async def _try_protocol_refresh_st(self, token_id: int, token: Token) -> Optional[str]:
        if self._normalize_protocol_mode(getattr(token, "protocol_mode", "session")) != "protocol":
            return None
        if not (getattr(token, "google_cookies", "") or "").strip():
            debug_logger.log_info(f"[ST_REFRESH] Token {token_id}: Google Cookies not configured, skipping protocol refresh")
            return None

        try:
            from .protocol_login import protocol_loginer

            debug_logger.log_info(f"[ST_REFRESH] Token {token_id}: Attempting protocol refresh of ST...")
            login_result = await protocol_loginer.login(
                token.google_cookies,
                proxy=(getattr(token, "proxy_url", "") or None),
                email=(getattr(token, "login_account", "") or token.email or None),
            )
            if login_result.get("success") and login_result.get("session_token"):
                new_st = str(login_result["session_token"]).strip()
                await self.db.update_token(
                    token_id,
                    st=new_st,
                    last_st_refresh_at=datetime.now(timezone.utc),
                    last_st_refresh_result="success",
                )
                debug_logger.log_info(f"[ST_REFRESH] Token {token_id}: Protocol refresh of ST succeeded")
                record_token_refresh("st", "success")
                return new_st

            error = str(login_result.get("error") or "Protocol refresh failed")
            await self.db.update_token(
                token_id,
                last_st_refresh_at=datetime.now(timezone.utc),
                last_st_refresh_result=error,
            )
            debug_logger.log_warning(f"[ST_REFRESH] Token {token_id}: Protocol refresh of ST failed - {error}")
            record_token_refresh("st", "failure")
            return None
        except Exception as e:
            await self.db.update_token(
                token_id,
                last_st_refresh_at=datetime.now(timezone.utc),
                last_st_refresh_result=str(e),
            )
            debug_logger.log_error(f"[ST_REFRESH] Token {token_id}: Protocol refresh of ST exception - {e}")
            record_token_refresh("st", "failure")
            return None

    async def _try_refresh_st(self, token_id: int, token) -> Optional[str]:
        """Try to refresh the Session Token via the browser.

        Uses a resident tab to obtain a new __Secure-next-auth.session-token.

        Args:
            token_id: Token ID
            token: Token object

        Returns:
            New ST string, or None on failure.
        """
        try:
            from ..core.config import config

            protocol_st = await self._try_protocol_refresh_st(token_id, token)
            if protocol_st:
                return protocol_st

            # ST auto-refresh is only supported in personal mode.
            if config.captcha_method != "personal":
                debug_logger.log_info(f"[ST_REFRESH] Not in personal mode, skipping ST auto-refresh")
                return None

            if not token.current_project_id:
                debug_logger.log_warning(f"[ST_REFRESH] Token {token_id} has no project_id, cannot refresh ST")
                return None

            debug_logger.log_info(f"[ST_REFRESH] Token {token_id}: trying to refresh ST via browser...")

            from .browser_captcha_personal import BrowserCaptchaService
            service = await BrowserCaptchaService.get_instance(self.db)

            refresh_timeout_seconds = 45.0
            try:
                new_st = await asyncio.wait_for(
                    service.refresh_session_token(token.current_project_id),
                    timeout=refresh_timeout_seconds,
                )
            except asyncio.TimeoutError:
                debug_logger.log_error(
                    f"[ST_REFRESH] Token {token_id}: ST refresh timed out ({refresh_timeout_seconds:.0f}s)"
                )
                record_token_refresh("st", "failure")
                return None
            if new_st and new_st != token.st:
                # Update the ST in the database.
                await self.db.update_token(token_id, st=new_st)
                debug_logger.log_info(f"[ST_REFRESH] Token {token_id}: ST auto-updated")
                record_token_refresh("st", "success")
                return new_st
            elif new_st == token.st:
                debug_logger.log_warning(f"[ST_REFRESH] Token {token_id}: retrieved ST equals existing ST, login may be invalid")
                record_token_refresh("st", "failure")
                return None
            else:
                debug_logger.log_warning(f"[ST_REFRESH] Token {token_id}: failed to obtain new ST")
                record_token_refresh("st", "failure")
                return None

        except Exception as e:
            debug_logger.log_error(f"[ST_REFRESH] Token {token_id}: ST refresh failed - {str(e)}")
            record_token_refresh("st", "failure")
            return None

    async def _refresh_protocol_token(self, token: Token, now: datetime) -> None:
        token_id = int(token.id)
        refresh_lock = await self._get_token_lock(
            self._refresh_locks,
            self._refresh_lock_guard,
            token_id,
        )
        async with refresh_lock:
            latest = await self.db.get_token(token_id)
            if not latest or not latest.is_active:
                return
            if not latest.auto_refresh_enabled:
                return
            if self._normalize_protocol_mode(latest.protocol_mode) != "protocol":
                return
            if not (latest.google_cookies or "").strip():
                return

            new_st = await self._try_protocol_refresh_st(token_id, latest)
            if not new_st:
                return

            try:
                session = await self._st_to_at_for_token(latest, new_st)
                new_at = str(session.get("access_token") or "").strip()
                if not new_at:
                    raise RuntimeError("ST-to-AT response missing access_token")

                updates: Dict[str, Any] = {
                    "st": new_st,
                    "at": new_at,
                    "at_expires": self._parse_at_expires(session.get("expires")),
                    "last_st_refresh_at": now,
                    "last_st_refresh_result": "success",
                }
                user_info = session.get("user") if isinstance(session.get("user"), dict) else {}
                if user_info.get("email"):
                    updates["email"] = user_info.get("email")
                if user_info.get("name"):
                    updates["name"] = user_info.get("name")

                try:
                    credits_result = await self._get_credits_for_token(latest, new_at)
                    updates["credits"] = credits_result.get("credits", 0)
                    updates["user_paygate_tier"] = credits_result.get("userPaygateTier")
                except Exception as e:
                    debug_logger.log_warning(f"[PROTOCOL_REFRESH] Token {token_id}: refresh credits failed - {e}")

                await self.db.update_token(token_id, **updates)
                record_token_refresh("at", "success")
                debug_logger.log_info(f"[PROTOCOL_REFRESH] Token {token_id}: protocol ST/AT refresh succeeded")
            except Exception as e:
                await self.db.update_token(
                    token_id,
                    st=new_st,
                    last_st_refresh_at=now,
                    last_st_refresh_result=str(e),
                )
                record_token_refresh("at", "failure")
                debug_logger.log_error(f"[PROTOCOL_REFRESH] Token {token_id}: protocol ST-to-AT failed - {e}")

    async def run_protocol_refresh_once(self) -> None:
        """Refresh protocol-mode tokens whose ST refresh interval is due."""
        try:
            refresh_config = await self.db.get_token_refresh_config()
        except Exception as e:
            debug_logger.log_warning(f"[PROTOCOL_REFRESH] failed to read refresh config: {e}")
            return

        if not refresh_config or not refresh_config.enabled:
            return

        tokens = await self.db.get_active_tokens()
        now = datetime.now(timezone.utc)
        for token in tokens:
            try:
                if not token.auto_refresh_enabled:
                    continue
                if self._normalize_protocol_mode(token.protocol_mode) != "protocol":
                    continue
                if not (token.google_cookies or "").strip():
                    continue

                interval_minutes = token.refresh_interval_minutes or refresh_config.refresh_interval_minutes or 120
                interval_minutes = self._normalize_refresh_interval(interval_minutes)
                last_refresh = self._as_utc(token.last_st_refresh_at)
                if last_refresh and now - last_refresh < timedelta(minutes=interval_minutes):
                    continue

                await self._refresh_protocol_token(token, now)
            except Exception as e:
                debug_logger.log_error(f"[PROTOCOL_REFRESH] Token {getattr(token, 'id', '?')}: background refresh exception - {e}")

    async def _protocol_refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            try:
                await self.run_protocol_refresh_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                debug_logger.log_error(f"[PROTOCOL_REFRESH] background task exception - {e}")

    def start_protocol_refresher(self) -> None:
        if self._protocol_refresher_task and not self._protocol_refresher_task.done():
            return
        self._protocol_refresher_task = asyncio.create_task(self._protocol_refresh_loop())

    async def stop_protocol_refresher(self) -> None:
        task = self._protocol_refresher_task
        self._protocol_refresher_task = None
        if not task or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            debug_logger.log_warning(f"[PROTOCOL_REFRESH] error stopping background task: {e}")

    async def ensure_project_exists(self, token_id: int) -> str:
        """Ensure a token has a pooled set of projects and return one in round-robin order."""
        project_lock = await self._get_token_lock(
            self._project_locks,
            self._project_lock_guard,
            token_id,
        )
        async with project_lock:
            token = await self.db.get_token(token_id)
            if not token:
                raise ValueError("Token not found")

            projects = [project for project in await self.db.get_projects_by_token(token_id) if project.is_active]
            projects = self._sort_projects(projects)

            try:
                project_pool_size = self._get_project_pool_size()
                while len(projects) < project_pool_size:
                    new_project = await self._create_project_for_token(token, len(projects) + 1)
                    projects.append(new_project)
                    projects = self._sort_projects(projects)

                selectable_projects = projects[:project_pool_size]
                selected_project = self._select_next_project(token, selectable_projects)
                await self.db.update_token(
                    token_id,
                    current_project_id=selected_project.project_id,
                    current_project_name=selected_project.project_name,
                )
                return selected_project.project_id
            except Exception as e:
                raise ValueError(f"Failed to prepare project pool: {str(e)}")

    async def record_usage(self, token_id: int, is_video: bool = False):
        """Record token usage"""
        await self.db.update_token(token_id, use_count=1, last_used_at=datetime.now())

        if is_video:
            await self.db.increment_token_stats(token_id, "video")
        else:
            await self.db.increment_token_stats(token_id, "image")

    async def record_error(self, token_id: int):
        """Record token error and auto-disable if threshold reached"""
        await self.db.increment_token_stats(token_id, "error")

        # Check if should auto-disable token (based on consecutive errors)
        stats = await self.db.get_token_stats(token_id)
        admin_config = await self.db.get_admin_config()

        if stats and stats.consecutive_error_count >= admin_config.error_ban_threshold:
            debug_logger.log_warning(
                f"[TOKEN_BAN] Token {token_id} consecutive error count ({stats.consecutive_error_count}) "
                f"reached threshold ({admin_config.error_ban_threshold}), auto-disabling"
            )
            await self.disable_token(token_id)

    async def record_success(self, token_id: int):
        """Record successful request (reset consecutive error count)

        This method resets error_count to 0, which is used for auto-disable threshold checking.
        Note: today_error_count and historical statistics are NOT reset.
        """
        await self.db.reset_error_count(token_id)

    async def ban_token_for_429(self, token_id: int):
        """Immediately ban a token due to a 429 error.

        Args:
            token_id: Token ID
        """
        debug_logger.log_warning(f"[429_BAN] Banning Token {token_id} (reason: 429 Rate Limit)")
        await self.db.update_token(
            token_id,
            is_active=False,
            ban_reason="429_rate_limit",
            banned_at=datetime.now(timezone.utc)
        )

    async def auto_unban_429_tokens(self):
        """Automatically unban tokens banned due to 429 errors.

        Rules:
        - Auto-unban 12 hours after the ban time.
        - Only unban tokens that have not yet expired.
        - Only unban tokens that were banned due to 429.
        """
        all_tokens = await self.db.get_all_tokens()
        now = datetime.now(timezone.utc)

        for token in all_tokens:
            # Skip tokens not banned due to 429.
            if token.ban_reason != "429_rate_limit":
                continue

            # Skip tokens that are not currently banned.
            if token.is_active:
                continue

            # Skip tokens without a ban timestamp.
            if not token.banned_at:
                continue

            # Check whether the token has already expired.
            if token.at_expires:
                # Normalize the timezone.
                if token.at_expires.tzinfo is None:
                    at_expires_aware = token.at_expires.replace(tzinfo=timezone.utc)
                else:
                    at_expires_aware = token.at_expires

                # Skip if already expired.
                if at_expires_aware <= now:
                    debug_logger.log_info(f"[AUTO_UNBAN] Token {token.id} expired, skipping unban")
                    continue

            # Normalize banned_at timezone.
            if token.banned_at.tzinfo is None:
                banned_at_aware = token.banned_at.replace(tzinfo=timezone.utc)
            else:
                banned_at_aware = token.banned_at

            # Check whether 12 hours have passed.
            time_since_ban = now - banned_at_aware
            if time_since_ban.total_seconds() >= 12 * 3600:  # 12 hours
                debug_logger.log_info(
                    f"[AUTO_UNBAN] Unbanning Token {token.id} (banned at: {banned_at_aware}, "
                    f"elapsed: {time_since_ban.total_seconds() / 3600:.1f} hours)"
                )
                await self.db.update_token(
                    token.id,
                    is_active=True,
                    ban_reason=None,
                    banned_at=None
                )
                # Reset the error counter.
                await self.db.reset_error_count(token.id)

    # ========== Credits refresh ==========

    async def refresh_credits(self, token_id: int) -> int:
        """Refresh the credits balance for a token.

        Returns:
            credits
        """
        token = await self.db.get_token(token_id)
        if not token:
            return 0

        # Ensure the AT is valid.
        token = await self.ensure_valid_token(token)
        if not token:
            return 0

        try:
            result = await self.flow_client.get_credits(token.at)
            credits = result.get("credits", 0)
            user_paygate_tier = result.get("userPaygateTier")

            # Update the database.
            await self.db.update_token(
                token_id,
                credits=credits,
                user_paygate_tier=user_paygate_tier,
            )

            return credits
        except Exception as e:
            debug_logger.log_error(f"Failed to refresh credits for token {token_id}: {str(e)}")
            return 0
