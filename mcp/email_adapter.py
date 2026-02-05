#!/usr/bin/env python3
"""
Email provider adapter for SMTP/IMAP operations.
"""

import asyncio
import base64
import email
import imaplib
import smtplib
import ssl
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import decode_header
from email.utils import parseaddr

from .mail_errors import MailError, ErrorSeverity, classify_smtp_error, CircuitBreaker
from .mail_config import SMTPConfig, IMAPConfig

@dataclass
class EmailMessage:
    message_id: str
    subject: str
    from_addr: str
    to_addrs: List[str]
    date: str
    body: str
    is_html: bool
    attachments: List[Dict[str, Any]]
    flags: List[str]

class EmailAdapter(ABC):
    """Abstract base class for email operations."""
    
    @abstractmethod
    async def send_email(self, to: List[str], subject: str, body: str, 
                        cc: Optional[List[str]] = None, 
                        bcc: Optional[List[str]] = None,
                        is_html: bool = False,
                        attachments: Optional[List[Dict]] = None) -> str:
        """Send an email. Returns message ID."""
        pass
    
    @abstractmethod
    async def read_inbox(self, limit: int = 10, offset: int = 0, 
                        unread_only: bool = False) -> List[EmailMessage]:
        """Read emails from inbox."""
        pass
    
    @abstractmethod
    async def search_emails(self, query: Optional[str] = None, 
                           from_addr: Optional[str] = None,
                           subject: Optional[str] = None,
                           date_from: Optional[str] = None,
                           date_to: Optional[str] = None,
                           limit: int = 10) -> List[EmailMessage]:
        """Search emails by criteria."""
        pass
    
    @abstractmethod
    async def delete_email(self, message_id: str, permanent: bool = False) -> bool:
        """Delete an email."""
        pass

class SMTPEmailAdapter(EmailAdapter):
    """SMTP/IMAP implementation of email adapter."""
    
    def __init__(self, smtp_config: SMTPConfig, imap_config: IMAPConfig):
        self.smtp_config = smtp_config
        self.imap_config = imap_config
        self.circuit_breaker = CircuitBreaker()
        self._smtp_pool: Optional[smtplib.SMTP] = None
        self._imap_pool: Optional[imaplib.IMAP4_SSL] = None
    
    async def _get_smtp_connection(self) -> smtplib.SMTP:
        """Get or create SMTP connection."""
        if not self.circuit_breaker.can_execute():
            raise MailError("provider_unavailable", 
                          "Circuit breaker open - too many failures",
                          ErrorSeverity.TRANSIENT)
        
        try:
            if self.smtp_config.use_tls:
                server = smtplib.SMTP(self.smtp_config.host, self.smtp_config.port, 
                                    timeout=self.smtp_config.timeout)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_config.host, self.smtp_config.port,
                                    timeout=self.smtp_config.timeout)
            
            server.login(self.smtp_config.username, self.smtp_config.password)
            self.circuit_breaker.record_success()
            return server
        except smtplib.SMTPAuthenticationError as e:
            self.circuit_breaker.record_failure()
            raise MailError("auth_failed", str(e), ErrorSeverity.PERMANENT)
        except smtplib.SMTPException as e:
            self.circuit_breaker.record_failure()
            raise classify_smtp_error(getattr(e, 'smtp_code', 500), str(e))
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise MailError("server_error", str(e), ErrorSeverity.TRANSIENT)
    
    async def _get_imap_connection(self) -> imaplib.IMAP4_SSL:
        """Get or create IMAP connection."""
        if not self.circuit_breaker.can_execute():
            raise MailError("provider_unavailable",
                          "Circuit breaker open - too many failures",
                          ErrorSeverity.TRANSIENT)
        
        try:
            if self.imap_config.use_ssl:
                server = imaplib.IMAP4_SSL(self.imap_config.host, self.imap_config.port)
            else:
                server = imaplib.IMAP4(self.imap_config.host, self.imap_config.port)
            
            server.login(self.imap_config.username, self.imap_config.password)
            self.circuit_breaker.record_success()
            return server
        except imaplib.IMAP4.error as e:
            self.circuit_breaker.record_failure()
            error_str = str(e)
            if "AUTH" in error_str.upper() or "LOGIN" in error_str.upper():
                raise MailError("auth_failed", error_str, ErrorSeverity.PERMANENT)
            raise MailError("server_error", error_str, ErrorSeverity.TRANSIENT)
    
    async def send_email(self, to: List[str], subject: str, body: str,
                        cc: Optional[List[str]] = None,
                        bcc: Optional[List[str]] = None,
                        is_html: bool = False,
                        attachments: Optional[List[Dict]] = None) -> str:
        """Send email via SMTP."""
        msg = MIMEMultipart()
        msg['From'] = self.smtp_config.username
        msg['To'] = ', '.join(to)
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = ', '.join(cc)
            to = to + cc
        if bcc:
            to = to + bcc
        
        # Attach body
        content_type = 'html' if is_html else 'plain'
        msg.attach(MIMEText(body, content_type))
        
        # Attach files
        if attachments:
            for att in attachments:
                part = MIMEBase('application', 'octet-stream')
                content = base64.b64decode(att['content'])
                part.set_payload(content)
                part.add_header('Content-Disposition', 
                              f'attachment; filename="{att["filename"]}"')
                msg.attach(part)
        
        # Send
        loop = asyncio.get_event_loop()
        server = await self._get_smtp_connection()
        
        try:
            await loop.run_in_executor(
                None, 
                lambda: server.sendmail(self.smtp_config.username, to, msg.as_string())
            )
            server.quit()
            return f"<{abs(hash(subject + str(asyncio.get_event_loop().time())))}@mcp.mail>"
        except smtplib.SMTPException as e:
            raise classify_smtp_error(getattr(e, 'smtp_code', 500), str(e))
    
    async def read_inbox(self, limit: int = 10, offset: int = 0,
                        unread_only: bool = False) -> List[EmailMessage]:
        """Read inbox via IMAP."""
        loop = asyncio.get_event_loop()
        server = await self._get_imap_connection()
        
        try:
            await loop.run_in_executor(None, lambda: server.select('INBOX'))
            
            search_criteria = 'UNSEEN' if unread_only else 'ALL'
            _, data = await loop.run_in_executor(
                None, 
                lambda: server.search(None, search_criteria)
            )
            
            message_ids = data[0].split()
            message_ids = message_ids[offset:offset+limit]
            
            messages = []
            for msg_id in message_ids:
                _, msg_data = await loop.run_in_executor(
                    None,
                    lambda: server.fetch(msg_id, '(RFC822)')
                )
                raw_email = msg_data[0][1]
                email_msg = email.message_from_bytes(raw_email)
                messages.append(self._parse_email(email_msg))
            
            server.close()
            server.logout()
            return messages
        except Exception as e:
            raise MailError("server_error", f"IMAP error: {str(e)}", 
                          ErrorSeverity.TRANSIENT)
    
    async def search_emails(self, query: Optional[str] = None,
                           from_addr: Optional[str] = None,
                           subject: Optional[str] = None,
                           date_from: Optional[str] = None,
                           date_to: Optional[str] = None,
                           limit: int = 10) -> List[EmailMessage]:
        """Search emails via IMAP."""
        loop = asyncio.get_event_loop()
        server = await self._get_imap_connection()
        
        try:
            await loop.run_in_executor(None, lambda: server.select('INBOX'))
            
            # Build IMAP search criteria
            criteria = []
            if from_addr:
                criteria.extend(['FROM', from_addr])
            if subject:
                criteria.extend(['SUBJECT', subject])
            if date_from:
                criteria.extend(['SINCE', date_from])
            if date_to:
                criteria.extend(['BEFORE', date_to])
            
            if not criteria:
                criteria = ['ALL']
            
            _, data = await loop.run_in_executor(
                None,
                lambda: server.search(None, ' '.join(criteria))
            )
            
            message_ids = data[0].split()[-limit:]  # Get most recent
            
            messages = []
            for msg_id in message_ids:
                _, msg_data = await loop.run_in_executor(
                    None,
                    lambda: server.fetch(msg_id, '(RFC822)')
                )
                raw_email = msg_data[0][1]
                email_msg = email.message_from_bytes(raw_email)
                messages.append(self._parse_email(email_msg))
            
            server.close()
            server.logout()
            return messages
        except Exception as e:
            raise MailError("server_error", f"IMAP search error: {str(e)}",
                          ErrorSeverity.TRANSIENT)
    
    async def delete_email(self, message_id: str, permanent: bool = False) -> bool:
        """Delete email via IMAP."""
        loop = asyncio.get_event_loop()
        server = await self._get_imap_connection()
        
        try:
            await loop.run_in_executor(None, lambda: server.select('INBOX'))
            
            # Search for message by Message-ID
            _, data = await loop.run_in_executor(
                None,
                lambda: server.search(None, f'HEADER Message-ID "{message_id}"')
            )
            
            if not data[0]:
                raise MailError("message_not_found", 
                              f"Message {message_id} not found",
                              ErrorSeverity.PERMANENT)
            
            for msg_id in data[0].split():
                if permanent:
                    await loop.run_in_executor(
                        None,
                        lambda: server.store(msg_id, '+FLAGS', '\\Deleted')
                    )
                else:
                    # Move to trash (Gmail) or mark deleted
                    await loop.run_in_executor(
                        None,
                        lambda: server.store(msg_id, '+FLAGS', '\\Deleted')
                    )
            
            if permanent:
                await loop.run_in_executor(None, server.expunge)
            
            server.close()
            server.logout()
            return True
        except MailError:
            raise
        except Exception as e:
            raise MailError("server_error", f"Delete error: {str(e)}",
                          ErrorSeverity.TRANSIENT)
    
    def _parse_email(self, msg) -> EmailMessage:
        """Parse email.message.Message into EmailMessage."""
        subject = self._decode_header(msg.get('Subject', ''))
        from_addr = parseaddr(msg.get('From', ''))[1]
        to_addrs = [parseaddr(addr)[1] for addr in msg.get_all('To', [])]
        date = msg.get('Date', '')
        message_id = msg.get('Message-ID', '')
        
        body = ""
        is_html = False
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        attachments.append({
                            "filename": filename,
                            "size": len(part.get_payload(decode=True) or b"")
                        })
                elif content_type == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif content_type == "text/html":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    is_html = True
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            is_html = msg.get_content_type() == "text/html"
        
        return EmailMessage(
            message_id=message_id,
            subject=subject,
            from_addr=from_addr,
            to_addrs=to_addrs,
            date=date,
            body=body[:10000],  # Limit body size
            is_html=is_html,
            attachments=attachments,
            flags=[]
        )
    
    def _decode_header(self, header: str) -> str:
        """Decode email header."""
        decoded = decode_header(header)
        result = []
        for part, charset in decoded:
            if isinstance(part, bytes):
                result.append(part.decode(charset or 'utf-8', errors='ignore'))
            else:
                result.append(part)
        return ''.join(result)
