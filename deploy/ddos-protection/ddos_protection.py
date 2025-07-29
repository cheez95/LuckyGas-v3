#!/usr/bin/env python3
"""
DDoS Protection Service for LuckyGas
Monitors request patterns and blocks suspicious IPs
"""

import asyncio
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Set

import aiohttp
import redis
import structlog
import yaml
from aiohttp import web
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Configure structured logging
logger = structlog.get_logger()

# Prometheus metrics
requests_analyzed = Counter('ddos_requests_analyzed_total', 'Total requests analyzed')
blocked_ips = Counter('ddos_blocked_ips_total', 'Total IPs blocked')
current_blocked = Gauge('ddos_currently_blocked', 'Currently blocked IPs')
detection_histogram = Histogram('ddos_detection_duration_seconds', 'Detection processing time')

# Configuration from environment
THRESHOLD_RPS = int(os.getenv('THRESHOLD_RPS', '1000'))
BLOCK_DURATION = int(os.getenv('BLOCK_DURATION', '3600'))  # seconds
DETECTION_WINDOW = int(os.getenv('DETECTION_WINDOW', '60'))  # seconds
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
K8S_API_SERVER = os.getenv('KUBERNETES_SERVICE_HOST', 'kubernetes.default.svc.cluster.local')


class DDoSProtector:
    def __init__(self):
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.request_counts: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Set[str] = set()
        self.session = None
        
    async def start(self):
        """Initialize the service"""
        self.session = aiohttp.ClientSession()
        await self.load_blocked_ips()
        logger.info("DDoS Protection Service started", 
                   threshold_rps=THRESHOLD_RPS,
                   block_duration=BLOCK_DURATION,
                   detection_window=DETECTION_WINDOW)
    
    async def stop(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    
    async def load_blocked_ips(self):
        """Load blocked IPs from Redis"""
        try:
            blocked = self.redis_client.smembers('ddos:blocked_ips')
            self.blocked_ips = set(blocked)
            current_blocked.set(len(self.blocked_ips))
            logger.info("Loaded blocked IPs", count=len(self.blocked_ips))
        except Exception as e:
            logger.error("Failed to load blocked IPs", error=str(e))
    
    async def analyze_request(self, ip: str, path: str, user_agent: str):
        """Analyze a request for DDoS patterns"""
        requests_analyzed.inc()
        
        with detection_histogram.time():
            # Check if already blocked
            if ip in self.blocked_ips:
                return True
            
            # Record request timestamp
            now = time.time()
            self.request_counts[ip].append(now)
            
            # Clean old entries
            cutoff = now - DETECTION_WINDOW
            self.request_counts[ip] = [t for t in self.request_counts[ip] if t > cutoff]
            
            # Calculate request rate
            request_count = len(self.request_counts[ip])
            if request_count > THRESHOLD_RPS * (DETECTION_WINDOW / 60):
                await self.block_ip(ip, f"High request rate: {request_count} in {DETECTION_WINDOW}s")
                return True
            
            # Check for suspicious patterns
            if await self.check_suspicious_patterns(ip, path, user_agent):
                return True
            
            return False
    
    async def check_suspicious_patterns(self, ip: str, path: str, user_agent: str) -> bool:
        """Check for known attack patterns"""
        suspicious_patterns = [
            # Scanner detection
            ('nikto' in user_agent.lower(), "Scanner detected: nikto"),
            ('sqlmap' in user_agent.lower(), "Scanner detected: sqlmap"),
            ('nmap' in user_agent.lower(), "Scanner detected: nmap"),
            ('masscan' in user_agent.lower(), "Scanner detected: masscan"),
            
            # Path traversal attempts
            ('../' in path, "Path traversal attempt"),
            ('%2e%2e' in path.lower(), "Encoded path traversal"),
            
            # SQL injection patterns
            ('union select' in path.lower(), "SQL injection attempt"),
            ('drop table' in path.lower(), "SQL injection attempt"),
            
            # Suspicious endpoints
            (path.startswith('/admin') and ip not in self.get_admin_ips(), "Unauthorized admin access"),
            (path.startswith('/.git'), "Git repository scan"),
            (path.startswith('/.env'), "Environment file scan"),
        ]
        
        for condition, reason in suspicious_patterns:
            if condition:
                await self.block_ip(ip, reason)
                return True
        
        return False
    
    async def block_ip(self, ip: str, reason: str):
        """Block an IP address"""
        try:
            # Add to blocked set
            self.blocked_ips.add(ip)
            blocked_ips.inc()
            current_blocked.set(len(self.blocked_ips))
            
            # Store in Redis with expiry
            self.redis_client.sadd('ddos:blocked_ips', ip)
            self.redis_client.setex(f'ddos:block_reason:{ip}', BLOCK_DURATION, reason)
            
            # Log the block
            logger.warning("IP blocked", ip=ip, reason=reason, duration=BLOCK_DURATION)
            
            # Update Kubernetes network policy
            await self.update_network_policy(ip)
            
        except Exception as e:
            logger.error("Failed to block IP", ip=ip, error=str(e))
    
    async def unblock_ip(self, ip: str):
        """Unblock an IP address"""
        try:
            self.blocked_ips.discard(ip)
            self.redis_client.srem('ddos:blocked_ips', ip)
            current_blocked.set(len(self.blocked_ips))
            
            logger.info("IP unblocked", ip=ip)
            
        except Exception as e:
            logger.error("Failed to unblock IP", ip=ip, error=str(e))
    
    async def update_network_policy(self, ip: str):
        """Update Kubernetes network policy to block IP"""
        # This would integrate with Kubernetes API to update NetworkPolicy
        # For now, we just log the action
        logger.info("Would update network policy", ip=ip)
    
    def get_admin_ips(self) -> Set[str]:
        """Get allowed admin IPs from configuration"""
        # In production, this would come from a secure configuration
        return {'10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'}
    
    async def cleanup_expired_blocks(self):
        """Remove expired IP blocks"""
        while True:
            try:
                for ip in list(self.blocked_ips):
                    if not self.redis_client.exists(f'ddos:block_reason:{ip}'):
                        await self.unblock_ip(ip)
                
            except Exception as e:
                logger.error("Failed to cleanup blocks", error=str(e))
            
            await asyncio.sleep(60)  # Check every minute


# Web server for metrics and health checks
async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="OK", status=200)


async def metrics(request):
    """Prometheus metrics endpoint"""
    return web.Response(text=generate_latest().decode('utf-8'), 
                       content_type='text/plain; version=0.0.4')


async def analyze(request):
    """Analyze request endpoint (called by nginx)"""
    protector = request.app['protector']
    
    try:
        data = await request.json()
        ip = data.get('ip', '')
        path = data.get('path', '')
        user_agent = data.get('user_agent', '')
        
        is_blocked = await protector.analyze_request(ip, path, user_agent)
        
        return web.json_response({
            'blocked': is_blocked,
            'ip': ip
        })
        
    except Exception as e:
        logger.error("Failed to analyze request", error=str(e))
        return web.json_response({'error': str(e)}, status=500)


async def on_startup(app):
    """Initialize the application"""
    protector = DDoSProtector()
    await protector.start()
    app['protector'] = protector
    
    # Start background cleanup task
    app['cleanup_task'] = asyncio.create_task(protector.cleanup_expired_blocks())


async def on_cleanup(app):
    """Cleanup on shutdown"""
    app['cleanup_task'].cancel()
    await app['protector'].stop()


def create_app():
    """Create the web application"""
    app = web.Application()
    
    # Routes
    app.router.add_get('/health', health_check)
    app.router.add_get('/metrics', metrics)
    app.router.add_post('/analyze', analyze)
    
    # Lifecycle
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    
    return app


if __name__ == '__main__':
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Run the service
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=9090)