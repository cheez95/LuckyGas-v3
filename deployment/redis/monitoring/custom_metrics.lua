-- Custom Redis metrics for Lucky Gas
-- This Lua script provides business-specific metrics for monitoring

-- Get current time
local current_time = redis.call('TIME')
local timestamp = current_time[1]

-- Initialize metrics table
local metrics = {}

-- Count active sessions
local session_keys = redis.call('KEYS', 'luckygas:session:*')
metrics['active_sessions'] = #session_keys

-- Count pending orders
local pending_orders = redis.call('ZCOUNT', 'luckygas:orders:pending', '-inf', '+inf')
metrics['pending_orders'] = pending_orders or 0

-- Count active deliveries
local active_deliveries = redis.call('SCARD', 'luckygas:deliveries:active')
metrics['active_deliveries'] = active_deliveries or 0

-- Get rate limiting metrics
local rate_limit_keys = redis.call('KEYS', 'luckygas:ratelimit:*')
local rate_limited_count = 0
for _, key in ipairs(rate_limit_keys) do
    local count = redis.call('GET', key)
    if tonumber(count) > 0 then
        rate_limited_count = rate_limited_count + 1
    end
end
metrics['rate_limited_clients'] = rate_limited_count

-- Get WebSocket connection count
local ws_connections = redis.call('HLEN', 'luckygas:websocket:connections')
metrics['websocket_connections'] = ws_connections or 0

-- Get notification queue size
local notification_queue_size = redis.call('LLEN', 'luckygas:notifications:queue')
metrics['notification_queue_size'] = notification_queue_size or 0

-- Get cache statistics
local cache_keys = redis.call('KEYS', 'luckygas:cache:*')
metrics['cache_keys_count'] = #cache_keys

-- Calculate cache memory usage
local cache_memory = 0
for _, key in ipairs(cache_keys) do
    local mem_usage = redis.call('MEMORY', 'USAGE', key)
    if mem_usage then
        cache_memory = cache_memory + mem_usage
    end
end
metrics['cache_memory_bytes'] = cache_memory

-- Get prediction cache metrics
local prediction_cache_keys = redis.call('KEYS', 'luckygas:predictions:*')
metrics['prediction_cache_count'] = #prediction_cache_keys

-- Get driver location tracking metrics
local driver_locations = redis.call('ZCARD', 'luckygas:drivers:locations')
metrics['tracked_drivers'] = driver_locations or 0

-- Get API usage metrics (last hour)
local api_calls_hour = 0
local api_usage_keys = redis.call('KEYS', 'luckygas:api:usage:*')
for _, key in ipairs(api_usage_keys) do
    local ttl = redis.call('TTL', key)
    if ttl > 0 and ttl <= 3600 then  -- Within last hour
        local count = redis.call('GET', key)
        if count then
            api_calls_hour = api_calls_hour + tonumber(count)
        end
    end
end
metrics['api_calls_last_hour'] = api_calls_hour

-- Get error count from error tracking
local error_count = redis.call('GET', 'luckygas:errors:count:' .. os.date('%Y%m%d'))
metrics['errors_today'] = tonumber(error_count) or 0

-- Get background job metrics
local job_queues = {'default', 'critical', 'low'}
for _, queue in ipairs(job_queues) do
    local queue_size = redis.call('LLEN', 'luckygas:jobs:' .. queue)
    metrics['job_queue_' .. queue] = queue_size or 0
end

-- Get real-time event stream metrics
local event_stream_length = redis.call('XLEN', 'luckygas:events:stream')
metrics['event_stream_length'] = event_stream_length or 0

-- Return metrics as JSON
return cjson.encode(metrics)